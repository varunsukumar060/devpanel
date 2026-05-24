# devpanel 🖥️

> A lightweight terminal TUI dev companion for Linux — system stats, git repo monitor, thermal manager, memory inspector, boot optimizer & workspace launcher in one tabbed app.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Phase](https://img.shields.io/badge/Phase-2%20%E2%80%94%20Config%20System-brightgreen)

---

## Features

| Tab | Key | Description |
|-----|-----|-------------|
| HUD | `1` | Live CPU, RAM, disk, WiFi, serial ports, git status of CWD |
| Repos | `2` | Scans all project dirs for git repos — branch, dirty state, last commit |
| Thermal | `3` | CPU/GPU temps, fan RPM, power profile switcher |
| Memory | `4` | RAM map, top processes, swap, zombie cleaner |
| Boot | `5` | systemd-analyze blame, slowest services breakdown |
| Workspace | `6` | USB device detection, ESP32/Arduino profile matching, project quick-access |
| **Config** | `7` | **Live view + edit of `~/.devpanel/config.toml`** |

---

## Installation

```bash
git clone https://github.com/varunsukumar060/devpanel.git
cd devpanel
bash install.sh
bash run.sh
```

On first launch, devpanel auto-creates `~/.devpanel/config.toml` with smart defaults for your system.

---

## Configuration

All settings live in **`~/.devpanel/config.toml`** — auto-generated on first run.

```toml
[general]
title = "devpanel — Linux Dev Companion"
hud_refresh   = 3    # seconds
repos_refresh = 10
stats_refresh = 4

[paths]
projects_dir   = "~/Projects"           # auto-detected on first run
extra_scan_dirs = ["~/Documents", "~/Desktop"]

[workspace.profiles]
# "vendor:product" = ["label", "cmd1", "cmd2"]
"10c4:ea60" = ["ESP32 (CP2102)", "code", "python3 -m serial.tools.miniterm"]
"1a86:7523" = ["Arduino (CH340)", "arduino-ide"]

[thermal]
warn_temp = 60
crit_temp = 80
```

Edit via **Tab 7 (Config)** inside devpanel, or directly:
```bash
nano ~/.devpanel/config.toml
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`–`7` | Switch tabs |
| `r` | Refresh all tabs |
| `q` | Quit |

---

## Power Profile Buttons (Thermal Tab)

CPU governor control requires root access. To use without typing sudo each time:

```bash
# Option 1: Run devpanel as root
sudo bash run.sh

# Option 2: Passwordless sudoers rule (recommended)
sudo visudo -f /etc/sudoers.d/devpanel-cpufreq
# Add this line:
# YOUR_USERNAME ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

---

## Roadmap

- [x] Phase 1 — Core 6-tab TUI
- [x] Phase 2 — `~/.devpanel/config.toml` + Config Viewer tab
- [ ] Phase 3 — Distro-agnostic, `pipx` installable
- [ ] Phase 4 — Screenshots, GitHub release `v1.0.0`
- [ ] Phase 5 — Publish to PyPI

---

## Author

**Varun Sukumar K** — [@varunsukumar060](https://github.com/varunsukumar060)  
Electronics & Communication Engineering | Embedded Systems | Linux

---

## License

MIT — free to use, modify, and distribute.
