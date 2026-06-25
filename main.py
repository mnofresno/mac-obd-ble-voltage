"""OBD-II BLE Dashboard for macOS — simple mode + full PID browser."""
import asyncio
import re
import sys
from datetime import datetime
from bleak import BleakScanner, BleakClient
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich import box

from pids import PID_DATABASE, SIMPLE_PIDS

# --- Config ---
SCAN_TIMEOUT = 5.0
ELM_INIT_COMMANDS = ["ATZ", "ATE0", "ATL0", "ATS0"]
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"  # Nordic UART Service
UART_NOTIFY_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # Nordic UART TX (notify)
UART_WRITE_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"   # Nordic UART RX (write)

# --- Global state ---
stats: dict[str, str] = {}
simple_mode = False
device_name = "None"
status_msg = "Initializing..."
client_ble = None

class OBDBleReader:
    def __init__(self):
        self.client = None
        self.buf = ""
        self.ev = asyncio.Event()
    def notify(self, sender, data):
        self.buf += data.decode("ascii", errors="replace")
        if ">" in self.buf or "\r" in self.buf:
            self.ev.set()
    async def cmd(self, c, timeout=1.5):
        if not self.client or not self.client.is_connected:
            return ""
        self.buf = ""; self.ev.clear()
        try:
            await self.client.write_gatt_char(UART_WRITE_UUID, f"{c}\r".encode(), response=True)
            await asyncio.wait_for(self.ev.wait(), timeout=timeout)
        except:
            pass
        return self.buf.strip()
    def parse(self, resp, pid, nbytes):
        """Parse ELM327 response. Mode 01 -> 41xx, Mode 21 -> 61xx."""
        clean = "".join(resp.split()).upper()
        resp_prefix = "41" if pid.startswith("01") else "61"
        pid_part = pid[2:]  # strip mode prefix
        m = re.search(f"{resp_prefix}{pid_part}([0-9A-F]{{{nbytes*2}}})", clean)
        return m.group(1) if m else None

def get_health(v):
    if v >= 13.2: return "[green]Healthy (Charging)[/]"
    if v >= 12.4: return "[green]Good[/]"
    if v >= 12.0: return "[yellow]Low[/]"
    if v >= 11.6: return "[orange]Critical[/]"
    return "[red]DANGER[/]"

