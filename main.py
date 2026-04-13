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

# --- Configuration ---
SCAN_TIMEOUT = 5.0
DEVICE_NAME_FILTER = ["OBDII", "ELM", "VGATE"]

# Common ELM327 BLE Characteristics (Service FFF0)
UART_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
UART_NOTIFY_UUID  = "0000fff1-0000-1000-8000-00805f9b34fb"
UART_WRITE_UUID   = "0000fff2-0000-1000-8000-00805f9b34fb"

ELM_INIT_COMMANDS = ["ATZ", "ATE0", "ATL0", "ATS0"]

# Global stats storage
stats = {
    "voltage": 0.0,
    "rpm": 0,
    "speed": 0,
    "coolant": 0,
    "load": 0,
    "throttle": 0,
    "status_msg": "Initializing...",
    "device_name": "None",
    "last_update": "--:--:--",
    "health": "Unknown"
}

class OBDBleReader:
    def __init__(self):
        self.client = None
        self.response_buffer = ""
        self.response_event = None

    def notification_handler(self, sender, data):
        decoded = data.decode("ascii", errors="replace")
        self.response_buffer += decoded
        if ">" in decoded or "\r" in decoded:
            if self.response_event:
                self.response_event.set()

    async def send_command(self, cmd, timeout=1.5):
        if not self.client or not self.client.is_connected:
            return ""
        self.response_buffer = ""
        self.response_event.clear()
        try:
            await self.client.write_gatt_char(UART_WRITE_UUID, f"{cmd}\r".encode(), response=False)
            await asyncio.wait_for(self.response_event.wait(), timeout=timeout)
        except:
            pass
        return self.response_buffer.strip()

    def parse_hex(self, resp, pid, expected_bytes):
        # Clean response: remove spaces, echoes, and prompt
        clean = "".join(resp.split()).upper()
        # Look for 41 + PID
        pattern = f"41{pid}([0-9A-F]{{{expected_bytes*2}}})"
        match = re.search(pattern, clean)
        if match:
            return match.group(1)
        return None

    async def update_data(self):
        # 0. Connection check
        if not self.client or not self.client.is_connected:
            return

        # 1. Voltage (PID 42)
        r = await self.send_command("0142")
        h = self.parse_hex(r, "42", 2)
        if h:
            val = int(h, 16)
            stats["voltage"] = val / 1000.0
            stats["health"] = self.get_health_label(stats["voltage"])

        # 2. RPM (PID 0C)
        r = await self.send_command("010C")
        h = self.parse_hex(r, "0C", 2)
        if h:
            stats["rpm"] = int(int(h, 16) / 4)

        # 3. Speed (PID 0D)
        r = await self.send_command("010D")
        h = self.parse_hex(r, "0D", 1)
        if h:
            stats["speed"] = int(h, 16)

        # 4. Coolant (PID 05)
        r = await self.send_command("0105")
        h = self.parse_hex(r, "05", 1)
        if h:
            stats["coolant"] = int(h, 16) - 40

        # 5. Engine Load (PID 04)
        r = await self.send_command("0104")
        h = self.parse_hex(r, "04", 1)
        if h:
            stats["load"] = int(int(h, 16) * 100 / 255)

        # 6. Throttle Position (PID 11)
        r = await self.send_command("0111")
        h = self.parse_hex(r, "11", 1)
        if h:
            stats["throttle"] = int(int(h, 16) * 100 / 255)

        stats["last_update"] = datetime.now().strftime("%H:%M:%S")

    def get_health_label(self, v):
        if v >= 13.2: return "[bold green]Healthy (Charging)[/]"
        if v >= 12.4: return "[green]Healthy (Good)[/]"
        if v >= 12.0: return "[yellow]Warning (Low Load)[/]"
        if v >= 11.6: return "[bold orange]Critical (Might not start)[/]"
        return "[bold red]DANGER (Battery Dead?)[/]"

def make_layout() -> Layout:
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
    return layout

