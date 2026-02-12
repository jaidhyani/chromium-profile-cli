#!/bin/bash
# Development setup script for chromium-cli

set -e

echo "🔧 Setting up chromium-cli development environment..."

# Check for leveldb
if ! brew list leveldb &>/dev/null; then
    echo "📦 Installing leveldb..."
    brew install leveldb
else
    echo "✓ leveldb already installed"
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "🐍 Creating virtual environment..."
    uv venv
else
    echo "✓ Virtual environment exists"
fi

# Activate
source .venv/bin/activate

# Install build dependencies
echo "📦 Installing build dependencies..."
uv pip install pip setuptools wheel

# Build and install plyvel with leveldb paths
echo "📦 Building plyvel with leveldb..."
LEVELDB_PREFIX=$(brew --prefix leveldb)
export CFLAGS="-I${LEVELDB_PREFIX}/include"
export LDFLAGS="-L${LEVELDB_PREFIX}/lib"
export LIBRARY_PATH="${LEVELDB_PREFIX}/lib"
export CPATH="${LEVELDB_PREFIX}/include"

python -m pip install --no-cache-dir --no-binary :all: plyvel

# Then install chromium-cli
echo "📦 Installing chromium-cli..."
uv pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use chromium-cli:"
echo "  source .venv/bin/activate"
echo "  chromium-cli --help"
