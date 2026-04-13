# macOS OBD-II BLE Voltage Reader

This project provides a simple Python-based solution for reading vehicle battery voltage from an ELM327 OBD-II adapter on macOS using Bluetooth Low Energy (BLE).

## Research Summary

Connecting to ELM327 devices on macOS typically presents two paths:

1.  **Classic Bluetooth (SPP):** Requires the OS to create a serial device node (`/dev/cu.*`). On macOS, this requires manual pairing in System Settings. Many modern ELM327 adapters use Bluetooth 4.0+ (BLE), which does not appear as a classic serial device by default.
2.  **Bluetooth Low Energy (BLE):** This is the path used by modern apps like "Car Scanner". It bypasses the serial port abstraction and communicates directly with the Bluetooth radio using GATT characteristics.

### Findings
- **Discovery:** Classic Bluetooth discovery found the device `OBDII [66:1E:32:9C:14:C2]`, but it wouldn't mount as a serial port without manual user intervention and pairing.
- **BLE Path:** Using `bleak`, we identified the device `OBDII [6820D751-BC27-E33F-B577-1A7228E07CC3]` (macOS-specific UUID). It exposes the `FFF0` service, which is common for serial-over-BLE on ELM327 devices.
- **Communication:** By writing to characteristic `FFF2` and subscribing to notifications on `FFF1`, we can send AT commands and receive OBD-II PID responses.

## Installation

```bash
pip install bleak
```

## Usage

Run the main script to auto-discover and start reading voltage:

```bash
python main.py
```

It will:
1. Scan for devices named "OBDII", "ELM", or "VGATE".
2. Initialize the ELM327 (ATZ, ATE0, etc.).
3. Request PID `0142` (Control Module Voltage) every second.

## Repository Structure

- `main.py`: The primary BLE-based voltage reader.
- `serial_fallback.py`: A `pyserial` based version (requires manual macOS pairing).
- `research/`:
    - `classic_scan.swift`: Swift script to find Bluetooth Classic devices.
    - `ble_discovery.py`: Script to scan for BLE advertisements.
    - `ble_descriptor_dump.py`: Inspects services and characteristics of the device.

## License
MIT
