"""OBD-II PID database: formulas, units, display names."""

SIMPLE_PIDS = {"010C", "010D", "0105", "0104", "0111", "0142", "2101"}

def _ab(h):
    return 256 * int(h[0:2], 16) + int(h[2:4], 16)

def _fmt(val, fmt):
    return fmt.format(val)

PID_DATABASE = [
    # (cmd, name, description, nbytes, unit, formula_fn, mode, category)
    ("0100", "PIDs supported 01-20", "Supported PID bitmask range 01-20", 6, "", lambda h: f"0x{h[:12]}", "01", "Diagnostics"),
    ("0101", "DTC count", "Number of stored trouble codes", 1, "codes", lambda h: str(int(h,16)), "01", "Diagnostics"),
    ("0104", "Engine load", "Calculated engine load", 1, "%", lambda h: f"{int(h,16)*100/255:.1f}", "01", "Engine"),
    ("0105", "Coolant temp", "Engine coolant temperature", 1, "°C", lambda h: str(int(h,16)-40), "01", "Engine"),
    ("0106", "ST fuel trim B1", "Short term O2 trim Bank 1", 1, "%", lambda h: f"{(int(h,16)-128)*100/128:+.1f}", "01", "Fuel"),
    ("0107", "LT fuel trim B1", "Long term O2 trim Bank 1", 1, "%", lambda h: f"{(int(h,16)-128)*100/128:+.1f}", "01", "Fuel"),
    ("0108", "ST fuel trim B2", "Short term O2 trim Bank 2", 1, "%", lambda h: f"{(int(h,16)-128)*100/128:+.1f}", "01", "Fuel"),
    ("0109", "LT fuel trim B2", "Long term O2 trim Bank 2", 1, "%", lambda h: f"{(int(h,16)-128)*100/128:+.1f}", "01", "Fuel"),
    ("010C", "Engine RPM", "Engine revolutions per minute", 2, "rpm", lambda h: f"{_ab(h)//4}", "01", "Engine"),
    ("010D", "Vehicle speed", "Vehicle speed", 1, "km/h", lambda h: str(int(h,16)), "01", "Vehicle"),
    ("010E", "Timing advance", "Ignition timing advance from TDC", 1, "°", lambda h: f"{(int(h,16)-128)/2:.1f}", "01", "Engine"),
    ("010F", "Intake air temp", "Intake air temperature", 1, "°C", lambda h: str(int(h,16)-40), "01", "Engine"),
    ("0110", "MAF air flow", "Mass air flow rate", 2, "g/s", lambda h: f"{_ab(h)/100:.1f}", "01", "Engine"),
    ("0111", "Throttle position", "Throttle position sensor", 1, "%", lambda h: f"{int(h,16)*100/255:.1f}", "01", "Engine"),
    ("0112", "A/C request", "Air conditioning request switch", 1, "", lambda h: "ON" if int(h,16)&0x80 else "OFF", "01", "Climate"),
    ("0114", "Engine run time", "Engine run time since DTC clear", 2, "min", lambda h: f"{_ab(h)}", "01", "Engine"),
    ("0115", "Distance with MIL", "Distance traveled since DTC clear", 2, "km", lambda h: f"{_ab(h)}", "01", "Diagnostics"),
    ("0119", "Absolute load", "Absolute load value (no load signal)", 2, "%", lambda h: f"{_ab(h)/255*100:.1f}", "01", "Engine"),
    ("011B", "Fuel pressure", "Fuel system pressure", 2, "kPa", lambda h: f"{_ab(h)*0.079:.1f}", "01", "Fuel"),
    ("011C", "O2 Sensor 1", "O2 sensor bank 1 sensor 1 voltage/load", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("011D", "O2 Sensor 2", "O2 sensor bank 1 sensor 2", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("011E", "O2 Sensor 3", "O2 sensor bank 1 sensor 3", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("011F", "O2 Sensor 4", "O2 sensor bank 1 sensor 4", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("0120", "O2 Sensor 5", "O2 sensor bank 2 sensor 1", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("0121", "O2 Sensor 6", "O2 sensor bank 2 sensor 2", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("0122", "O2 Sensor 7", "O2 sensor bank 2 sensor 3", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("0123", "O2 Sensor 8", "O2 sensor bank 2 sensor 4", 2, "mV", lambda h: f"{_ab(h)/325.5*1000:.1f}", "01", "Engine"),
    ("012D", "Compliance", "Emissions standard (1=OBDII 2=OBDIII EUROII)", 1, "", lambda h: str(int(h,16)), "01", "Diagnostics"),
    ("012E", "O2 Sensors alt", "O2 sensor configuration mask", 1, "", lambda h: str(int(h,16)), "01", "Diagnostics"),
    # Custom voltage (not standard OBD, ELM327 sends 0142 -> 4142)
    ("0142", "Battery voltage", "Battery voltage from ELM327 analog", 2, "V", lambda h: f"{_ab(h)/1000:.2f}", "01", "Power"),
    # Toyota enhanced
    ("2101", "Toyota: Brake + flags", "Toyota diagnostic flags (brake pedal etc.)", 13, "", lambda h: "ON" if int(h[24:26],16)&0x20 else "OFF", "21", "Toyota"),
]
