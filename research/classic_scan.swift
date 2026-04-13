#!/usr/bin/env swift
// bt_scan.swift — Scan for nearby Bluetooth Classic devices and list them.
// Usage: swift bt_scan.swift

import Foundation
import IOBluetooth

class BTScanner: NSObject, IOBluetoothDeviceInquiryDelegate {
    let inquiry = IOBluetoothDeviceInquiry(delegate: nil)!
    var found: [IOBluetoothDevice] = []

    func start() {
        inquiry.delegate = self
        inquiry.searchType = kIOBluetoothDeviceSearchClassic.rawValue
        inquiry.updateNewDeviceNames = true
        inquiry.inquiryLength = 8  // seconds

        print("🔍 Scanning for Bluetooth devices (8 seconds)…")
        inquiry.start()
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 12))
    }

    func deviceInquiryDeviceFound(_ sender: IOBluetoothDeviceInquiry!,
                                   device: IOBluetoothDevice!) {
        found.append(device)
        let name = device.name ?? "<unknown>"
        let addr = device.addressString ?? "??"
        print("  Found: \(name)  [\(addr)]")
    }

    func deviceInquiryComplete(_ sender: IOBluetoothDeviceInquiry!,
                                error: IOReturn,
                                aborted: Bool) {
        print("\nScan complete. \(found.count) device(s) found.\n")
        for (i, dev) in found.enumerated() {
            let name = dev.name ?? "<unknown>"
            let addr = dev.addressString ?? "??"
            let paired = dev.isPaired() ? "paired" : "not paired"
            print("  [\(i)] \(name)  \(addr)  (\(paired))")
        }
        if found.isEmpty {
            print("  No devices found. Make sure the ELM327 is powered on.")
        }
        CFRunLoopStop(CFRunLoopGetCurrent())
    }
}

let scanner = BTScanner()
scanner.start()
