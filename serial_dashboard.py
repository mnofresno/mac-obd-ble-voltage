"""OBD-II Dashboard via serial (ESP8266 emulator) — auto-reconnects."""
import sys, re, time, serial, glob
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich import box
from pids import PID_DATABASE, SIMPLE_PIDS

def find_port():
    ports = sorted(glob.glob("/dev/cu.usbserial*"))
    return ports[0] if ports else "/dev/cu.usbserial-110"

def init_port(port):
    s = serial.Serial(port, 115200, timeout=2)
    for c in ["ATZ", "ATE0", "ATL0", "ATS0"]:
        s.write((c + "\r\n").encode())
        time.sleep(0.3)
        s.read(s.in_waiting)
    return s

def query(s, pid, nbytes):
    rp = "41" if pid.startswith("01") else "61"
    pp = pid[2:]
    try: s.write((pid + "\r\n").encode())
    except: return None
    time.sleep(0.3)
    raw = s.read(s.in_waiting).decode(errors="replace")
    m = re.search(f"{rp}{pp}([0-9A-F]{{{nbytes*2}}})", raw)
    return m.group(1) if m else None

stats = {}
cur_port = ""

def make_dashboard():
    layout = Layout()
    layout.split_column(Layout(name="h", size=3), Layout(name="m"), Layout(name="f", size=3))
    layout["m"].split_row(Layout(name="l"), Layout(name="r"))
    def upd():
        t = Table(show_header=False, box=box.SIMPLE, expand=True)
        t.add_row("[cyan]Engine RPM[/]", f"[bold]{stats.get('010C','N/A')}[/] rpm")
        t.add_row("[cyan]Speed[/]", f"[bold]{stats.get('010D','N/A')}[/] km/h")
        t.add_row("[cyan]Load[/]", f"[bold]{stats.get('0104','N/A')}[/] %")
        t.add_row("[cyan]Throttle[/]", f"[bold]{stats.get('0111','N/A')}[/] %")
        t.add_row("[cyan]Coolant[/]", f"[bold]{stats.get('0105','N/A')}[/] C")
        bv = stats.get("2101","N/A"); bc = "red" if bv=="ON" else "green"
        t.add_row("[yellow]Brake[/]", f"[bold {bc}]{bv}[/]")
        layout["l"].update(Panel(t, title="[cyan]Engine[/]", border_style="cyan"))
        v = stats.get("0142","N/A"); vc = "green" if v!="N/A" and float(v)>12.4 else "red"
        bt = Table(show_header=False, box=box.SIMPLE, expand=True)
        bt.add_row("[magenta]Voltage[/]", f"[bold {vc}]{v} V[/]")
        bt.add_row("[grey70]Port[/]", f"[white]{cur_port}[/]")
        bt.add_row("[grey70]Time[/]", stats.get("__time","--:--:--"))
        layout["r"].update(Panel(bt, title="[magenta]Power[/]", border_style="magenta"))
        layout["h"].update(Panel("[white]OBD-II Dashboard (ESP8266 Emulator)[/]", style="on blue", box=box.SQUARE))
        layout["f"].update(Panel(f"[green]{stats.get('__st','Connecting...')}[/]", border_style="dim"))
    return layout, upd

def main():
    global cur_port
    pids = [p for p in PID_DATABASE if p[0] in SIMPLE_PIDS]
    layout, upd = make_dashboard()
    s = None
    with Live(layout, console=Console(), refresh_per_second=2) as live:
        while True:
            if s is None or not s.is_open:
                port = find_port(); cur_port = port
                stats["__st"] = f"Connecting to {port}..."
                try:
                    s = init_port(port)
                    stats["__st"] = "Connected — ESP8266 ELM327 (fake data)"
                except Exception as e:
                    stats["__st"] = f"Retry 2s: {e}"; upd(); time.sleep(2); continue
            ok = True
            for p in pids:
                h = query(s, p[0], p[3])
                if h is None:
                    try: s.close()
                    except: pass
                    s = None; ok = False; break
                if h:
                    try: stats[p[0]] = p[5](h)
                    except: stats[p[0]] = "ERR"
                else: stats[p[0]] = "N/A"
            if ok: stats["__time"] = datetime.now().strftime("%H:%M:%S")
            upd(); time.sleep(0.5)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass
