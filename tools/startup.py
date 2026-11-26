#!/usr/bin/env python3
"""Connect every device after a boot and print what the rig looks like.

INDI starts its drivers at boot but leaves each device disconnected. This
connects the power ports, both cameras, the filter wheel and the mount, and
reports their state. Devices that are not plugged in are reported, not fatal.

  startup.py            connect and report
  startup.py --status   report only
"""
from __future__ import annotations

import sys

import indi

POWER = "ASI Power"
MAIN = "ZWO CCD ASI1600MM Pro"
GUIDE = "ZWO CCD ASI120MC-S"
WHEEL = "ZWO EFW"
MOUNT = "EQMod Mount"


def main() -> None:
    report_only = "--status" in sys.argv[1:]
    rows = []
    for dev in (POWER, MAIN, GUIDE, WHEEL, MOUNT):
        if indi.getprop(f"{dev}.CONNECTION.CONNECT") is None:
            rows.append((dev, "not present"))
            continue
        up = indi.connected(dev) if report_only else indi.connect(dev)
        rows.append((dev, "connected" if up else "NOT connected"))
    for dev, state in rows:
        print(f"{dev:24s} {state}")

    if indi.connected(MAIN):
        t = indi.getprop(f"{MAIN}.CCD_TEMPERATURE.CCD_TEMPERATURE_VALUE")
        c = indi.getprop(f"{MAIN}.CCD_COOLER_POWER.CCD_COOLER_VALUE")
        print(f"  main camera: sensor {float(t):.1f} C, cooler {float(c):.0f}%")
    if indi.connected(WHEEL):
        slot = indi.getprop(f"{WHEEL}.FILTER_SLOT.FILTER_SLOT_VALUE")
        name = indi.getprop(f"{WHEEL}.FILTER_NAME.FILTER_SLOT_NAME_{slot}")
        print(f"  filter wheel: slot {slot} ({name})")
    if indi.connected(POWER):
        on = [str(i + 1) for i in range(4)
              if indi.getprop(f"{POWER}.ONOFF{i}.ONOFF{i}ON") == "On"]
        print(f"  12 V outputs on: {', '.join(on) if on else 'none'}")
    if indi.connected(MOUNT):
        ra = float(indi.getprop(f"{MOUNT}.EQUATORIAL_EOD_COORD.RA"))
        dec = float(indi.getprop(f"{MOUNT}.EQUATORIAL_EOD_COORD.DEC"))
        track = indi.getprop(f"{MOUNT}.TELESCOPE_TRACK_STATE.TRACK_ON")
        park = indi.getprop(f"{MOUNT}.TELESCOPE_PARK.PARK")
        print(f"  mount: RA {ra:.4f} h, Dec {dec:+.3f} deg, tracking {track}, parked {park}")
    if any(state == "NOT connected" for _, state in rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