def simple_dashboard():
    """Simple dashboard with only the 7 PIDs. Returns (layout, update_fn)."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )

    def update_layout():
        t = Table(show_header=False, box=box.SIMPLE, expand=True)
        t.add_row("[cyan]Engine RPM[/]", f"[bold]{stats.get('010C','N/A')}[/] rpm")
        t.add_row("[cyan]Vehicle Speed[/]", f"[bold]{stats.get('010D','N/A')}[/] km/h")
        t.add_row("[cyan]Engine Load[/]", f"[bold]{stats.get('0104','N/A')}[/] %")
        t.add_row("[cyan]Throttle Pos[/]", f"[bold]{stats.get('0111','N/A')}[/] %")
        t.add_row("[cyan]Coolant Temp[/]", f"[bold]{stats.get('0105','N/A')}[/] °C")
        bval = stats.get("2101", "N/A")
        b_color = "red" if bval == "ON" else "green"
        t.add_row("[yellow]Brake Pedal[/]", f"[bold {b_color}]{bval}[/]")
        layout["left"].update(Panel(t, title="[bold cyan]Engine Data[/]", border_style="cyan"))

        vval = stats.get("0142", "N/A")
        if vval != "N/A":
            v_color = "red" if float(vval) < 11.8 else "green"
        else:
            v_color = "white"
        bt = Table(show_header=False, box=box.SIMPLE, expand=True)
        bt.add_row("[magenta]Battery Voltage[/]", f"[bold {v_color}]{vval} V[/]")
        bt.add_row("[grey70]OBD Device[/]", f"[white]{device_name}[/]")
        bt.add_row("[grey70]Last Update[/]", stats.get("__time", "--:--:--"))
        layout["right"].update(Panel(bt, title="[bold magenta]Power & Connectivity[/]", border_style="magenta"))

        layout["header"].update(Panel("[bold white]OBD-II Dashboard (Simple)[/]", style="on blue", box=box.SQUARE))
        layout["footer"].update(Panel(f"[bold yellow]Status:[/] {status_msg}", border_style="dim"))

    return layout, update_layout

async def main():
    global simple_mode, device_name, status_msg, client_ble
    simple_mode = "--simple" in sys.argv
    reader = OBDBleReader()

    if not simple_mode:
        console = Console()
        console.print("[bold cyan]OBD-II Full PID Browser[/]")
        console.print("[dim]Type to search PIDs. Press Enter to toggle selection. Ctrl+D to start monitoring.[/]\n")
        table = Table(show_header=True)
        table.add_column("Sel", width=4)
        table.add_column("PID", width=6)
        table.add_column("Name", width=24)
        table.add_column("Description", width=40)
        table.add_column("Unit", width=8)
        table.add_column("Category", width=12)
        selected = set(SIMPLE_PIDS)
        query = ""
        try:
            while True:
                filtered = [p for p in PID_DATABASE if query.lower() in p[1].lower() or query.lower() in p[2].lower() or query.lower() in p[0] or query.lower() in p[7].lower()]
                table = Table(show_header=True)
                table.add_column("Sel", width=4)
                table.add_column("PID", width=6)
                table.add_column("Name", width=24)
                table.add_column("Description", width=40)
                table.add_column("Unit", width=8)
                table.add_column("Category", width=12)
                for p in filtered:
                    mark = "[green]*[/]" if p[0] in selected else "[dim]  [/]"
                    table.add_row(mark, p[0], p[1], p[2], p[4], p[7])
                console.clear()
                console.print(f"[bold cyan]PID Browser[/] (query: {query or '[dim]all[/]'}))\n")
                console.print(table)
                console.print(f"\n[dim]Selected: {len(selected)}. Type to filter. Enter on a row to toggle. Ctrl+D to start.[/]\n")
                try:
                    line = input("[yellow]>[/] ").strip()
                    if line == "":
                        # toggle the first match
                        for p in filtered:
                            if p[0] == query:
                                if p[0] in selected: selected.discard(p[0])
                                else: selected.add(p[0])
                                break
                    else:
                        query = line
                except (EOFError, KeyboardInterrupt):
                    break
        except:
            pass
        simple_mode = len(selected) == 0
        if selected:
            SIMPLE_PIDS.clear()
            SIMPLE_PIDS.update(selected)
        status_msg = f"Monitoring {len(SIMPLE_PIDS)} PIDs"

    # BLE connection loop
    reader.ev = asyncio.Event()
    while True:
        try:
            devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)
            target = None
            for d in devices:
                nm = (d.name or "").lower()
                if any(k in nm for k in ["obd", "elm", "vgate"]):
                    target = d; break
            if not target:
                status_msg = "No ELM327 device found"
                await asyncio.sleep(3); continue
            device_name = target.name or "Unknown"
            status_msg = f"Connecting to {device_name}..."
            try:
                client = await BleakClient.connect(target, timeout=10.0)
                reader.client = client
                client_ble = client
                await client.start_notify(UART_NOTIFY_UUID, reader.notify)
                for ac in ELM_INIT_COMMANDS:
                    await reader.cmd(ac)
                    await asyncio.sleep(0.3)
                # Start monitoring
                layout, update_fn = simple_dashboard()
                async with Live(layout, console=Console(), refresh_per_second=2) as live:
                    while client.is_connected:
                        for pid_entry in [p for p in PID_DATABASE if p[0] in SIMPLE_PIDS]:
                            r = await reader.cmd(pid_entry[0], timeout=1.5)
                            h = reader.parse(r, pid_entry[0], pid_entry[3])
                            if h:
                                try: stats[pid_entry[0]] = pid_entry[5](h)
                                except: stats[pid_entry[0]] = "ERR"
                            else:
                                stats[pid_entry[0]] = "N/A"
                        stats["__time"] = datetime.now().strftime("%H:%M:%S")
                        if "0142" in stats and stats["0142"] != "N/A":
                            stats["__health"] = get_health(float(stats["0142"]))
                        update_fn()
                        await asyncio.sleep(0.5)
            except Exception as e:
                status_msg = f"Connection error: {e}"
        except Exception as e:
            status_msg = f"Scan error: {e}"
        await asyncio.sleep(2)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