def get_dashboard_content():
    # Left Panel: Vital Gauges
    table = Table(show_header=False, box=box.SIMPLE, expand=True)
    table.add_row("[cyan]Engine RPM[/]", f"[bold]{stats['rpm']}[/] rpm")
    table.add_row("[cyan]Vehicle Speed[/]", f"[bold]{stats['speed']}[/] km/h")
    table.add_row("[cyan]Engine Load[/]", f"[bold]{stats['load']}%[/]")
    table.add_row("[cyan]Throttle Pos[/]", f"[bold]{stats['throttle']}%[/]")
    table.add_row("[cyan]Coolant Temp[/]", f"[bold]{stats['coolant']}[/] °C")
    
    # Right Panel: Battery & Connection
    batt_table = Table(show_header=False, box=box.SIMPLE, expand=True)
    v_color = "red" if stats["voltage"] < 11.8 else "green"
    batt_table.add_row("[magenta]Battery Voltage[/]", f"[bold {v_color}]{stats['voltage']:.2f} V[/]")
    batt_table.add_row("[magenta]Battery Health[/]", stats["health"])
    batt_table.add_row("")
    batt_table.add_row("[grey70]OBD Device[/]", f"[white]{stats['device_name']}[/]")
    batt_table.add_row("[grey70]Last Update[/]", stats["last_update"])

    return Panel(table, title="[bold cyan]Engine Data[/]", border_style="cyan"), \
           Panel(batt_table, title="[bold magenta]Power & Connectivity[/]", border_style="magenta")

def update_layout(layout):
    """Refreshes all components of the layout with current stats."""
    # Update Header
    layout["header"].update(Panel("[bold white]OBD-II Dashboard for macOS (BLE)[/]", style="on blue", box=box.SQUARE))
    
    # Update Footer with dynamic status
    layout["footer"].update(Panel(f"[bold yellow]Status:[/] {stats['status_msg']}", border_style="dim"))
    
    # Update Main Panels
    left, right = get_dashboard_content()
    layout["left"].update(left)
    layout["right"].update(right)

async def main():
    console = Console()
    reader = OBDBleReader()
    layout = make_layout()
    
    with Live(layout, refresh_per_second=4, screen=True) as live:
        while True:
            # 1. Discovery
            stats["status_msg"] = "🔍 Scanning for OBD-II BLE Devices (5s)..."
            update_layout(layout)
            
            try:
                devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)
                target = None
                for d in devices:
                    name = d.name or "Unknown"
                    if any(kw in name.upper() for kw in DEVICE_NAME_FILTER):
                        target = d
                        break
                
                if not target:
                    stats["status_msg"] = "❌ Device not found. Re-scanning in 3s..."
                    update_layout(layout)
                    await asyncio.sleep(3)
                    continue

                # 2. Connection
                stats["status_msg"] = f"🔗 Connecting to [bold cyan]{target.name}[/]..."
                update_layout(layout)
                
                async with BleakClient(target.address) as client:
                    try:
                        reader.client = client
                        reader.response_event = asyncio.Event()
                        stats["device_name"] = target.name
                        stats["status_msg"] = "⚙️ Initializing ELM327 protocol..."
                        update_layout(layout)
                        
                        await client.start_notify(UART_NOTIFY_UUID, reader.notification_handler)
                        
                        # Init ELM with visual feedback
                        for i, cmd in enumerate(ELM_INIT_COMMANDS):
                            stats["status_msg"] = f"⚙️ Sending {cmd} ({i+1}/{len(ELM_INIT_COMMANDS)})..."
                            update_layout(layout)
                            await reader.send_command(cmd)
                            await asyncio.sleep(0.1)
                        
                        stats["status_msg"] = "🚀 Dashboard Live"
                        update_layout(layout)
                        
                        # 3. Reading Loop
                        while client.is_connected:
                            await reader.update_data()
                            update_layout(layout)
                            await asyncio.sleep(0.5)
                    finally:
                        stats["status_msg"] = "🧹 Closing connection gracefully..."
                        update_layout(layout)
                        if client.is_connected:
                            await client.stop_notify(UART_NOTIFY_UUID)
                            await client.disconnect()
                        stats["device_name"] = "None"
                        await asyncio.sleep(0.5)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                stats["status_msg"] = f"⚠️ Error: {str(e)[:50]}"
                stats["device_name"] = "None"
                update_layout(layout)
                await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Final cleanup for terminal
        pass
