#!/usr/bin/env python3
"""
devpanel — Lightweight Linux Dev Companion TUI
Phase 2: config.toml system, auto-generated on first run
Author: Varun Sukumar K (@varunsukumar060)
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, Button
from textual.reactive import reactive

import psutil
import subprocess
import os
import glob
import shutil
import platform
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_DIR  = Path.home() / ".devpanel"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
# devpanel configuration file
# Location: ~/.devpanel/config.toml
# Edit freely — devpanel reads this on every launch.

[general]
# App title shown in the header
title = "devpanel — Linux Dev Companion"
# How often the HUD refreshes (seconds)
hud_refresh = 3
# How often the Repos tab rescans (seconds)
repos_refresh = 10
# How often Memory/Thermal refresh (seconds)
stats_refresh = 4

[paths]
# Your primary projects directory
projects_dir = "{projects_dir}"
# Additional directories to scan for git repos (comma-separated in the list)
extra_scan_dirs = [
    "~/Documents",
    "~/Desktop",
]

[workspace]
# USB device profiles: "vendor_id:product_id" = ["label", "cmd1", "cmd2"]
# Find your device IDs by running: lsusb
[workspace.profiles]
"10c4:ea60" = ["ESP32 (CP2102)",  "code",  "python3 -m serial.tools.miniterm"]
"1a86:7523" = ["Arduino (CH340)", "arduino-ide"]
"0403:6001" = ["FTDI Device",     "code"]
"2341:0043" = ["Arduino Uno",     "arduino-ide"]
"2341:0010" = ["Arduino Mega",    "arduino-ide"]

[thermal]
# Temperature thresholds (Celsius) for colour coding
warn_temp  = 60
crit_temp  = 80
"""


