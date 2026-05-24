#!/usr/bin/env python3
"""
devpanel — Lightweight Linux Dev Companion TUI
Phase 6: Network & Connectivity Tab
Author: Varun Sukumar K (@varunsukumar060)
"""

__version__ = "1.1.0-dev"
__author__  = "Varun Sukumar K"

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, Button, Input
from textual.reactive import reactive

import psutil
import subprocess
import os
import sys
import glob
import shutil
import platform
import time
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# DISTRO DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_distro() -> dict:
    info = {"name": "Linux", "id": "", "id_like": "", "version": "",
            "pkg_manager": "unknown", "terminal": "xterm"}
    try:
        with open("/etc/os-release") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NAME="):
                    info["name"] = line.split("=", 1)[1].strip('"')
                elif line.startswith("ID="):
                    info["id"] = line.split("=", 1)[1].strip('"').lower()
                elif line.startswith("ID_LIKE="):
                    info["id_like"] = line.split("=", 1)[1].strip('"').lower()
                elif line.startswith("VERSION_ID="):
                    info["version"] = line.split("=", 1)[1].strip('"')
    except Exception:
        pass
    family = info["id"] + " " + info["id_like"]
    if any(x in family for x in ["ubuntu", "debian", "mint", "pop", "elementary", "kali", "linuxmint"]):
        info["pkg_manager"] = "apt"
    elif any(x in family for x in ["arch", "manjaro", "endeavour", "garuda"]):
        info["pkg_manager"] = "pacman"
    elif any(x in family for x in ["fedora", "rhel", "centos", "rocky", "alma"]):
        info["pkg_manager"] = "dnf"
    elif any(x in family for x in ["opensuse", "suse"]):
        info["pkg_manager"] = "zypper"
    elif shutil.which("apt"):    info["pkg_manager"] = "apt"
    elif shutil.which("pacman"): info["pkg_manager"] = "pacman"
    elif shutil.which("dnf"):    info["pkg_manager"] = "dnf"
    for t in ["xfce4-terminal", "gnome-terminal", "konsole", "xterm", "kitty", "alacritty", "tilix"]:
        if shutil.which(t):
            info["terminal"] = t
            break
    return info

DISTRO = detect_distro()

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_DIR  = Path.home() / ".devpanel"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
# devpanel configuration — ~/.devpanel/config.toml
# Docs: https://github.com/varunsukumar060/devpanel

[general]
title         = "devpanel — Linux Dev Companion"
hud_refresh   = 3
repos_refresh = 10
stats_refresh = 4

[paths]
projects_dir    = "{projects_dir}"
extra_scan_dirs = [
    "~/Documents",
    "~/Desktop",
]

[network]
ping_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]

[workspace]
[workspace.profiles]
"10c4:ea60" = ["ESP32 (CP2102)",  "code",  "python3 -m serial.tools.miniterm"]
"1a86:7523" = ["Arduino (CH340)", "arduino-ide"]
"0403:6001" = ["FTDI Device",     "code"]
"2341:0043" = ["Arduino Uno",     "arduino-ide"]
"2341:0010" = ["Arduino Mega",    "arduino-ide"]

