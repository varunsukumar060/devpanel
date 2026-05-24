# devpanel 🖥️

> A lightweight terminal TUI dev companion for Linux — system stats, git repo monitor, thermal manager, memory inspector, boot optimizer & workspace launcher in one tabbed app.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

| Tab | Feature | Description |
|-----|---------|-------------|
| `[1] HUD` | System HUD | Live CPU, RAM, disk, WiFi, serial ports, git status |
| `[2] Repos` | Git Monitor | Scans all project dirs for git repos — branch, dirty state, last commit |
| `[3] Thermal` | Thermal Manager | CPU/GPU temps, fan RPM, power profile switcher |
| `[4] Memory` | Memory Inspector | RAM map, top processes, swap, zombie cleaner |
| `[5] Boot` | Boot Optimizer | systemd-analyze blame, slowest services breakdown |
| `[6] Workspace` | Workspace Launcher | USB device detection, ESP32/Arduino profile matching, project quick-access |

---

## Installation

### Prerequisites
- Python 3.8+
- Linux (tested on Linux Mint XFCE)

### Quick Install

```bash
git clone https://github.com/varunsukumar060/devpanel.git
cd devpanel
bash install.sh
```

### Manual Install

```bash
git clone https://github.com/varunsukumar060/devpanel.git
cd devpanel
pip3 install --user textual psutil
python3 devpanel.py
```

---

## Usage

```bash
python3 devpanel.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Switch to HUD tab |
| `2` | Switch to Repos tab |
| `3` | Switch to Thermal tab |
| `4` | Switch to Memory tab |
| `5` | Switch to Boot tab |
| `6` | Switch to Workspace tab |
| `r` | Refresh all tabs |
| `q` | Quit |

---

## Configuration

Edit the config block at the top of `devpanel.py`:

```python
# Path to your projects folder
PROJECTS_DIR = Path("/home/varun_sukumar/Project")

# Additional directories to scan for git repos
DEV_DIRS = [PROJECTS_DIR, Path.home() / "Documents", Path.home() / "Desktop"]

# USB device profiles: vendor:product → (label, [commands])
WORKSPACE_PROFILES = {
    "10c4:ea60": ("ESP32 (CP2102)",  ["code", "python3 -m serial.tools.miniterm"]),
    "1a86:7523": ("Arduino (CH340)", ["arduino-ide"]),
    "0403:6001": ("FTDI Device",     ["code"]),
}
```

---

## Roadmap

- [x] Phase 1 — Core 6-tab TUI (Linux Mint, single machine)
- [ ] Phase 2 — `~/.devpanel/config.toml` for user config
- [ ] Phase 3 — Distro-agnostic, `pipx` installable
- [ ] Phase 4 — Plugin system for custom tabs
- [ ] Phase 5 — Publish to PyPI

---

## Author

**Varun Sukumar K** — [@varunsukumar060](https://github.com/varunsukumar060)  
Electronics & Communication Engineering | Embedded Systems | Linux

---

## License

MIT License — free to use, modify, and distribute.