def _detect_projects_dir() -> str:
    """Best-guess projects directory for the current user."""
    candidates = [
        Path.home() / "Project",
        Path.home() / "Projects",
        Path.home() / "projects",
        Path.home() / "dev",
        Path.home() / "code",
        Path.home() / "workspace",
        Path.home() / "Documents" / "Projects",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return str(Path.home() / "Projects")   # fallback — will be created on first use


def ensure_config() -> None:
    """Create ~/.devpanel/config.toml if it doesn't exist yet."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        projects = _detect_projects_dir()
        CONFIG_FILE.write_text(DEFAULT_CONFIG.format(projects_dir=projects))
        print(f"\n✔  Created default config: {CONFIG_FILE}")
        print(    "    Edit it to customise paths, USB profiles, and thresholds.\n")


def load_config() -> dict:
    """
    Parse config.toml with the stdlib only (no tomllib dependency on Py<3.11).
    Returns a plain dict mirroring the TOML structure.
    """
    ensure_config()
    try:
        # Python 3.11+ ships tomllib in stdlib
        import tomllib
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        pass
    try:
        # Popular third-party fallback
        import tomli
        with open(CONFIG_FILE, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass
    # Minimal hand-rolled TOML parser (handles the subset we need)
    return _parse_toml_simple(CONFIG_FILE.read_text())


def _parse_toml_simple(text: str) -> dict:
    """
    Minimal TOML parser for the devpanel config subset:
      - [section] / [section.sub] headers
      - key = "string"  /  key = integer  /  key = ["list", ...]
    Enough for our config; not a full TOML implementation.
    """
    import re
    result: dict = {}
    section: list[str] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Section header
        m = re.match(r'^\[([\w.]+)\]$', line)
        if m:
            section = m.group(1).split(".")
            node = result
            for part in section:
                node = node.setdefault(part, {})
            continue
        # Key = value
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # Inline array
        if val.startswith("["):
            items = re.findall(r'"([^"]+)"', val)
            parsed: object = items
        # Quoted string
        elif val.startswith('"'):
            parsed = val.strip('"')
        # Integer
        elif re.match(r'^-?\d+$', val):
            parsed = int(val)
        # Boolean
        elif val in ("true", "false"):
            parsed = val == "true"
        else:
            parsed = val
        # Navigate to current section and set key
        node = result
        for part in section:
            node = node.setdefault(part, {})
        node[key] = parsed

    return result


def cfg_get(cfg: dict, *keys, default=None):
    """Safe nested key access: cfg_get(cfg, 'paths', 'projects_dir')."""
    node = cfg
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k, default)
        if node is None:
            return default
    return node


# ─────────────────────────────────────────────────────────────────────────────
# LOAD CONFIG (at import time — fast, cached for the session)
# ─────────────────────────────────────────────────────────────────────────────

CFG = load_config()

# Resolved values from config
PROJECTS_DIR = Path(os.path.expanduser(cfg_get(CFG, "paths", "projects_dir", default=str(Path.home() / "Projects"))))
_extra_raw   = cfg_get(CFG, "paths", "extra_scan_dirs", default=["~/Documents", "~/Desktop"])
DEV_DIRS     = [PROJECTS_DIR] + [Path(os.path.expanduser(p)) for p in _extra_raw]

HUD_REFRESH    = int(cfg_get(CFG, "general", "hud_refresh",    default=3))
REPOS_REFRESH  = int(cfg_get(CFG, "general", "repos_refresh",  default=10))
STATS_REFRESH  = int(cfg_get(CFG, "general", "stats_refresh",  default=4))
APP_TITLE      = cfg_get(CFG, "general", "title", default="devpanel — Linux Dev Companion")

WARN_TEMP = int(cfg_get(CFG, "thermal", "warn_temp", default=60))
CRIT_TEMP = int(cfg_get(CFG, "thermal", "crit_temp", default=80))

_profiles_raw = cfg_get(CFG, "workspace", "profiles", default={})
WORKSPACE_PROFILES: dict[str, tuple[str, list[str]]] = {}
for vid_pid, items in (_profiles_raw.items() if isinstance(_profiles_raw, dict) else {}.items()):
    if isinstance(items, list) and len(items) >= 1:
        WORKSPACE_PROFILES[vid_pid] = (items[0], items[1:])

# Fallback built-in profiles if config gave nothing
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

def set_governor_direct(gov: str) -> tuple[bool, str]:
    cpu_count = psutil.cpu_count(logical=True)
    ok_count  = 0
    last_err  = ""
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
        return True,  f"✔ Governor → [bold]{gov}[/] on all {cpu_count} CPUs"
    elif ok_count > 0:
        return True,  f"✔ Governor → [bold]{gov}[/] on {ok_count}/{cpu_count} CPUs"
    elif last_err == "permission":
        return False, (
            f"[yellow]⚠ Permission denied.[/]\n"
            f"  Relaunch with:  [bold]sudo bash run.sh[/]\n"
            f"  Or add a passwordless sudoers rule — see README."
        )
    elif last_err == "not_found":
        return False, "[yellow]⚠ cpufreq not available on this CPU[/]"
    else:
        return False, f"[red]✖ {last_err}[/]"

def get_serial_ports() -> list[str]:
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

def get_all_repos() -> list[tuple]:
    repos = []
    seen  = set()
    for base in DEV_DIRS:
        if not base.exists():
            continue
        st = get_git_status(base)
        if st and str(base) not in seen:
            repos.append((base.name, str(base), st))
            seen.add(str(base))
        for sub in sorted(base.iterdir()):
            if sub.is_dir() and not sub.name.startswith(".") and str(sub) not in seen:
                st = get_git_status(sub)
                if st:
                    repos.append((sub.name, str(sub), st))
                    seen.add(str(sub))
    return repos

def get_thermal() -> list[dict]:
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

def get_fans() -> list[dict]:
    fans = []
    try:
        for chip, entries in psutil.sensors_fans().items():
            for e in entries:
                fans.append({"chip": chip, "label": e.label or chip, "rpm": e.current})
    except Exception:
        pass
    return fans

def get_top_procs(n: int = 10) -> list[dict]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "status"]):
        try:
            procs.append(p.info)
        except Exception:
            pass
    return sorted(procs, key=lambda x: x["memory_percent"] or 0, reverse=True)[:n]

def get_usb_devices() -> list[dict]:
    devices = []
    try:
        for line in run("lsusb").splitlines():
            parts = line.split()
            if len(parts) >= 6:
                devices.append({"id": parts[5], "name": " ".join(parts[6:])})
    except Exception:
        pass
    return devices

def get_systemd_blame() -> list[dict]:
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
    if t < WARN_TEMP:  return "green"
    if t < CRIT_TEMP:  return "yellow"
    return "red"


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
        cpu_cls  = "green" if cpu < 60  else ("yellow" if cpu < 85  else "red")
        ram_cls  = "green" if ram.percent < 70 else ("yellow" if ram.percent < 90 else "red")
        disk_cls = "green" if disk.percent < 80 else ("yellow" if disk.percent < 90 else "red")
        temp_str = f"   Temp: [{temp_color(cpu_temp)}]{cpu_temp:.1f}°C[/]" if cpu_temp else ""
        running_as = "[green]root[/]" if os.geteuid() == 0 else "[dim]user[/]"
        git_str = ""
        if git:
            dirty_tag = " [yellow][dirty][/]" if git["dirty"] else " [green][clean][/]"
            ahead_tag = f" [cyan]↑{git['ahead']}[/]" if git["ahead"] else ""
            git_str = f"\n  Branch : [bold]{git['branch']}[/]{dirty_tag}{ahead_tag}\n  Last   : {git['last']}"

        text = (
            f"[bold cyan]╔══ SYSTEM HUD ═════════════════════════════════════╗[/]\n"
            f"[bold cyan]║[/] {datetime.now().strftime('%H:%M:%S')}  Uptime: {uptime}  As: {running_as}  Config: [dim]{CONFIG_FILE}[/]\n"
            f"[bold cyan]╚════════════════════════════════════════════════╝[/]\n\n"
            f"[bold]── CPU & Memory ──────────────────────────────[/]\n"
            f"  CPU    : [{cpu_cls}]{cpu:5.1f}%[/]  {bar(cpu,100)}{temp_str}\n"
            f"  RAM    : [{ram_cls}]{ram.percent:5.1f}%[/]  {bar(ram.percent,100)}  {ram.used//1024**2}MB / {ram.total//1024**2}MB\n"
            f"  Swap   : {swap.percent:5.1f}%  {bar(swap.percent,100)}\n"
            f"  Disk / : [{disk_cls}]{disk.percent:5.1f}%[/]  {bar(disk.percent,100)}  {disk.used//1024**3:.1f}GB / {disk.total//1024**3:.1f}GB\n\n"
            f"[bold]── Network ───────────────────────────────────[/]\n"
            f"  WiFi   : [cyan]{wifi}[/]\n"
            f"  Net ↑   : {net.bytes_sent//1024**2} MB   ↓ {net.bytes_recv//1024**2} MB\n\n"
            f"[bold]── Serial Ports ──────────────────────────────[/]\n"
            f"  Ports  : [yellow]{', '.join(ports)}[/]\n\n"
            f"[bold]── Git (CWD: {cwd.name}) ──────────────────────[/]"
            + (git_str if git_str else "\n  Not a git repo")
        )
        self.query_one("#hud-body", Static).update(text)


class ReposTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="repos-body")

    def on_mount(self) -> None:
        self.refresh_repos()
        self.set_interval(REPOS_REFRESH, self.refresh_repos)

    def refresh_repos(self) -> None:
        repos = get_all_repos()
        scanned = ', '.join(str(d) for d in DEV_DIRS if d.exists())
        lines = [
            "[bold cyan]╔══ GIT REPO MONITOR ════════════════════════════╗[/]",
            f"[bold cyan]║[/] Scanning: {scanned}",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
        ]
        if not repos:
            lines.append("[yellow]No git repositories found. Check paths in ~/.devpanel/config.toml[/]")
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
        yield Static(
            "  [dim]Thresholds from config: "
            f"warn={WARN_TEMP}°C  crit={CRIT_TEMP}°C  —  edit ~/.devpanel/config.toml to change[/]\n"
            "  [dim]cpufreq buttons need root — relaunch with:  sudo bash run.sh[/]"
        )
        yield Button("⚡ Performance", id="btn-perf",  variant="warning")
        yield Button("⚖  Balanced",    id="btn-bal",   variant="primary")
        yield Button("🔋 Power Save",   id="btn-save",  variant="success")

    def on_mount(self) -> None:
        self.refresh_thermal()
        self.set_interval(STATS_REFRESH, self.refresh_thermal)

    def refresh_thermal(self) -> None:
        sensors = get_thermal()
        fans    = get_fans()
        lines   = [
            "[bold cyan]╔══ THERMAL MONITOR ═════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", ""
        ]
        if sensors:
            lines.append("[bold]── Temperature Sensors ───────────────────────[/]")
            for s in sensors:
                t   = s["current"]
                col = temp_color(t)
                b   = bar(t, s["critical"] or CRIT_TEMP, width=16)
                lines.append(f"  {s['label']:<22} [{col}]{t:5.1f}°C[/]  {b}  (crit: {s['critical']}°C)")
        else:
            lines.append("  [dim]No temperature sensors found.[/]")
        if fans:
            lines.append("\n[bold]── Fan Speeds ────────────────────────────────[/]")
            for f in fans:
                lines.append(f"  {f['label']:<22} {f['rpm']} RPM")
        else:
            lines.append("\n  [dim]No fan sensors reported.[/]")
        gov   = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null") or "unknown"
        freq  = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null")
        avail = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null") or "N/A"
        freq_mhz = f"{int(freq)//1000} MHz" if freq else "unknown"
        lines += [
            "\n[bold]── CPU Frequency ─────────────────────────────[/]",
            f"  Governor  : [cyan]{gov}[/]",
            f"  Cur Freq  : [cyan]{freq_mhz}[/]",
            f"  Available : [dim]{avail}[/]",
        ]
        self.query_one("#thermal-body",  Static).update("\n".join(lines))
        self.query_one("#profile-info",  Static).update(f"  Active: [bold cyan]{gov}[/]")

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
        ram   = psutil.virtual_memory()
        swap  = psutil.swap_memory()
        procs = get_top_procs(10)
        lines = [
            "[bold cyan]╔══ MEMORY INSPECTOR ════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", ""
        ]
        lines += [
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
        boot_time = get_boot_time()
        services  = get_systemd_blame()
        lines = [
            "[bold cyan]╔══ BOOT OPTIMIZER ══════════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", ""
        ]
        lines += [
            "[bold]── Boot Summary ──────────────────────────────[/]",
            f"  {boot_time}\n",
        ]
        if services:
            lines += [
                "[bold]── Slowest Services ────────────────────────────────[/]",
                f"  {'Time':<14} Service",
                "  " + "─" * 46,
            ]
            for s in services[:15]:
                try:
                    digits = int(''.join(filter(str.isdigit, s["time"].split(".")[0])) or "0")
                    col = "red" if "min" in s["time"] else ("yellow" if digits > 2000 else "green")
                except Exception:
                    col = "white"
                lines.append(f"  [{col}]{s['time']:<14}[/] {s['service']}")
        else:
            lines.append("  [dim]systemd-analyze not available or run as root for more detail.[/]")
        lines += [
            "\n[bold]── Quick Actions ─────────────────────────────[/]",
            "  Disable a slow service :",
            "  [cyan]sudo systemctl disable <service>[/]",
            "  Mask completely        :",
            "  [cyan]sudo systemctl mask <service>[/]",
        ]
        self.query_one("#boot-body", Static).update("\n".join(lines))


class WorkspaceTab(Static):
    def compose(self) -> ComposeResult:
        yield Static(id="ws-body")
        yield Button("🔄 Refresh Devices", id="btn-refresh-ws", variant="primary")

    def on_mount(self) -> None:
        self.refresh_ws()

    def refresh_ws(self) -> None:
        devices = get_usb_devices()
        ports   = get_serial_ports()
        lines = [
            "[bold cyan]╔══ WORKSPACE LAUNCHER ══════════════════════════╗[/]",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", ""
        ]
        lines.append("[bold]── Connected USB Devices ─────────────────────[/]")
        for d in (devices or [{"id": "none", "name": "[dim]No USB devices found[/]"}]):
            matched = WORKSPACE_PROFILES.get(d["id"])
            tag = f"  [green]→ {matched[0]}[/]" if matched else ""
            lines.append(f"  [cyan]{d['id']}[/]  {d['name']}{tag}")
        lines.append("\n[bold]── Serial Ports ──────────────────────────────[/]")
        for p in ports:
            lines.append(f"  [yellow]{p}[/]")
        lines.append("\n[bold]── Matched Workspace Profiles ────────────────[/]")
        matched_any = False
        for d in devices:
            profile = WORKSPACE_PROFILES.get(d["id"])
            if profile:
                matched_any = True
                label, cmds = profile
                lines.append(f"  [bold green]✔ {label}[/] detected")
                for cmd in cmds:
                    lines.append(f"    [cyan]$ {cmd}[/]")
        if not matched_any:
            lines.append("  [dim]No known dev boards detected. Plug in your ESP32 or Arduino.[/]")
            lines.append(f"  [dim]Add custom profiles in: {CONFIG_FILE}[/]")
        lines.append("\n[bold]── Project Quick-Access ──────────────────────[/]")
        if PROJECTS_DIR.exists():
            subdirs = sorted(d for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith("."))
            for d in subdirs[:12]:
                git = get_git_status(d)
                tag = f" [dim](git:{git['branch']})[/]" if git else ""
                lines.append(f"  [cyan]{d.name}[/]{tag}  →  {d}")
        else:
            lines.append(f"  [yellow]Projects dir not found: {PROJECTS_DIR}[/]")
            lines.append(f"  [dim]Edit projects_dir in {CONFIG_FILE}[/]")
        self.query_one("#ws-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-ws":
            self.refresh_ws()


class ConfigTab(Static):
    """Live view of the current config file."""
    def compose(self) -> ComposeResult:
        yield Static(id="cfg-body")
        yield Button("📂 Open in Editor  (nano)", id="btn-edit", variant="primary")
        yield Button("🔄 Reload Config",            id="btn-reload", variant="success")

    def on_mount(self) -> None:
        self.refresh_cfg()

    def refresh_cfg(self) -> None:
        try:
            content = CONFIG_FILE.read_text()
        except Exception:
            content = "[red]Config file not found.[/]"
        lines = [
            "[bold cyan]╔══ CONFIG VIEWER ═══════════════════════════════╗[/]",
            f"[bold cyan]║[/] {CONFIG_FILE}",
            "[bold cyan]╚════════════════════════════════════════════════╝[/]", "",
        ]
        for line in content.splitlines():
            if line.startswith("#"):
                lines.append(f"[dim]{line}[/]")
            elif line.startswith("["):
                lines.append(f"[bold yellow]{line}[/]")
            elif "=" in line:
                k, _, v = line.partition("=")
                lines.append(f"  [cyan]{k.rstrip()}[/] = [green]{v.lstrip()}[/]")
            else:
                lines.append(line)
        self.query_one("#cfg-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-edit":
            # Open nano in a new terminal window (doesn’t conflict with TUI)
            term = shutil.which("xterm") or shutil.which("xfce4-terminal") or shutil.which("gnome-terminal")
            if term:
                subprocess.Popen([term, "-e", f"nano {CONFIG_FILE}"])
            else:
                self.query_one("#cfg-body", Static).update(
                    f"[yellow]No terminal emulator found.\nEdit manually:\n  nano {CONFIG_FILE}[/]"
                )
        elif event.button.id == "btn-reload":
            self.query_one("#cfg-body", Static).update(
                "[green]✔ Config reloaded! Restart devpanel to apply all changes.[/]"
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
        ("7", "switch_tab('config')",    "Config"),
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
            with TabPane("[7] Config",    id="config"):    yield ConfigTab()
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_refresh_all(self) -> None:
        refresh_map = {
            HUDTab:       "refresh_hud",
            ReposTab:     "refresh_repos",
            ThermalTab:   "refresh_thermal",
            MemoryTab:    "refresh_mem",
            BootTab:      "refresh_boot",
            WorkspaceTab: "refresh_ws",
            ConfigTab:    "refresh_cfg",
        }
        for cls, method in refresh_map.items():
            try:
                getattr(self.query_one(cls), method)()
            except Exception:
                pass


if __name__ == "__main__":
    DevPanel().run()
