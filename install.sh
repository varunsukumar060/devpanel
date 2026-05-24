#!/usr/bin/env bash
# devpanel — install script for Linux Mint / Debian-based systems
# Usage: bash install.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  devpanel — Linux Dev Companion Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 not found. Install it first."
    exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✔ Python $PYVER detected"

# Install pip if missing
if ! command -v pip3 &>/dev/null; then
    echo "Installing pip..."
    sudo apt-get install -y python3-pip
fi

# Install pipx if missing (cleaner installs)
if ! command -v pipx &>/dev/null; then
    echo "Installing pipx..."
    sudo apt-get install -y pipx
    pipx ensurepath
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install --user textual psutil

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✔ Installation complete!"
echo ""
echo "To run devpanel:"
echo "  python3 devpanel.py"
echo ""
echo "Keyboard shortcuts:"
echo "  1-6   → Switch tabs"
echo "  r     → Refresh current tab"
echo "  q     → Quit"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
