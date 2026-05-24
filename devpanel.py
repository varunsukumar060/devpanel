#!/usr/bin/env python3
"""
devpanel — Lightweight Linux Dev Companion TUI
Phase 1: Tuned for Varun's Linux Mint XFCE setup
Author: Varun Sukumar K (@varunsukumar060)
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static, Button, DataTable, ProgressBar, Label
from textual.reactive import reactive
from textual import work
from textual.timer import Timer

import psutil
import subprocess
import os
import glob
import shutil
import platform
from pathlib import Path
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
PROJECTS_DIR = Path("/home/varun_sukumar/Project")
DEV_DIRS = [PROJECTS_DIR, Path.home() / "Documents", Path.home() / "Desktop"]

# Workspace profiles: USB vendor:product → (label, commands[])
WORKSPACE_PROFILES = {
    "10c4:ea60": ("ESP32 (CP2102)",  ["code", "python3 -m serial.tools.miniterm"]),
    "1a86:7523": ("Arduino (CH340)", ["arduino-ide"]),
    "0403:6001": ("FTDI Device",     ["code"]),
}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def run(cmd: str) -> str:
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

def get_serial_ports() -> list[str]:
    ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
    return sorted(ports) if ports else ["None detected"]

def get_git_status(path: Path) -> dict:
    if not (path / ".git").exists():
        return {}
    branch = run(f"git -C {path} rev-parse --abbrev-ref HEAD")
    dirty  = run(f"git -C {path} status --porcelain")
    last   = run(f"git -C {path} log -1 --format='%cr | %s'")
    ahead  = run(f"git -C {path} rev-list @{{u}}..HEAD --count 2>/dev/null") or "0"
    return {"branch": branch, "dirty": bool(dirty), "last": last, "ahead": int(ahead)}

def get_all_repos() -> list[tuple]:
    repos = []
    for base in DEV_DIRS:
        if not base.exists():
            continue
        # Check the dir itself
        st = get_git_status(base)
        if st:
            repos.append((base.name, str(base), st))
        # Check one level deep
        for sub in sorted(base.iterdir()):
            if sub.is_dir() and not sub.name.startswith("."):
                st = get_git_status(sub)
                if st:
                    repos.append((sub.name, str(sub), st))
    return repos

def get_thermal() -> list[dict]:
    sensors = []
    try:
        temps = psutil.sensors_temperatures()
        for chip, entries in temps.items():
            for e in entries:
                sensors.append({"chip": chip, "label": e.label or chip, "current": e.current, "high": e.high or 80, "critical": e.critical or 100})
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

def get_top_procs(n=8) -> list[dict]:
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
        out = run("lsusb")
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 6:
                vid_pid = parts[5]
                name = " ".join(parts[6:])
                devices.append({"id": vid_pid, "name": name})
    except Exception:
        pass
    return devices

def get_systemd_blame() -> list[dict]:
    try:
        out = run("systemd-analyze blame --no-pager 2>/dev/null | head -20")
        services = []
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                services.append({"time": parts[0], "service": parts[1]})
        return services
    except Exception:
        return []

def get_boot_time() -> str:
    try:
        return run("systemd-analyze 2>/dev/null | head -1")
    except Exception:
        return "N/A"

def bar(val, max_val, width=20, fill="█", empty="░") -> str:
    filled = int((val / max(max_val, 1)) * width)
    return fill * filled + empty * (width - filled)

def temp_color(t: float) -> str:
    if t < 50:  return "green"
    if t < 70:  return "yellow"
    return "red"

# ─── Tab: HUD ─────────────────────────────────────────────────────────────────
class HUDTab(Static):
    DEFAULT_CSS = """
    HUDTab { padding: 1 2; }
    .hud-section { margin-bottom: 1; border: solid $primary-darken-2; padding: 1 2; }
    .hud-title { color: $accent; text-style: bold; }
    .ok   { color: green; }
    .warn { color: yellow; }
    .crit { color: red; }
    """

    content = reactive("Loading...")

    def compose(self) -> ComposeResult:
        yield Static(id="hud-body")

    def on_mount(self) -> None:
        self.refresh_hud()
        self.set_interval(3, self.refresh_hud)

    def refresh_hud(self) -> None:
        cpu   = psutil.cpu_percent(interval=None)
        ram   = psutil.virtual_memory()
        swap  = psutil.swap_memory()
        disk  = psutil.disk_usage("/")
        net   = psutil.net_io_counters()
        uptime_s = int(datetime.now().timestamp() - psutil.boot_time())
        uptime = f"{uptime_s//3600}h {(uptime_s%3600)//60}m"
        wifi  = run("iwgetid -r") or "Not connected"
        ports = get_serial_ports()
        cwd   = Path.cwd()
        git   = get_git_status(cwd)
        temps = get_thermal()
        cpu_temp = next((s["current"] for s in temps if "cpu" in s["label"].lower() or "core" in s["label"].lower() or "package" in s["label"].lower()), None)

        cpu_bar  = bar(cpu, 100)
        ram_bar  = bar(ram.percent, 100)
        disk_bar = bar(disk.percent, 100)

        cpu_cls  = "ok" if cpu < 60 else ("warn" if cpu < 85 else "crit")
        ram_cls  = "ok" if ram.percent < 70 else ("warn" if ram.percent < 90 else "crit")
        disk_cls = "ok" if disk.percent < 80 else ("warn" if disk.percent < 90 else "crit")

        temp_str = f"  CPU Temp : [{temp_color(cpu_temp)}]{cpu_temp:.1f}°C[/]" if cpu_temp else ""

        git_str = ""
        if git:
            dirty_tag = " [yellow][dirty][/]" if git["dirty"] else " [green][clean][/]"
            ahead_tag = f" [cyan]↑{git['ahead']}[/]" if git["ahead"] else ""
            git_str = f"\n  Branch   : [bold]{git['branch']}[/]{dirty_tag}{ahead_tag}\n  Last     : {git['last']}"

        text = f"""[bold cyan]╔══ SYSTEM HUD ══════════════════════════════════╗[/]
