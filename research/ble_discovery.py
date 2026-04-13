import asyncio
from bleak import BleakScanner, BleakClient

async def run():
    print("🔍 Scanning for BLE devices (5s)...")
    devices = await BleakScanner.discover(timeout=5.0)
    
    for d in devices:
        print(f"  [{d.address}] {d.name or 'Unknown'}")
        if d.name and ("OBD" in d.name.upper() or "ELM" in d.name.upper() or "VGATE" in d.name.upper()):
            print(f"  🎯 Found potential OBD candidate: {d.name}")
            
    print("\nScan complete.")

if __name__ == "__main__":
    asyncio.run(run())
