import asyncio
from bleak import BleakClient

ADDRESS = "6820D751-BC27-E33F-B577-1A7228E07CC3"

async def run():
    print(f"Connecting to {ADDRESS}...")
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        for service in client.services:
            print(f"Service: {service}")
            for char in service.characteristics:
                print(f"  Characteristic: {char} (Handle: {char.handle}, Properties: {char.properties})")

if __name__ == "__main__":
    asyncio.run(run())
