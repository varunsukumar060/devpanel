# devpanel 🖥️

> A lightweight terminal TUI dev companion for Linux — system stats, git repo monitor, thermal manager, memory inspector, boot optimizer & workspace launcher in one tabbed app.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-brightgreen)

---

## Screenshots

> Running on Lenovo E41-25 • Linux Mint 22.3 • AMD Ryzen CPU • 8GB RAM

| Tab | Preview |
|-----|---------|
| **[1] HUD** | Live CPU 22.5%, RAM 50%, WiFi: SRMTRC\_EC, git branch on CWD |
| **[2] Repos** | Scans ~/Project, ~/Documents, ~/Desktop — shows ecg-monitor-pro ✔ clean |
| **[3] Thermal** | k10temp 46.5°C, Governor: powersave @ 1297 MHz, 3 power profile buttons |
| **[4] Memory** | 7403MB total, top procs: clamd 13%, chrome tabs, mysqld, zombie counter |
| **[5] Boot** | Total: 5m 11s — vboxdrv.service tops at 24.8s, quick disable actions shown |
| **[6] Workspace** | USB hub/WiFi/camera list, ESP32/Arduino profile matcher, project browser |
| **[7] Config** | Live `~/.devpanel/config.toml` viewer with syntax highlighting + nano launcher |

---

## Features

| Tab | Key | Description |
|-----|-----|-------------|
| HUD | `1` | Live CPU, RAM, disk, WiFi, serial ports, git status, distro info |
| Repos | `2` | Scans all project dirs for git repos — branch, dirty state, last commit |
| Thermal | `3` | CPU/GPU temps, fan RPM, power profile switcher |
| Memory | `4` | RAM map, top processes, swap, zombie cleaner |
| Boot | `5` | systemd-analyze blame, slowest services breakdown |
| Workspace | `6` | USB device detection, ESP32/Arduino profile matching, project quick-access |
| Config | `7` | Live view + edit of `~/.devpanel/config.toml` |

---

## Quick Install (any Linux distro)

```bash
git clone https://github.com/varunsukumar060/devpanel.git
cd devpanel
bash install.sh
bash run.sh
```

> On first launch, `~/.devpanel/config.toml` is auto-created with smart defaults for your system.

### Supported Distros

| Distro Family | Tested |
|---|---|
| Ubuntu / Linux Mint / Debian / Pop!_OS | ✔ |
| Arch / Manjaro / EndeavourOS | ✔ |
| Fedora / RHEL / Rocky / AlmaLinux | ✔ |
| openSUSE | ✔ |

---

## Configuration

All settings live in **`~/.devpanel/config.toml`** — auto-generated on first run:

```toml
[general]
title         = "devpanel — Linux Dev Companion"
hud_refresh   = 3
repos_refresh = 10
stats_refresh = 4

[paths]
projects_dir    = "~/Projects"       # auto-detected on first launch
extra_scan_dirs = ["~/Documents", "~/Desktop"]

[workspace.profiles]
"10c4:ea60" = ["ESP32 (CP2102)", "code", "python3 -m serial.tools.miniterm"]
"1a86:7523" = ["Arduino (CH340)", "arduino-ide"]
"0403:6001" = ["FTDI Device",     "code"]

[thermal]
warn_temp = 60
crit_temp = 80
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`–7 | Switch tabs |
| `r` | Refresh all tabs |
| `q` | Quit |

---

## Power Profiles (Thermal Tab)

```bash
# Option 1: run as root
sudo bash run.sh

# Option 2: passwordless sudoers rule (recommended)
sudo visudo -f /etc/sudoers.d/devpanel-cpufreq
# Add: YOUR_USERNAME ALL=(ALL) NOPASSWD: /usr/bin/tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

---

## Roadmap

- [x] Phase 1 — Core 6-tab TUI (HUD, Repos, Thermal, Memory, Boot, Workspace)
- [x] Phase 2 — `~/.devpanel/config.toml` auto-generation + Config tab
- [x] Phase 3 — Distro-agnostic (apt/pacman/dnf/zypper), `pyproject.toml`, pipx-ready
- [x] Phase 4 — `v1.0.0` GitHub release with screenshots
- [ ] Phase 5 — Publish to PyPI (`pip install devpanel`)

---

## Author

**Varun Sukumar K** — [@varunsukumar060](https://github.com/varunsukumar060)  
Electronics & Communication Engineering | Embedded Systems | Linux

---

## License

MIT — free to use, modify, and distribute.
