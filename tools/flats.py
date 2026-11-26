#!/usr/bin/env python3
"""Shoot flats and their dark-flats.

For each filter it finds the exposure that puts the frame's median at the
target level, then takes COUNT frames. The exposures are written to
flats.json in the output folder. Run it again with --darks, cap on, and it
takes COUNT dark frames at each exposure that was used.

  flats.py --out ~/frames/flats/2026-11-26                    one set, no wheel
  flats.py --out DIR --slots 1,2,3,4,5,6,7                    one set per slot
  flats.py --out DIR --darks                                  dark-flats, cap on

Use the same gain, offset and sensor temperature as the lights, and keep the
panel bright enough to flicker-free but dim enough for exposures of a second
or more (paper over the dew shield).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from astropy.io import fits

import indi

SATURATED = 60000   # 16-bit scale
E_MIN, E_MAX = 0.001, 120.0


def median(path: str) -> float:
    return float(np.median(fits.getdata(path)))


def find_exposure(camera: str, folder: str, target: float, start: float,
                  tolerance: float = 0.07) -> tuple[float, float]:
    """Exposure whose median is within tolerance of target. Returns (seconds, median)."""
    e = start
    last = None  # (exposure, median) of the previous probe
    for _ in range(10):
        path = indi.expose(camera, e, os.path.join(folder, "probe"), "probe", "FRAME_FLAT")
        m = median(path)
        os.remove(path)
        print(f"    probe {e:8.3f} s  median {m:7.0f}", flush=True)
        if abs(m - target) <= tolerance * target:
            return e, m
        # Much more exposure and hardly more signal: nothing is lighting the sensor.
        if last and e >= 4 * last[0] and m < 1.3 * last[1]:
            raise RuntimeError(f"the frame stays dark ({last[1]:.0f} at {last[0]} s, {m:.0f} at {e} s): "
                               "is the cap on, or the panel off?")
        last = (e, m)
        # Step by at most 8x either way, so one bad probe cannot cost minutes.
        scale = 0.125 if m >= SATURATED else min(max(target / max(m, 1.0), 0.125), 8.0)
        e_new = min(max(e * scale, E_MIN), E_MAX)
        if e_new == e:
            break
        e = round(e_new, 4)
    raise RuntimeError(f"could not reach median {target:.0f}: last {e} s gave {m:.0f}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="folder for this flat set")
    p.add_argument("--camera", default="ZWO CCD ASI1600MM Pro")
    p.add_argument("--wheel", default="ZWO EFW")
    p.add_argument("--slots", default="", help="comma-separated filter slots; empty = no wheel")
    p.add_argument("--target", type=float, default=25000, help="median to aim for, 16-bit scale")
    p.add_argument("--count", type=int, default=25, help="frames per filter")
    p.add_argument("--start", type=float, default=1.0, help="first exposure to try, seconds")
    p.add_argument("--darks", action="store_true", help="take dark-flats for an existing set")
    a = p.parse_args()

    out = os.path.expanduser(a.out)
    record = os.path.join(out, "flats.json")
    if not indi.connect(a.camera):
        sys.exit(f"cannot connect to {a.camera}")

    if a.darks:
        sets = json.load(open(record))
        exposures = sorted({s["exposure"] for s in sets.values()})
        print(f"dark-flats, cap on: {len(exposures)} exposure(s), {a.count} frames each")
        for e in exposures:
            for _ in range(a.count):
                indi.expose(a.camera, e, os.path.join(out, "darkflat"), f"darkflat_{e}s", "FRAME_DARK")
            print(f"  {e} s done", flush=True)
        return

    slots = [int(s) for s in a.slots.split(",") if s.strip()]
    if slots and not indi.connect(a.wheel):
        sys.exit(f"cannot connect to {a.wheel}")
    sets = json.load(open(record)) if os.path.exists(record) else {}
    start = a.start
    for slot in slots or [None]:
        if slot is None:
            name = "nofilter"
        else:
            indi.set_filter(a.wheel, slot)
            name = indi.getprop(f"{a.wheel}.FILTER_NAME.FILTER_SLOT_NAME_{slot}") or f"slot{slot}"
            name = f"slot{slot}_{name}".replace(" ", "_")
        print(f"{name}: finding the exposure for median {a.target:.0f}", flush=True)
        e, m = find_exposure(a.camera, out, a.target, start)
        print(f"  using {e} s; taking {a.count} frames", flush=True)
        for _ in range(a.count):
            indi.expose(a.camera, e, os.path.join(out, name), f"flat_{name}_{e}s", "FRAME_FLAT")
        sets[name] = {"slot": slot, "exposure": e, "median": round(m), "count": a.count}
        json.dump(sets, open(record, "w"), indent=2)
        start = e
    print(f"done; exposures recorded in {record}")
    print("next: cap on, then run again with --darks")


if __name__ == "__main__":
    main()
