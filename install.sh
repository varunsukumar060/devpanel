#!/usr/bin/env bash
# devpanel — install script for Linux Mint / Debian-based systems
# Supports Python 3.12+ externally-managed-environment (PEP 668)
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

# Ensure python3-venv is available
if ! python3 -m venv --help &>/dev/null; then
    echo "Installing python3-venv..."
    sudo apt-get install -y python3-venv python3-full
fi

# Create virtual environment inside the devpanel folder
VENV_DIR="$(pwd)/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv and install deps
echo "Installing Python dependencies into venv..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install textual psutil --quiet

# Create launcher script
cat > run.sh << 'EOF'
#!/usr/bin/env bash
# devpanel launcher — uses the local venv
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/.venv/bin/python3" "$DIR/devpanel.py"
EOF
chmod +x run.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✔ Installation complete!"
echo ""
echo "To run devpanel:"
echo "  bash run.sh"
echo ""
echo "  (or activate venv manually: source .venv/bin/activate)"
echo "  (then run: python3 devpanel.py)"
echo ""
echo "Keyboard shortcuts:"
echo "  1-6   → Switch tabs"
echo "  r     → Refresh current tab"
echo "  q     → Quit"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