[thermal]
warn_temp = 60
crit_temp = 80
"""

def _detect_projects_dir() -> str:
    for candidate in ["Project", "Projects", "projects", "dev", "code", "workspace",
                      "Documents/Projects", "Documents/projects"]:
        p = Path.home() / candidate
        if p.exists():
            return str(p)
    return str(Path.home() / "Projects")

def ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG.format(projects_dir=_detect_projects_dir()))

def _parse_toml_simple(text: str) -> dict:
    import re
    result: dict = {}
    section: list = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^\[([\w.]+)\]$', line)
        if m:
            section = m.group(1).split(".")
            node = result
            for part in section:
                node = node.setdefault(part, {})
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if val.startswith("["):
            parsed: object = re.findall(r'"([^"]+)"', val)
        elif val.startswith('"'):
            parsed = val.strip('"')
        elif re.match(r'^-?\d+$', val):
            parsed = int(val)
        elif val in ("true", "false"):
            parsed = val == "true"
        else:
            parsed = val
        node = result
        for part in section:
            node = node.setdefault(part, {})
        node[key] = parsed
    return result

def load_config() -> dict:
    ensure_config()
    try:
        import tomllib
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        pass
    try:
        import tomli
        with open(CONFIG_FILE, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass
    return _parse_toml_simple(CONFIG_FILE.read_text())

def cfg_get(cfg: dict, *keys, default=None):
    node = cfg
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k, default)
        if node is None:
            return default
    return node

CFG = load_config()

PROJECTS_DIR  = Path(os.path.expanduser(cfg_get(CFG, "paths", "projects_dir", default=str(Path.home() / "Projects"))))
_extra_raw    = cfg_get(CFG, "paths", "extra_scan_dirs", default=["~/Documents", "~/Desktop"])
DEV_DIRS      = [PROJECTS_DIR] + [Path(os.path.expanduser(p)) for p in _extra_raw]
HUD_REFRESH   = int(cfg_get(CFG, "general", "hud_refresh",    default=3))
REPOS_REFRESH = int(cfg_get(CFG, "general", "repos_refresh",  default=10))
STATS_REFRESH = int(cfg_get(CFG, "general", "stats_refresh",  default=4))
APP_TITLE     = cfg_get(CFG, "general", "title", default="devpanel — Linux Dev Companion")
WARN_TEMP     = int(cfg_get(CFG, "thermal", "warn_temp", default=60))
CRIT_TEMP     = int(cfg_get(CFG, "thermal", "crit_temp", default=80))
PING_HOSTS    = cfg_get(CFG, "network", "ping_hosts", default=["8.8.8.8", "1.1.1.1", "google.com"])
if not isinstance(PING_HOSTS, list):
    PING_HOSTS = ["8.8.8.8", "1.1.1.1", "google.com"]

_profiles_raw = cfg_get(CFG, "workspace", "profiles", default={})
WORKSPACE_PROFILES: dict = {}
for vid_pid, items in (_profiles_raw.items() if isinstance(_profiles_raw, dict) else {}.items()):
    if isinstance(items, list) and len(items) >= 1:
        WORKSPACE_PROFILES[vid_pid] = (items[0], items[1:])
if not WORKSPACE_PROFILES:
    WORKSPACE_PROFILES = {
        "10c4:ea60": ("ESP32 (CP2102)",  ["code", "python3 -m serial.tools.miniterm"]),
        "1a86:7523": ("Arduino (CH340)", ["arduino-ide"]),
        "0403:6001": ("FTDI Device",     ["code"]),
    }

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

def set_governor_direct(gov: str) -> tuple:
    cpu_count = psutil.cpu_count(logical=True)
    ok_count, last_err = 0, ""
    for i in range(cpu_count):
        path = f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"
        try:
            with open(path, "w") as f:
                f.write(gov)
            ok_count += 1
        except PermissionError:
            last_err = "permission"
        except FileNotFoundError:
            last_err = "not_found"
        except Exception as e:
            last_err = str(e)
    if ok_count == cpu_count:
        return True, f"✔ Governor → [bold]{gov}[/] on all {cpu_count} CPUs"
    elif ok_count > 0:
        return True, f"✔ Governor → [bold]{gov}[/] on {ok_count}/{cpu_count} CPUs"
    elif last_err == "permission":
        return False, "[yellow]⚠ Permission denied — add sudoers rule for cpufreq[/]"
    elif last_err == "not_found":
        return False, "[yellow]⚠ cpufreq not available on this CPU[/]"
    else:
        return False, f"[red]✖ {last_err}[/]"

def get_serial_ports() -> list:
    ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    return sorted(ports) if ports else ["None detected"]

def get_git_status(path: Path) -> dict:
    if not (path / ".git").exists():
        return {}
    branch = run(f"git -C '{path}' rev-parse --abbrev-ref HEAD")
    dirty  = run(f"git -C '{path}' status --porcelain")
    last   = run(f"git -C '{path}' log -1 --format='%cr | %s'")
    ahead  = run(f"git -C '{path}' rev-list @{{u}}..HEAD --count 2>/dev/null") or "0"
    return {"branch": branch, "dirty": bool(dirty), "last": last, "ahead": int(ahead)}

def get_all_repos() -> list:
    repos, seen = [], set()
    for base in DEV_DIRS:
        if not base.exists():
            continue
        st = get_git_status(base)
        if st and str(base) not in seen:
            repos.append((base.name, str(base), st))
            seen.add(str(base))
        try:
            for sub in sorted(base.iterdir()):
                if sub.is_dir() and not sub.name.startswith(".") and str(sub) not in seen:
                    st = get_git_status(sub)
                    if st:
                        repos.append((sub.name, str(sub), st))
                        seen.add(str(sub))
        except PermissionError:
            pass
    return repos

def get_thermal() -> list:
    sensors = []
    try:
        for chip, entries in psutil.sensors_temperatures().items():
            for e in entries:
                sensors.append({"chip": chip, "label": e.label or chip,
                                 "current": e.current, "high": e.high or WARN_TEMP,
                                 "critical": e.critical or CRIT_TEMP})
    except Exception:
        pass
    return sensors

def get_fans() -> list:
    fans = []
    try:
        for chip, entries in psutil.sensors_fans().items():
            for e in entries:
                fans.append({"chip": chip, "label": e.label or chip, "rpm": e.current})
    except Exception:
        pass
    return fans

def get_top_procs(n: int = 10) -> list:
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]):
        try:
            procs.append(p.info)
        except Exception:
            pass
    return sorted(procs, key=lambda x: x["memory_percent"] or 0, reverse=True)[:n]

def get_usb_devices() -> list:
    devices = []
    for line in run("lsusb").splitlines():
        parts = line.split()
        if len(parts) >= 6:
            devices.append({"id": parts[5], "name": " ".join(parts[6:])})
    return devices

def get_systemd_blame() -> list:
    out = run("systemd-analyze blame --no-pager 2>/dev/null | head -20")
    services = []
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            services.append({"time": parts[0], "service": parts[1]})
    return services

def get_boot_time() -> str:
    return run("systemd-analyze 2>/dev/null | head -1") or "N/A"

def bar(val, max_val, width=20, fill="█", empty="░") -> str:
    filled = int((val / max(max_val, 1)) * width)
    return fill * filled + empty * (width - filled)

def temp_color(t: float) -> str:
    return "green" if t < WARN_TEMP else ("yellow" if t < CRIT_TEMP else "red")

# ─────────────────────────────────────────────────────────────────────────────
# NETWORK HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_net_prev: dict = {}
_net_prev_time: float = 0.0

def get_net_speed() -> dict:
    """Returns per-interface bytes/sec upload and download since last call."""
    global _net_prev, _net_prev_time
    now   = time.monotonic()
    stats = psutil.net_io_counters(pernic=True)
    speed = {}
    dt    = now - _net_prev_time if _net_prev_time else 1.0
    for iface, s in stats.items():
        prev = _net_prev.get(iface)
        if prev and dt > 0:
            tx = max(0, s.bytes_sent - prev.bytes_sent) / dt
            rx = max(0, s.bytes_recv - prev.bytes_recv) / dt
        else:
            tx, rx = 0.0, 0.0
        speed[iface] = {"tx": tx, "rx": rx,
                        "tx_total": s.bytes_sent, "rx_total": s.bytes_recv,
                        "errin": s.errin, "errout": s.errout,
                        "dropin": s.dropin, "dropout": s.dropout}
    _net_prev      = stats
    _net_prev_time = now
    return speed

def fmt_speed(bps: float) -> str:
    """Format bytes/sec → human readable."""
    if bps >= 1024 ** 2:
        return f"{bps / 1024**2:.1f} MB/s"
    elif bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps:.0f} B/s"

def fmt_bytes(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024**3:.2f} GB"
    elif b >= 1024 ** 2:
        return f"{b / 1024**2:.1f} MB"
    elif b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"

def get_active_connections(limit: int = 12) -> list:
    """Returns list of active TCP ESTABLISHED connections."""
    conns = []
    try:
        for c in psutil.net_connections(kind="tcp"):
            if c.status == "ESTABLISHED" and c.raddr:
                try:
                    name = psutil.Process(c.pid).name() if c.pid else "?"
                except Exception:
                    name = "?"
                conns.append({
                    "laddr": f"{c.laddr.ip}:{c.laddr.port}",
                    "raddr": f"{c.raddr.ip}:{c.raddr.port}",
                    "pid":   c.pid or 0,
                    "name":  name,
                })
    except Exception:
        pass
    return conns[:limit]

def get_open_ports(limit: int = 10) -> list:
    """Returns listening TCP/UDP ports."""
    ports = []
    seen  = set()
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status in ("LISTEN", "") and c.laddr:
                key = (c.laddr.port, c.type)
                if key not in seen:
                    seen.add(key)
                    try:
                        name = psutil.Process(c.pid).name() if c.pid else "system"
                    except Exception:
                        name = "system"
                    proto = "TCP" if c.type == 1 else "UDP"
                    ports.append({"port": c.laddr.port, "proto": proto, "name": name})
    except Exception:
        pass
    return sorted(ports, key=lambda x: x["port"])[:limit]

def ping_host(host: str) -> str:
    """Ping a host once, return latency string or 'timeout'."""
    try:
        out = subprocess.check_output(
            ["ping", "-c", "1", "-W", "1", host],
            stderr=subprocess.DEVNULL, text=True, timeout=2
        )
        for line in out.splitlines():
            if "time=" in line:
                ms = line.split("time=")[1].split()[0]
                return f"{float(ms):.1f} ms"
        return "ok"
    except Exception:
        return "timeout"

def get_wifi_info() -> dict:
    """Returns SSID, signal strength, frequency via iwconfig/iw."""
    info = {"ssid": "", "signal": "", "freq": "", "iface": ""}
    for iface in run("ls /sys/class/net").split():
        if iface.startswith(("w", "wl")):
            info["iface"] = iface
            info["ssid"]  = run(f"iwgetid {iface} -r") or ""
            iw = run(f"iw dev {iface} link 2>/dev/null")
            for line in iw.splitlines():
                line = line.strip()
                if "signal:" in line:
                    info["signal"] = line.split("signal:")[1].strip()
                elif "freq:" in line:
                    info["freq"] = line.split("freq:")[1].strip() + " MHz"
            break
    return info

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

class HUDTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="hud-body")

    def on_mount(self) -> None:
        self.refresh_hud()
        self.set_interval(HUD_REFRESH, self.refresh_hud)

    def refresh_hud(self) -> None:
        cpu      = psutil.cpu_percent(interval=None)
        ram      = psutil.virtual_memory()
        swap     = psutil.swap_memory()
        disk     = psutil.disk_usage("/")
        net      = psutil.net_io_counters()
        uptime_s = int(datetime.now().timestamp() - psutil.boot_time())
        uptime   = f"{uptime_s//3600}h {(uptime_s%3600)//60}m"
        wifi     = run("iwgetid -r") or "Not connected"
        ports    = get_serial_ports()
        cwd      = Path.cwd()
        git      = get_git_status(cwd)
        temps    = get_thermal()
        cpu_temp = next(
            (s["current"] for s in temps
             if any(k in s["label"].lower() for k in ["cpu","core","package","tdie","tctl"])),
            None
        )
        cpu_cls  = "green" if cpu < 60 else ("yellow" if cpu < 85 else "red")
        ram_cls  = "green" if ram.percent < 70 else ("yellow" if ram.percent < 90 else "red")
        disk_cls = "green" if disk.percent < 80 else ("yellow" if disk.percent < 90 else "red")
        temp_str = f"  Temp: [{temp_color(cpu_temp)}]{cpu_temp:.1f}°C[/]" if cpu_temp else ""
        as_str   = "[green]root[/]" if os.geteuid() == 0 else "[dim]user[/]"
        git_str  = ""
        if git:
            dirty = " [yellow][dirty][/]" if git["dirty"] else " [green][clean][/]"
            ahead = f" [cyan]↑{git['ahead']}[/]" if git["ahead"] else ""
            git_str = f"\n  Branch : [bold]{git['branch']}[/]{dirty}{ahead}\n  Last   : {git['last']}"
        self.query_one("#hud-body", Static).update(
            f"[bold cyan]╔══ SYSTEM HUD ═════════════════════════════════════╗[/]\n"
            f"[bold cyan]║[/] {datetime.now().strftime('%H:%M:%S')}  Uptime: {uptime}  As: {as_str}  "
            f"[dim]{DISTRO['name']} {DISTRO['version']} • devpanel v{__version__}[/]\n"
            f"[bold cyan]╚════════════════════════════════════════════════╝[/]\n\n"
            f"[bold]── CPU & Memory ──────────────────────────────[/]\n"
            f"  CPU    : [{cpu_cls}]{cpu:5.1f}%[/]  {bar(cpu,100)}{temp_str}\n"
            f"  RAM    : [{ram_cls}]{ram.percent:5.1f}%[/]  {bar(ram.percent,100)}  {ram.used//1024**2}MB / {ram.total//1024**2}MB\n"
            f"  Swap   : {swap.percent:5.1f}%  {bar(swap.percent,100)}\n"
            f"  Disk / : [{disk_cls}]{disk.percent:5.1f}%[/]  {bar(disk.percent,100)}  {disk.used//1024**3:.1f}GB / {disk.total//1024**3:.1f}GB\n\n"
            f"[bold]── Network ───────────────────────────────────[/]\n"
            f"  WiFi   : [cyan]{wifi}[/]\n"
            f"  Net ↑   : {net.bytes_sent//1024**2} MB  ↓ {net.bytes_recv//1024**2} MB\n\n"
            f"[bold]── Serial Ports ──────────────────────────────[/]\n"
            f"  Ports  : [yellow]{', '.join(ports)}[/]\n\n"
            f"[bold]── Git (CWD: {cwd.name}) ──────────────────────[/]"
            + (git_str if git_str else "\n  Not a git repo")
        )


class ReposTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="repos-body")

    def on_mount(self) -> None:
        self.refresh_repos()
        self.set_interval(REPOS_REFRESH, self.refresh_repos)

    def refresh_repos(self) -> None:
        repos   = get_all_repos()
        scanned = ', '.join(str(d) for d in DEV_DIRS if d.exists())
        lines   = [
            "[bold cyan]╔══ GIT REPO MONITOR ════════════════════════════╗[/]",
            f"[bold cyan]║[/] Scanning: {scanned}",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
        ]
        if not repos:
            lines.append("[yellow]No git repos found. Check paths in ~/.devpanel/config.toml[/]")
        for name, path, st in repos:
            dirty = "[yellow]✎ dirty[/]" if st["dirty"] else "[green]✔ clean[/]"
            ahead = f" [cyan]↑{st['ahead']} ahead[/]" if st["ahead"] else ""
            lines.append(f"[bold]{name}[/]  [dim][{st['branch']}][/]  {dirty}{ahead}")
            lines.append(f"  [dim]{path}[/]")
            if st["last"]:
                lines.append(f"  Last: {st['last']}")
            lines.append("")
        self.query_one("#repos-body", Static).update("\n".join(lines))


class ThermalTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="thermal-body")
        yield Static(id="thermal-status")
        yield Static("\n[bold]── Power Profiles ────────────────────────────[/]")
        yield Static(id="profile-info")
        yield Static(f"  [dim]Thresholds: warn={WARN_TEMP}°C  crit={CRIT_TEMP}°C  (edit ~/.devpanel/config.toml)[/]\n"
                     "  [dim]For cpufreq: add sudoers rule — see README[/]")
        yield Button("⚡ Performance", id="btn-perf",  variant="warning")
        yield Button("⚖  Balanced",    id="btn-bal",   variant="primary")
        yield Button("🔋 Power Save",   id="btn-save",  variant="success")

    def on_mount(self) -> None:
        self.refresh_thermal()
        self.set_interval(STATS_REFRESH, self.refresh_thermal)

    def refresh_thermal(self) -> None:
        sensors = get_thermal()
        fans    = get_fans()
        gov     = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null") or "unknown"
        freq    = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null")
        avail   = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null") or "N/A"
        freq_mhz = f"{int(freq)//1000} MHz" if freq else "unknown"
        lines = [
            "[bold cyan]╔══ THERMAL MONITOR ═════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", ""
        ]
        if sensors:
            lines.append("[bold]── Temperature Sensors ───────────────────────[/]")
            for s in sensors:
                t = s["current"]
                lines.append(f"  {s['label']:<22} [{temp_color(t)}]{t:5.1f}°C[/]  {bar(t, s['critical'] or CRIT_TEMP, 16)}  (crit:{s['critical']}°C)")
        else:
            lines.append("  [dim]No temperature sensors found.[/]")
        if fans:
            lines.append("\n[bold]── Fan Speeds ────────────────────────────────[/]")
            for f in fans:
                lines.append(f"  {f['label']:<22} {f['rpm']} RPM")
        else:
            lines.append("\n  [dim]No fan sensors reported.[/]")
        lines += [
            "\n[bold]── CPU Frequency ─────────────────────────────[/]",
            f"  Governor  : [cyan]{gov}[/]",
            f"  Cur Freq  : [cyan]{freq_mhz}[/]",
            f"  Available : [dim]{avail}[/]",
        ]
        self.query_one("#thermal-body", Static).update("\n".join(lines))
        self.query_one("#profile-info", Static).update(f"  Active: [bold cyan]{gov}[/]")

    def _set_governor(self, gov: str) -> None:
        sw = self.query_one("#thermal-status", Static)
        sw.update(f"  [dim]Setting {gov}...[/]")
        ok, msg = set_governor_direct(gov)
        sw.update(f"  {msg}")
        self.refresh_thermal()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {"btn-perf": "performance", "btn-bal": "schedutil", "btn-save": "powersave"}
        if event.button.id in mapping:
            self._set_governor(mapping[event.button.id])


class MemoryTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="mem-body")
        yield Button("🧹 Kill Zombie Processes", id="btn-kill", variant="error")

    def on_mount(self) -> None:
        self.refresh_mem()
        self.set_interval(STATS_REFRESH, self.refresh_mem)

    def refresh_mem(self) -> None:
        ram, swap = psutil.virtual_memory(), psutil.swap_memory()
        procs = get_top_procs(10)
        lines = [
            "[bold cyan]╔══ MEMORY INSPECTOR ════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
            "[bold]── RAM Overview ──────────────────────────────[/]",
            f"  Total  : {ram.total//1024**2} MB",
            f"  Used   : {ram.used//1024**2} MB  ({ram.percent}%)  {bar(ram.percent,100,18)}",
            f"  Free   : {ram.available//1024**2} MB",
        ]
        if hasattr(ram, "cached"):
            lines.append(f"  Cached : {ram.cached//1024**2} MB")
        lines.append(f"  Swap   : {swap.used//1024**2} MB / {swap.total//1024**2} MB  ({swap.percent}%)")
        lines += [
            "\n[bold]── Top Processes by RAM ──────────────────────[/]",
            f"  {'PID':<7} {'Name':<22} {'RAM%':>6}  {'CPU%':>6}  Status",
            "  " + "─" * 56,
        ]
        for p in procs:
            col = "red" if (p["memory_percent"] or 0) > 10 else ("yellow" if (p["memory_percent"] or 0) > 4 else "green")
            lines.append(f"  {p['pid']:<7} {p['name'][:22]:<22} [{col}]{p['memory_percent'] or 0:5.1f}%[/]  {p['cpu_percent'] or 0:5.1f}%  {p['status']}")
        zombies = [p for p in psutil.process_iter(["status"]) if p.info.get("status") == "zombie"]
        lines.append(f"\n  Zombie processes: [{'red' if zombies else 'green'}]{len(zombies)}[/]")
        self.query_one("#mem-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-kill":
            killed = 0
            for p in psutil.process_iter(["status", "pid"]):
                try:
                    if p.info["status"] == "zombie":
                        p.kill()
                        killed += 1
                except Exception:
                    pass
            self.query_one("#mem-body", Static).update(f"[green]✔ Cleaned {killed} zombie process(es).[/]")
            self.set_timer(2, self.refresh_mem)


class BootTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="boot-body")

    def on_mount(self) -> None:
        self.refresh_boot()

    def refresh_boot(self) -> None:
        services = get_systemd_blame()
        lines = [
            "[bold cyan]╔══ BOOT OPTIMIZER ══════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
            "[bold]── Boot Summary ──────────────────────────────[/]",
            f"  {get_boot_time()}\n",
        ]
        if services:
            lines += [
                "[bold]── Slowest Services ────────────────────────────────[/]",
                f"  {'Time':<14} Service", "  " + "─" * 46,
            ]
            for s in services[:15]:
                try:
                    digits = int(''.join(filter(str.isdigit, s["time"].split(".")[0])) or "0")
                    col = "red" if "min" in s["time"] else ("yellow" if digits > 2000 else "green")
                except Exception:
                    col = "white"
                lines.append(f"  [{col}]{s['time']:<14}[/] {s['service']}")
        else:
            lines.append("  [dim]systemd-analyze not available. Try: sudo devpanel[/]")
        lines += [
            "\n[bold]── Quick Actions ─────────────────────────────[/]",
            "  [cyan]sudo systemctl disable <service>[/]   ← disable slow service",
            "  [cyan]sudo systemctl mask <service>[/]      ← mask completely",
        ]
        self.query_one("#boot-body", Static).update("\n".join(lines))


class WorkspaceTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="ws-body")
        yield Button("🔄 Refresh", id="btn-refresh-ws", variant="primary")

    def on_mount(self) -> None:
        self.refresh_ws()

    def refresh_ws(self) -> None:
        devices, ports = get_usb_devices(), get_serial_ports()
        lines = [
            "[bold cyan]╔══ WORKSPACE LAUNCHER ══════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
            "[bold]── USB Devices ────────────────────────────────[/]",
        ]
        for d in (devices or [{"id": "-", "name": "[dim]None detected[/]"}]):
            matched = WORKSPACE_PROFILES.get(d["id"])
            tag = f"  [green]→ {matched[0]}[/]" if matched else ""
            lines.append(f"  [cyan]{d['id']}[/]  {d['name']}{tag}")
        lines.append("\n[bold]── Serial Ports ──────────────────────────────[/]")
        for p in ports:
            lines.append(f"  [yellow]{p}[/]")
        lines.append("\n[bold]── Matched Profiles ────────────────────────────────[/]")
        matched_any = False
        for d in devices:
            profile = WORKSPACE_PROFILES.get(d["id"])
            if profile:
                matched_any = True
                label, cmds = profile
                lines.append(f"  [bold green]✔ {label}[/]")
                for cmd in cmds:
                    lines.append(f"    [cyan]$ {cmd}[/]")
        if not matched_any:
            lines.append(f"  [dim]No known boards detected. Add profiles in {CONFIG_FILE}[/]")
        lines.append("\n[bold]── Projects ────────────────────────────────────────[/]")
        if PROJECTS_DIR.exists():
            for d in sorted(d for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith("."))[:12]:
                git = get_git_status(d)
                tag = f" [dim](git:{git['branch']})[/]" if git else ""
                lines.append(f"  [cyan]{d.name}[/]{tag}  →  {d}")
        else:
            lines.append(f"  [yellow]Not found: {PROJECTS_DIR}  — edit {CONFIG_FILE}[/]")
        self.query_one("#ws-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-ws":
            self.refresh_ws()


class NetworkTab(Static):
    """Phase 6 — Network & Connectivity Tab."""

    _ping_results: dict = {}

    def compose(self) -> ComposeResult:
        yield Static(id="net-body")
        yield Static(id="net-ping-status")
        yield Button("📡 Ping Hosts",   id="btn-ping",    variant="primary")
        yield Button("🔄 Refresh",       id="btn-net-ref", variant="success")

    def on_mount(self) -> None:
        self.refresh_net()
        self.set_interval(STATS_REFRESH, self.refresh_net)

    def refresh_net(self) -> None:
        speeds   = get_net_speed()
        conns    = get_active_connections(12)
        ports    = get_open_ports(10)
        wifi     = get_wifi_info()

        lines = [
            "[bold cyan]╔══ NETWORK & CONNECTIVITY ══════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
        ]

        # WiFi info
        if wifi["ssid"]:
            sig_col = "green"
            try:
                sig_val = int(wifi["signal"].split()[0])
                sig_col = "green" if sig_val >= -60 else ("yellow" if sig_val >= -75 else "red")
            except Exception:
                pass
            lines += [
                "[bold]── WiFi ──────────────────────────────────────[/]",
                f"  Interface : [cyan]{wifi['iface']}[/]",
                f"  SSID      : [bold]{wifi['ssid']}[/]",
                f"  Signal    : [{sig_col}]{wifi['signal']}[/]",
                f"  Frequency : {wifi['freq']}",
                "",
            ]
        else:
            lines += ["[bold]── WiFi ──────────────────────────────────────[/]",
                      "  [dim]No wireless interface detected[/]", ""]

        # Per-interface bandwidth
        lines.append("[bold]── Live Bandwidth (per interface) ────────────[/]")
        lines.append(f"  {'Interface':<14} {'↑ Upload':>12}  {'↓ Download':>12}  {'TX Total':>10}  {'RX Total':>10}")
        lines.append("  " + "─" * 66)
        for iface, s in speeds.items():
            if s["tx_total"] == 0 and s["rx_total"] == 0:
                continue
            tx_col = "yellow" if s["tx"] > 512*1024 else "green"
            rx_col = "yellow" if s["rx"] > 512*1024 else "cyan"
            err_str = f"  [red]errs:{s['errin']+s['errout']}[/]" if s["errin"] + s["errout"] > 0 else ""
            lines.append(
                f"  {iface:<14} [{tx_col}]{fmt_speed(s['tx']):>12}[/]  [{rx_col}]{fmt_speed(s['rx']):>12}[/]  "
                f"{fmt_bytes(s['tx_total']):>10}  {fmt_bytes(s['rx_total']):>10}{err_str}"
            )
        lines.append("")

        # Active connections
        lines += [
            "[bold]── Active TCP Connections ────────────────────[/]",
            f"  {'Process':<18} {'Local':>22}  {'Remote':>22}  PID",
            "  " + "─" * 68,
        ]
        if conns:
            for c in conns:
                lines.append(f"  {c['name'][:18]:<18} {c['laddr']:>22}  {c['raddr']:>22}  {c['pid']}")
        else:
            lines.append("  [dim]No established connections (or needs root for full list)[/]")
        lines.append("")

        # Open/listening ports
        lines += [
            "[bold]── Listening Ports ───────────────────────────[/]",
            f"  {'Port':<8} {'Proto':<6} Process",
            "  " + "─" * 36,
        ]
        if ports:
            for p in ports:
                lines.append(f"  {p['port']:<8} {p['proto']:<6} {p['name']}")
        else:
            lines.append("  [dim]No listening ports found[/]")
        lines.append("")

        # Ping results (cached from last run)
        if self._ping_results:
            lines.append("[bold]── Ping Results ──────────────────────────────[/]")
            for host, latency in self._ping_results.items():
                col = "green" if "ms" in latency else "red"
                lines.append(f"  {host:<28} [{col}]{latency}[/]")
        else:
            lines.append("[dim]  Press 📡 Ping Hosts to test connectivity[/]")

        self.query_one("#net-body", Static).update("\n".join(lines))

    def _do_ping(self) -> None:
        status = self.query_one("#net-ping-status", Static)
        status.update("  [dim]Pinging...[/]")
        results = {}
        for host in PING_HOSTS:
            results[host] = ping_host(host)
        self._ping_results = results
        status.update("  [green]✔ Ping complete[/]")
        self.refresh_net()
        self.set_timer(3, lambda: status.update(""))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ping":
            self._do_ping()
        elif event.button.id == "btn-net-ref":
            self.refresh_net()


class ConfigTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="cfg-body")
        yield Button("📂 Open in Editor (nano)", id="btn-edit",   variant="primary")
        yield Button("🔄 Reload Config",         id="btn-reload", variant="success")

    def on_mount(self) -> None:
        self.refresh_cfg()

    def refresh_cfg(self) -> None:
        try:
            content = CONFIG_FILE.read_text()
        except Exception:
            content = ""
        lines = [
            "[bold cyan]╔══ CONFIG VIEWER ══════════════════════════════╗[/]",
            f"[bold cyan]║[/] {CONFIG_FILE}  •  distro: {DISTRO['name']}  pkg: {DISTRO['pkg_manager']}",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
        ]
        for line in content.splitlines():
            if line.startswith("#"):     lines.append(f"[dim]{line}[/]")
            elif line.startswith("["): lines.append(f"[bold yellow]{line}[/]")
            elif "=" in line:
                k, _, v = line.partition("=")
                lines.append(f"  [cyan]{k.rstrip()}[/] =[green]{v}[/]")
            else:                         lines.append(line)
        self.query_one("#cfg-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-edit":
            term = DISTRO["terminal"]
            if term and shutil.which(term):
                if term in ("xfce4-terminal", "gnome-terminal", "tilix"):
                    subprocess.Popen([term, "--", "nano", str(CONFIG_FILE)])
                elif term == "konsole":
                    subprocess.Popen([term, "-e", "nano", str(CONFIG_FILE)])
                else:
                    subprocess.Popen([term, "-e", f"nano {CONFIG_FILE}"])
            else:
                self.query_one("#cfg-body", Static).update(
                    f"[yellow]Open manually:\n  nano {CONFIG_FILE}[/]"
                )
        elif event.button.id == "btn-reload":
            self.query_one("#cfg-body", Static).update(
                "[green]✔ Restart devpanel to apply config changes.[/]"
            )
            self.set_timer(2, self.refresh_cfg)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

class DevPanel(App):
    CSS = """
    Screen { background: $background; }
    TabbedContent { height: 1fr; }
    TabPane { overflow-y: auto; padding: 0; }
    Button { margin: 0 1 1 2; }
    """
    TITLE = APP_TITLE
    BINDINGS = [
        ("q", "quit",                   "Quit"),
        ("1", "switch_tab('hud')",       "HUD"),
        ("2", "switch_tab('repos')",     "Repos"),
        ("3", "switch_tab('thermal')",   "Thermal"),
        ("4", "switch_tab('memory')",    "Memory"),
        ("5", "switch_tab('boot')",      "Boot"),
        ("6", "switch_tab('workspace')", "Workspace"),
        ("7", "switch_tab('network')",   "Network"),
        ("8", "switch_tab('config')",    "Config"),
        ("r", "refresh_all",             "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="hud"):
            with TabPane("[1] HUD",       id="hud"):       yield HUDTab()
            with TabPane("[2] Repos",     id="repos"):     yield ReposTab()
            with TabPane("[3] Thermal",   id="thermal"):   yield ThermalTab()
            with TabPane("[4] Memory",    id="memory"):    yield MemoryTab()
            with TabPane("[5] Boot",      id="boot"):      yield BootTab()
            with TabPane("[6] Workspace", id="workspace"): yield WorkspaceTab()
            with TabPane("[7] Network",   id="network"):   yield NetworkTab()
            with TabPane("[8] Config",    id="config"):    yield ConfigTab()
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_refresh_all(self) -> None:
        refresh_map = {
            HUDTab: "refresh_hud", ReposTab: "refresh_repos",
            ThermalTab: "refresh_thermal", MemoryTab: "refresh_mem",
            BootTab: "refresh_boot", WorkspaceTab: "refresh_ws",
            NetworkTab: "refresh_net", ConfigTab: "refresh_cfg",
        }
        for cls, method in refresh_map.items():
            try:
                getattr(self.query_one(cls), method)()
            except Exception:
                pass


def main():
    """Entry point for pipx / pip install."""
    DevPanel().run()


if __name__ == "__main__":
    main()
