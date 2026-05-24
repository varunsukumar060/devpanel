#!/usr/bin/env bash
# devpanel — universal install script
# Supports: Linux Mint, Ubuntu, Debian, Arch, Fedora, openSUSE
# Python 3.8–3.12+, handles PEP 668 externally-managed environments

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  devpanel — Linux Dev Companion Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Python check
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 not found."
    exit 1
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✔ Python $PYVER detected"

# ── Distro detection
DISTRO_ID=""
[ -f /etc/os-release ] && DISTRO_ID=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"' | tr '[:upper:]' '[:lower:]')
DISTRO_LIKE=$(grep '^ID_LIKE=' /etc/os-release 2>/dev/null | cut -d= -f2 | tr -d '"' | tr '[:upper:]' '[:lower:]') || true
FAMILY="$DISTRO_ID $DISTRO_LIKE"
echo "✔ Distro: $DISTRO_ID"

# ── Ensure python3-venv is available
if ! python3 -m venv --help &>/dev/null; then
    echo "Installing python3-venv..."
    if echo "$FAMILY" | grep -qE "ubuntu|debian|mint|linuxmint|pop"; then
        sudo apt-get install -y python3-venv python3-full
    elif echo "$FAMILY" | grep -qE "arch|manjaro|endeavour"; then
        sudo pacman -S --noconfirm python
    elif echo "$FAMILY" | grep -qE "fedora|rhel|centos|rocky|alma"; then
        sudo dnf install -y python3
    elif echo "$FAMILY" | grep -qE "opensuse|suse"; then
        sudo zypper install -y python3
    else
        echo "[WARN] Could not auto-install python3-venv. Install it manually for your distro."
    fi
fi

# ── Create venv
VENV_DIR="$(pwd)/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# ── Install deps
echo "Installing textual and psutil into venv..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install textual psutil --quiet

# ── Create launcher
cat > run.sh << 'RUNEOF'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/.venv/bin/python3" "$DIR/devpanel.py" "$@"
RUNEOF
chmod +x run.sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✔ Done! Run devpanel:"
echo ""
echo "  bash run.sh          ← normal"
echo "  sudo bash run.sh     ← with cpufreq control"
echo ""
echo "Keys: 1-7 tabs │ r refresh │ q quit"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
