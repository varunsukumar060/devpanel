# devpanel v1.0.0 — First Stable Release 🎉

> A lightweight terminal TUI dev companion for Linux — built in one session, from idea to v1.0.0.

---

### What is devpanel?

devpanel is a 7-tab terminal dashboard for Linux developers. One command launches a full system overview right in your terminal — no browser, no Electron, no cloud.

```bash
git clone https://github.com/varunsukumar060/devpanel.git
cd devpanel && bash install.sh && bash run.sh
```

---

### Tabs at a Glance

| Key | Tab | What it shows |
|-----|-----|---------------|
| `1` | **HUD** | CPU %, RAM, disk, WiFi SSID, serial ports, live git status of CWD |
| `2` | **Repos** | Scans project dirs for git repos — branch, clean/dirty, last commit |
| `3` | **Thermal** | CPU temps, fan RPM, governor + one-click power profiles |
| `4` | **Memory** | RAM map, top 10 procs by RAM, swap, zombie process cleaner |
| `5` | **Boot** | `systemd-analyze blame` — slowest services, quick disable commands |
| `6` | **Workspace** | USB device list + ESP32/Arduino board auto-detection + project browser |
| `7` | **Config** | Live `~/.devpanel/config.toml` viewer with syntax highlight + nano launch |

---

### Highlights

- **Auto-detects your distro** — reads `/etc/os-release`, shows name + version in HUD header
- **`~/.devpanel/config.toml`** — auto-created on first launch with smart path detection
- **Universal installer** — handles `apt`, `pacman`, `dnf`, `zypper` automatically
- **pipx-ready** — `pyproject.toml` included for `pip install .` or `pipx install .`
- **Embedded-dev friendly** — serial port detection, ESP32/Arduino USB profile matching
- **Zero config to start** — works out of the box, everything configurable via TOML

---

### Tested On

- ✔ **Linux Mint 22.3** (Lenovo E41-25, AMD Ryzen, 8GB RAM) — primary dev machine
- ✔ Ubuntu / Debian / Pop!_OS (apt family)
- ✔ Arch / Manjaro / EndeavourOS
- ✔ Fedora / RHEL / Rocky
- ✔ openSUSE

---

### Requirements

```
Python >= 3.8
textual >= 0.80.0
psutil >= 5.9.0
```

Installed automatically by `bash install.sh` into a local `.venv`.

---

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`–7 | Switch tabs |
| `r` | Refresh all |
| `q` | Quit |

---

### Phase History

- Phase 1 — Core 6-tab TUI
- Phase 2 — `~/.devpanel/config.toml` + Config tab
- Phase 3 — Distro-agnostic, `pyproject.toml`, universal installer
- Phase 4 — 🎉 This release — `v1.0.0` with screenshots and full docs

**Next:** Phase 5 — `pip install devpanel` via PyPI

---

*Built by [@varunsukumar060](https://github.com/varunsukumar060) — ECE student, embedded systems dev, Linux user.*
