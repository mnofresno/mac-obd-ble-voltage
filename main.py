import asyncio
import re
import sys
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient

# --- Configuration ---
SCAN_TIMEOUT = 5.0
DEVICE_NAME_FILTER = ["OBDII", "ELM", "VGATE"]

# Common ELM327 BLE Characteristics (Service FFF0)
UART_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
UART_NOTIFY_UUID  = "0000fff1-0000-1000-8000-00805f9b34fb"
UART_WRITE_UUID   = "0000fff2-0000-1000-8000-00805f9b34fb"

ELM_INIT_COMMANDS = ["ATZ", "ATE0", "ATL0", "ATS0"]
VOLTAGE_PID = "0142"
VOLTAGE_RE = re.compile(r"41\s*42\s*([0-9A-Fa-f]{2})\s*([0-9A-Fa-f]{2})")

class OBDBleReader:
    def __init__(self):
        self.client = None
        self.response_buffer = ""
        self.response_event = None

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)

    def notification_handler(self, sender, data):
        decoded = data.decode("ascii", errors="replace")
        self.response_buffer += decoded
        if ">" in decoded or "\r" in decoded:
            if self.response_event:
                self.response_event.set()

    async def send_command(self, cmd, wait=2.0):
        self.response_buffer = ""
        self.response_event.clear()
        
        full_cmd = f"{cmd}\r".encode()
        await self.client.write_gatt_char(UART_WRITE_UUID, full_cmd, response=False)
        
        try:
            await asyncio.wait_for(self.response_event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            pass
        
        return self.response_buffer.strip()

    async def initialize(self):
        for cmd in ELM_INIT_COMMANDS:
            resp = await self.send_command(cmd)
            self.log(f"  {cmd} -> {resp!r}")
            await asyncio.sleep(0.3)

    async def get_voltage(self):
        resp = await self.send_command(VOLTAGE_PID)
        # Remove spaces and non-hex chars to be safe
        clean_resp = "".join(resp.split())
        match = VOLTAGE_RE.search(clean_resp)
        if not match:
            # Try a more liberal match since spaces are off
            match = re.search(r"4142([0-9A-Fa-f]{4})", clean_resp)
            if match:
                hex_val = match.group(1)
                high = int(hex_val[0:2], 16)
                low = int(hex_val[2:4], 16)
                return ((high * 256) + low) / 1000.0
            return None
            
        high = int(match.group(1), 16)
        low = int(match.group(2), 16)
        return ((high * 256) + low) / 1000.0

    async def run(self):
        self.log("OBD-II BLE Voltage Reader starting...")
        self.response_event = asyncio.Event()
        
        while True:
            try:
                self.log(f"Scanning for OBD-II BLE devices ({SCAN_TIMEOUT}s)...")
                devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT)
                target = None
                for d in devices:
                    name = d.name or "Unknown"
                    if any(kw in name.upper() for kw in DEVICE_NAME_FILTER):
                        target = d
                        break
                
                if not target:
                    self.log("No OBD-II device found. Retrying...")
                    await asyncio.sleep(3)
                    continue

                self.log(f"Connecting to {target.name} ({target.address})...")
                async with BleakClient(target.address) as client:
                    self.client = client
                    self.log("Connected! Initializing ELM327...")
                    
                    await client.start_notify(UART_NOTIFY_UUID, self.notification_handler)
                    await self.initialize()
                    
                    while client.is_connected:
                        voltage = await self.get_voltage()
                        if voltage is not None:
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"[{ts}] {voltage:.2f} V", flush=True)
                        else:
                            # self.log("Check if engine is on/OBD is ready.")
                            pass
                        await asyncio.sleep(1.0)
                        
            except Exception as e:
                self.log(f"Error or Disconnect: {e}")
                await asyncio.sleep(3)
                self.log("Reconnecting...")

if __name__ == "__main__":
    try:
        reader = OBDBleReader()
        asyncio.run(reader.run())
    except KeyboardInterrupt:
        print("\nStopped.")
