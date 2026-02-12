"""Minimal LevelDB reader for Chromium sync data.

Reads key-value pairs from LevelDB databases (.ldb/.sst table files and .log
files) including Snappy-compressed blocks. Only supports raw iteration — no
sorted/merged views, no manifest handling.

Based on ccl_chromium_reader (ccl_leveldb) and ccl_simplesnappy by CCL Forensics,
both MIT licensed. Original author: Alex Caithness.
"""

import enum
import io
import os
import pathlib
import re
import struct
import typing


# ---------------------------------------------------------------------------
# Snappy decompression (from ccl_simplesnappy, MIT license)
# ---------------------------------------------------------------------------

_SNAPPY_LITERAL = 0
_SNAPPY_COPY_1BYTE = 1
_SNAPPY_COPY_2BYTE = 2
_SNAPPY_COPY_4BYTE = 3


def _read_le_varint(stream: typing.BinaryIO, *, is_google_32bit=False) -> int | None:
    """Read an unsigned little-endian varint. Returns None at EOF."""
    result = 0
    limit = 5 if is_google_32bit else 10
    for i in range(limit):
        raw = stream.read(1)
        if len(raw) < 1:
            return None
        byte = raw[0]
        result |= (byte & 0x7F) << (i * 7)
        if (byte & 0x80) == 0:
            return result
    return result


def _snappy_decompress(data: typing.BinaryIO) -> bytes:
    """Decompress a raw Snappy-compressed stream."""
    uncompressed_length = _read_le_varint(data)
    out = io.BytesIO()

    while True:
        raw = data.read(1)
        if not raw:
            break
        tag_byte = raw[0]
        tag = tag_byte & 0x03

        if tag == _SNAPPY_LITERAL:
            size_marker = (tag_byte & 0xFC) >> 2
            if size_marker < 60:
                length = 1 + size_marker
            elif size_marker == 60:
                length = 1 + data.read(1)[0]
            elif size_marker == 61:
                length = 1 + struct.unpack("<H", data.read(2))[0]
            elif size_marker == 62:
                length = 1 + struct.unpack("<I", data.read(3) + b"\x00")[0]
            else:
                length = 1 + struct.unpack("<I", data.read(4))[0]

            chunk = data.read(length)
            if len(chunk) < length:
                raise ValueError("Truncated snappy literal")
            out.write(chunk)

        else:
            if tag == _SNAPPY_COPY_1BYTE:
                length = ((tag_byte & 0x1C) >> 2) + 4
                offset = ((tag_byte & 0xE0) << 3) | data.read(1)[0]
            elif tag == _SNAPPY_COPY_2BYTE:
                length = 1 + ((tag_byte & 0xFC) >> 2)
                offset = struct.unpack("<H", data.read(2))[0]
            else:
                length = 1 + ((tag_byte & 0xFC) >> 2)
                offset = struct.unpack("<I", data.read(4))[0]

            if offset == 0:
                raise ValueError("Snappy backreference offset cannot be 0")

            src_pos = out.tell() - offset
            buf = out.getbuffer()[src_pos: src_pos + length].tobytes()
            if offset <= length:
                buf = (buf * length)[:length]
            out.write(buf)

    result = out.getvalue()
    if uncompressed_length != len(result):
        raise ValueError("Snappy decompression length mismatch")
    return result


# ---------------------------------------------------------------------------
# LevelDB types
# ---------------------------------------------------------------------------

class KeyState(enum.Enum):
    Deleted = 0
    Live = 1
    Unknown = 2


class Record:
    """A key-value record from a LevelDB database."""
    __slots__ = ("key", "value", "seq", "state", "_from_ldb")

    def __init__(self, key: bytes, value: bytes, seq: int, state: KeyState, from_ldb: bool):
        self.key = key
        self.value = value
        self.seq = seq
        self.state = state
        self._from_ldb = from_ldb

    @property
    def user_key(self) -> bytes:
        """Key without the trailing 8-byte metadata that .ldb files append."""
        if self._from_ldb and len(self.key) >= 8:
            return self.key[:-8]
        return self.key


# ---------------------------------------------------------------------------
# .ldb / .sst table files
# ---------------------------------------------------------------------------

_BLOCK_TRAILER_SIZE = 5
_TABLE_FOOTER_SIZE = 48
_TABLE_MAGIC = 0xDB4775248B80FB57


def _read_block_handle(stream: typing.BinaryIO) -> tuple[int, int]:
    """Read a (offset, length) BlockHandle from a varint-encoded stream."""
    offset = _read_le_varint(stream)
    length = _read_le_varint(stream)
    return offset, length


def _iter_block_entries(raw: bytes) -> typing.Iterable[tuple[bytes, bytes]]:
    """Yield (key, value) pairs from a LevelDB data block.

    Blocks use prefix compression: each entry stores how many bytes of the
    key it shares with the previous entry, then the non-shared suffix.
    """
    restart_count = struct.unpack("<I", raw[-4:])[0]
    restart_array_offset = len(raw) - (restart_count + 1) * 4

    first_entry_offset = struct.unpack("<i", raw[restart_array_offset: restart_array_offset + 4])[0]

    with io.BytesIO(raw) as buf:
        buf.seek(first_entry_offset)
        key = b""

        while buf.tell() < restart_array_offset:
            shared_len = _read_le_varint(buf, is_google_32bit=True)
            non_shared_len = _read_le_varint(buf, is_google_32bit=True)
            value_len = _read_le_varint(buf, is_google_32bit=True)

            key = key[:shared_len] + buf.read(non_shared_len)
            value = buf.read(value_len)
            yield key, value


