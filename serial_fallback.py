#!/usr/bin/env python3
"""
OBD-II Battery Voltage Reader via ELM327 Bluetooth Serial.

Connects to an ELM327 adapter exposed as a macOS serial device (/dev/cu.*)
and continuously reads the vehicle's control module voltage (PID 0x42).

Requirements:
    pip install pyserial

Usage:
    python obd_voltage_reader.py
"""

import glob
import re
import sys
import time
from datetime import datetime

import serial


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BAUDRATES = [38400, 9600]
SERIAL_TIMEOUT = 1          # seconds
DISCOVERY_INTERVAL = 3      # seconds between scan retries
READ_INTERVAL = 1           # seconds between voltage reads
MAX_RETRIES = 3             # retries on malformed response
PRIORITY_KEYWORDS = ["OBD", "ELM", "Bluetooth", "Serial"]

ELM_INIT_COMMANDS = [
    "ATZ",    # Reset
    "ATE0",   # Echo off
    "ATL0",   # Linefeeds off
    "ATS0",   # Spaces off (responses without spaces)
]

VOLTAGE_PID = "0142"
VOLTAGE_RE = re.compile(r"41\s*42\s*([0-9A-Fa-f]{2})\s*([0-9A-Fa-f]{2})")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print a timestamped log line."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def find_serial_candidates() -> list[str]:
    """Return a sorted list of candidate serial device paths.

    Devices whose names contain any of the PRIORITY_KEYWORDS are listed first.
    """
    devices = sorted(set(glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")))

    def _priority(path: str) -> int:
        name = path.upper()
        return 0 if any(kw.upper() in name for kw in PRIORITY_KEYWORDS) else 1

    return sorted(devices, key=_priority)


def send_command(port: serial.Serial, cmd: str, wait: float = 0.5) -> str:
    """Send an AT/OBD command and return the response string."""
    port.reset_input_buffer()
    port.write(f"{cmd}\r".encode())
    time.sleep(wait)
    raw = port.read(port.in_waiting or 128)
    return raw.decode("ascii", errors="replace").strip()


def initialize_elm(port: serial.Serial) -> bool:
    """Run the ELM327 initialisation sequence. Return True on success."""
    for cmd in ELM_INIT_COMMANDS:
        resp = send_command(port, cmd, wait=1.0 if cmd == "ATZ" else 0.5)
        log(f"  {cmd} -> {resp!r}")
        if cmd == "ATZ" and "ELM" not in resp.upper():
            log("  ⚠  ELM327 identification not found in ATZ response")
            return False
    return True


def read_voltage(port: serial.Serial):
    """Query PID 42 and return voltage in volts, or None on failure."""
    resp = send_command(port, VOLTAGE_PID, wait=0.8)
    match = VOLTAGE_RE.search(resp)
    if not match:
        return None
    high = int(match.group(1), 16)
    low = int(match.group(2), 16)
    return ((high * 256) + low) / 1000.0


# ---------------------------------------------------------------------------
# Connection loop
# ---------------------------------------------------------------------------

def try_connect():
    """Scan candidates and return an initialised serial connection or None."""
    candidates = find_serial_candidates()
    if not candidates:
        log("No serial devices found under /dev/cu.* or /dev/tty.*")
        return None

    log(f"Found {len(candidates)} candidate(s): {', '.join(candidates)}")

    for dev in candidates:
        for baud in BAUDRATES:
            log(f"Trying {dev} @ {baud} baud …")
            try:
                port = serial.Serial(dev, baudrate=baud, timeout=SERIAL_TIMEOUT)
                time.sleep(0.3)  # let the port settle
                if initialize_elm(port):
                    log(f"✔ Connected: {dev} @ {baud}")
                    return port
                port.close()
            except (serial.SerialException, OSError) as exc:
                log(f"  ✗ {exc}")
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log("OBD-II Battery Voltage Reader starting …")

    while True:
        # --- Discovery phase ---
        port = None
        while port is None:
            port = try_connect()
            if port is None:
                log(f"No ELM327 device found – retrying in {DISCOVERY_INTERVAL}s …")
                time.sleep(DISCOVERY_INTERVAL)

        # --- Reading phase ---
        consecutive_failures = 0
        try:
            while True:
                voltage = None
                for attempt in range(1, MAX_RETRIES + 1):
                    voltage = read_voltage(port)
                    if voltage is not None:
                        break
                    log(f"Malformed response (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(0.3)

                if voltage is not None:
                    consecutive_failures = 0
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] {voltage:.2f} V", flush=True)
                else:
                    consecutive_failures += 1
                    log(f"Failed to read voltage ({consecutive_failures} consecutive)")
                    if consecutive_failures >= 5:
                        log("Too many consecutive failures – reconnecting …")
                        break

                time.sleep(READ_INTERVAL)

        except (serial.SerialException, OSError) as exc:
            log(f"Device disconnected: {exc}")
        finally:
            try:
                port.close()
            except Exception:
                pass
            log("Port closed – restarting discovery …")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
        sys.exit(0)