[bold cyan]║[/] Updated: {datetime.now().strftime('%H:%M:%S')}   Uptime: {uptime}
[bold cyan]╚════════════════════════════════════════════════╝[/]

[bold]── CPU & Memory ──────────────────────────────[/]
  CPU      : [{cpu_cls}]{cpu:5.1f}%[/]  {cpu_bar}{temp_str}
  RAM      : [{ram_cls}]{ram.percent:5.1f}%[/]  {ram_bar}  {ram.used//1024//1024}MB / {ram.total//1024//1024}MB
  Swap     : {swap.percent:5.1f}%  {bar(swap.percent,100)}
  Disk /   : [{disk_cls}]{disk.percent:5.1f}%[/]  {disk_bar}  {disk.used//1024**3:.1f}GB / {disk.total//1024**3:.1f}GB

[bold]── Network ───────────────────────────────────[/]
  WiFi     : [cyan]{wifi}[/]
  Net ↑    : {net.bytes_sent//1024//1024} MB  ↓ {net.bytes_recv//1024//1024} MB

[bold]── Serial Ports ──────────────────────────────[/]
  Ports    : [yellow]{', '.join(ports)}[/]

[bold]── Git (CWD: {cwd.name}) ──────────────────────[/]{git_str if git_str else chr(10)+"  Not a git repo"}
"""
        self.query_one("#hud-body", Static).update(text)


# ─── Tab: Repos ───────────────────────────────────────────────────────────────
class ReposTab(Static):
    DEFAULT_CSS = """
    ReposTab { padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="repos-body")

    def on_mount(self) -> None:
        self.refresh_repos()
        self.set_interval(10, self.refresh_repos)

    def refresh_repos(self) -> None:
        repos = get_all_repos()
        if not repos:
            self.query_one("#repos-body", Static).update("[yellow]No git repositories found in scanned directories.[/]")
            return

        lines = ["[bold cyan]╔══ GIT REPO MONITOR ════════════════════════════╗[/]"]
        lines.append(f"[bold cyan]║[/] Scanned: {', '.join(str(d) for d in DEV_DIRS if d.exists())}")
        lines.append("[bold cyan]╚════════════════════════════════════════════════╝[/]\n")

        for name, path, st in repos:
            dirty_icon = "[yellow]✎ dirty[/] " if st["dirty"] else "[green]✔ clean[/] "
            ahead_icon = f"[cyan]↑{st['ahead']} ahead[/] " if st["ahead"] else ""
            lines.append(f"[bold]{name}[/]  [{st['branch']}]  {dirty_icon}{ahead_icon}")
            lines.append(f"  [dim]{path}[/]")
            if st["last"]:
                lines.append(f"  Last: {st['last']}")
            lines.append("")

        self.query_one("#repos-body", Static).update("\n".join(lines))


# ─── Tab: Thermal ─────────────────────────────────────────────────────────────
class ThermalTab(Static):
    DEFAULT_CSS = """
    ThermalTab { padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="thermal-body")
        yield Static("\n[bold]── Power Profiles ──────────────────────────────[/]")
        yield Static(id="profile-info")
        yield Button("⚡ Performance",  id="btn-perf",    variant="warning")
        yield Button("⚖  Balanced",    id="btn-bal",     variant="primary")
        yield Button("🔋 Power Save",   id="btn-save",    variant="success")

    def on_mount(self) -> None:
        self.refresh_thermal()
        self.set_interval(3, self.refresh_thermal)

    def refresh_thermal(self) -> None:
        sensors = get_thermal()
        fans    = get_fans()
        lines   = ["[bold cyan]╔══ THERMAL MONITOR ═════════════════════════════╗[/]",
                   "[bold cyan]╚════════════════════════════════════════════════╝[/]",""]

        if sensors:
            lines.append("[bold]── Temperature Sensors ──────────────────────[/]")
            for s in sensors:
                t = s["current"]
                col = temp_color(t)
                b = bar(t, s["critical"] or 100, width=16)
                lines.append(f"  {s['label']:<20} [{col}]{t:5.1f}°C[/]  {b}  (crit: {s['critical'] or '?'}°C)")
        else:
            lines.append("  [dim]No temperature sensors found (try: sudo modprobe coretemp)[/]")

        if fans:
            lines.append("\n[bold]── Fan Speeds ────────────────────────────────[/]")
            for f in fans:
                lines.append(f"  {f['label']:<20} {f['rpm']} RPM")
        else:
            lines.append("\n  [dim]No fan sensors reported[/]")

        gov = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null") or "unknown"
        freq = run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null")
        freq_mhz = f"{int(freq)//1000} MHz" if freq else "unknown"
        lines.append(f"\n[bold]── CPU Frequency ─────────────────────────────[/]")
        lines.append(f"  Governor : [cyan]{gov}[/]")
        lines.append(f"  Cur Freq : [cyan]{freq_mhz}[/]")

        self.query_one("#thermal-body", Static).update("\n".join(lines))
        self.query_one("#profile-info", Static).update(f"  Active governor: [bold cyan]{gov}[/]")

    def _set_governor(self, gov: str) -> None:
        cpu_count = psutil.cpu_count(logical=True)
        for i in range(cpu_count):
            run(f"echo {gov} | sudo tee /sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor > /dev/null")
        self.refresh_thermal()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-perf": self._set_governor("performance")
        elif event.button.id == "btn-bal":  self._set_governor("schedutil")
        elif event.button.id == "btn-save": self._set_governor("powersave")


# ─── Tab: Memory ──────────────────────────────────────────────────────────────
class MemoryTab(Static):
    DEFAULT_CSS = """
    MemoryTab { padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="mem-body")
        yield Button("🧹 Kill Zombie Processes", id="btn-kill", variant="error")

    def on_mount(self) -> None:
        self.refresh_mem()
        self.set_interval(4, self.refresh_mem)

    def refresh_mem(self) -> None:
        ram  = psutil.virtual_memory()
        swap = psutil.swap_memory()
        procs = get_top_procs(10)

        lines = ["[bold cyan]╔══ MEMORY INSPECTOR ════════════════════════════╗[/]",
                 "[bold cyan]╚════════════════════════════════════════════════╝[/]",""]

        lines.append("[bold]── RAM Overview ──────────────────────────────[/]")
        lines.append(f"  Total  : {ram.total//1024**2} MB")
        lines.append(f"  Used   : {ram.used//1024**2} MB  ({ram.percent}%)  {bar(ram.percent,100,18)}")
        lines.append(f"  Free   : {ram.available//1024**2} MB")
        lines.append(f"  Cached : {ram.cached//1024**2} MB" if hasattr(ram,'cached') else "")
        lines.append(f"  Swap   : {swap.used//1024**2} MB / {swap.total//1024**2} MB  ({swap.percent}%)")

        lines.append("\n[bold]── Top Processes by RAM ──────────────────────[/]")
        lines.append(f"  {'PID':<7} {'Name':<22} {'RAM%':>6}  {'CPU%':>6}  {'Status'}")
        lines.append("  " + "─" * 58)
        for p in procs:
            col = "red" if (p["memory_percent"] or 0) > 10 else ("yellow" if (p["memory_percent"] or 0) > 4 else "green")
            lines.append(f"  {p['pid']:<7} {p['name'][:22]:<22} [{col}]{p['memory_percent'] or 0:5.1f}%[/]  {p['cpu_percent'] or 0:5.1f}%  {p['status']}")

        # Zombie count
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
            self.query_one("#mem-body", Static).update(f"[green]✔ Cleaned up {killed} zombie process(es).[/]")
            self.set_timer(2, self.refresh_mem)


# ─── Tab: Boot ────────────────────────────────────────────────────────────────
class BootTab(Static):
    DEFAULT_CSS = """
    BootTab { padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="boot-body")

    def on_mount(self) -> None:
        self.refresh_boot()

    def refresh_boot(self) -> None:
        boot_time = get_boot_time()
        services  = get_systemd_blame()

        lines = ["[bold cyan]╔══ BOOT OPTIMIZER ══════════════════════════════╗[/]",
                 "[bold cyan]╚════════════════════════════════════════════════╝[/]",""]

        lines.append(f"[bold]── Boot Summary ──────────────────────────────[/]")
        lines.append(f"  {boot_time or 'Run: systemd-analyze for details'}\n")

        if services:
            lines.append("[bold]── Slowest Services (systemd-analyze blame) ──[/]")
            lines.append(f"  {'Time':<12} {'Service'}")
            lines.append("  " + "─" * 44)
            for s in services[:15]:
                col = "red" if "min" in s["time"] else ("yellow" if int(s["time"].replace("ms","").replace("s","000").split(".")[0]) > 2000 else "green")
                lines.append(f"  [{col}]{s['time']:<12}[/] {s['service']}")
        else:
            lines.append("  [dim]Run devpanel with sudo for full systemd analysis.[/]")

        lines.append("\n[bold]── Quick Actions ─────────────────────────────[/]")
        lines.append("  To disable a slow service:")
        lines.append("  [cyan]sudo systemctl disable <service-name>[/]")
        lines.append("  To mask completely:")
        lines.append("  [cyan]sudo systemctl mask <service-name>[/]")

        self.query_one("#boot-body", Static).update("\n".join(lines))


# ─── Tab: Workspace ───────────────────────────────────────────────────────────
class WorkspaceTab(Static):
    DEFAULT_CSS = """
    WorkspaceTab { padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="ws-body")
        yield Button("🔄 Refresh Devices", id="btn-refresh-ws", variant="primary")

    def on_mount(self) -> None:
        self.refresh_ws()

    def refresh_ws(self) -> None:
        devices = get_usb_devices()
        ports   = get_serial_ports()

        lines = ["[bold cyan]╔══ WORKSPACE LAUNCHER ══════════════════════════╗[/]",
                 "[bold cyan]╚════════════════════════════════════════════════╝[/]",""]

        lines.append("[bold]── Connected USB Devices ─────────────────────[/]")
        if devices:
            for d in devices:
                matched = WORKSPACE_PROFILES.get(d["id"])
                tag = f"  [green]→ Profile: {matched[0]}[/]" if matched else ""
                lines.append(f"  [cyan]{d['id']}[/]  {d['name']}{tag}")
        else:
            lines.append("  [dim]No USB devices found[/]")

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
                lines.append(f"  [bold green]{label}[/] detected")
                lines.append(f"  Suggested commands:")
                for cmd in cmds:
                    lines.append(f"    [cyan]{cmd}[/]")
        if not matched_any:
            lines.append("  [dim]No known dev boards detected.[/]")
            lines.append("  [dim]Plug in your ESP32 or Arduino to auto-match a profile.[/]")

        lines.append("\n[bold]── Project Quick-Access ──────────────────────[/]")
        if PROJECTS_DIR.exists():
            subdirs = sorted([d for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")])
            for d in subdirs[:10]:
                git = get_git_status(d)
                tag = f" [dim](git: {git['branch']})[/]" if git else ""
                lines.append(f"  [cyan]{d.name}[/]{tag}  →  {d}")
        else:
            lines.append(f"  [yellow]Projects dir not found: {PROJECTS_DIR}[/]")

        self.query_one("#ws-body", Static).update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-ws":
            self.refresh_ws()


# ─── Main App ─────────────────────────────────────────────────────────────────
class DevPanel(App):
    CSS = """
    Screen {
        background: $background;
    }
    TabbedContent {
        height: 1fr;
    }
    TabPane {
        overflow-y: auto;
        padding: 0;
    }
    Button {
        margin: 0 1 1 2;
    }
    """

    TITLE = "devpanel — Linux Dev Companion"
    BINDINGS = [
        ("q",     "quit",       "Quit"),
        ("1",     "switch_tab('hud')",       "HUD"),
        ("2",     "switch_tab('repos')",     "Repos"),
        ("3",     "switch_tab('thermal')",   "Thermal"),
        ("4",     "switch_tab('memory')",    "Memory"),
        ("5",     "switch_tab('boot')",      "Boot"),
        ("6",     "switch_tab('workspace')", "Workspace"),
        ("r",     "refresh_all",             "Refresh"),
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
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_refresh_all(self) -> None:
        try: self.query_one(HUDTab).refresh_hud()
        except: pass
        try: self.query_one(ReposTab).refresh_repos()
        except: pass
        try: self.query_one(ThermalTab).refresh_thermal()
        except: pass
        try: self.query_one(MemoryTab).refresh_mem()
        except: pass
        try: self.query_one(BootTab).refresh_boot()
        except: pass
        try: self.query_one(WorkspaceTab).refresh_ws()
        except: pass


if __name__ == "__main__":
    DevPanel().run()