def _iter_table_file(path: pathlib.Path) -> typing.Iterable[Record]:
    """Yield Records from a .ldb or .sst table file."""
    with open(path, "rb") as f:
        # Read footer (last 48 bytes)
        f.seek(-_TABLE_FOOTER_SIZE, os.SEEK_END)
        _meta_handle = _read_block_handle(f)  # noqa: F841 (unused but must consume)
        index_handle = _read_block_handle(f)

        f.seek(-8, os.SEEK_END)
        magic = struct.unpack("<Q", f.read(8))[0]
        if magic != _TABLE_MAGIC:
            raise ValueError(f"Invalid magic in {path}")

        def read_block(offset: int, length: int) -> tuple[bytes, bool]:
            f.seek(offset)
            block_data = f.read(length)
            trailer = f.read(_BLOCK_TRAILER_SIZE)
            is_compressed = trailer[0] != 0
            if is_compressed:
                block_data = _snappy_decompress(io.BytesIO(block_data))
            return block_data, is_compressed

        # Read index block to find data blocks
        index_data, _ = read_block(*index_handle)
        index_entries = list(_iter_block_entries(index_data))

        # Read each data block and yield records
        for _index_key, handle_bytes in index_entries:
            with io.BytesIO(handle_bytes) as hstream:
                block_handle = _read_block_handle(hstream)

            block_data, was_compressed = read_block(*block_handle)

            for key, value in _iter_block_entries(block_data):
                seq = struct.unpack("<Q", key[-8:])[0] >> 8
                state = KeyState.Deleted if (len(key) > 8 and key[-8] == 0) else KeyState.Live
                if len(key) <= 8:
                    state = KeyState.Unknown
                yield Record(key, value, seq, state, from_ldb=True)


# ---------------------------------------------------------------------------
# .log files
# ---------------------------------------------------------------------------

_LOG_BLOCK_SIZE = 32768

_LOG_FULL = 1
_LOG_FIRST = 2
_LOG_MIDDLE = 3
_LOG_LAST = 4


def _iter_log_batches(path: pathlib.Path) -> typing.Iterable[bytes]:
    """Yield raw batch payloads from a LevelDB .log file."""
    with open(path, "rb") as f:
        in_record = False
        block = b""

        while chunk := f.read(_LOG_BLOCK_SIZE):
            with io.BytesIO(chunk) as buf:
                while buf.tell() < _LOG_BLOCK_SIZE - 6:
                    header = buf.read(7)
                    if len(header) < 7:
                        break
                    _crc, length, block_type = struct.unpack("<IHB", header)

                    if block_type == _LOG_FULL:
                        yield buf.read(length)
                        in_record = False
                    elif block_type == _LOG_FIRST:
                        block = buf.read(length)
                        in_record = True
                    elif block_type == _LOG_MIDDLE:
                        if in_record:
                            block += buf.read(length)
                        else:
                            buf.read(length)
                    elif block_type == _LOG_LAST:
                        if in_record:
                            block += buf.read(length)
                            in_record = False
                            yield block
                        else:
                            buf.read(length)
                    else:
                        buf.read(length)


def _iter_log_file(path: pathlib.Path) -> typing.Iterable[Record]:
    """Yield Records from a .log file."""
    for batch in _iter_log_batches(path):
        with io.BytesIO(batch) as buf:
            header = buf.read(12)
            if len(header) < 12:
                continue
            seq, count = struct.unpack("<QI", header)

            for i in range(count):
                raw_state = buf.read(1)
                if len(raw_state) < 1:
                    break
                state = KeyState(raw_state[0]) if raw_state[0] <= 1 else KeyState.Unknown

                key_len = _read_le_varint(buf, is_google_32bit=True)
                if key_len is None:
                    break
                key = buf.read(key_len)

                if state != KeyState.Deleted:
                    val_len = _read_le_varint(buf, is_google_32bit=True)
                    if val_len is None:
                        break
                    value = buf.read(val_len)
                else:
                    value = b""

                yield Record(key, value, seq + i, state, from_ldb=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DATA_FILE_RE = re.compile(r"[0-9]{6}\.(ldb|log|sst)")


def iter_leveldb_records(db_dir: str | os.PathLike) -> typing.Iterable[Record]:
    """Iterate all records in a LevelDB database directory.

    Yields records from .ldb/.sst table files and .log files, ordered by
    file number (oldest first). Callers should deduplicate by keeping the
    last occurrence of each user_key.
    """
    db_path = pathlib.Path(db_dir)
    if not db_path.is_dir():
        raise ValueError(f"Not a directory: {db_dir}")

    files: list[tuple[int, pathlib.Path, str]] = []
    for f in db_path.iterdir():
        if f.is_file() and _DATA_FILE_RE.match(f.name):
            file_no = int(f.stem, 16)
            files.append((file_no, f, f.suffix.lower()))

    files.sort(key=lambda x: x[0])

    for _file_no, path, ext in files:
        if ext == ".log":
            yield from _iter_log_file(path)
        elif ext in (".ldb", ".sst"):
            yield from _iter_table_file(path)
