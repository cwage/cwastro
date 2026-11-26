"""Minimal INDI helpers built on the indi_getprop / indi_setprop commands.

Enough for scripts that run on the box itself: read and set properties and
take frames to a local folder. Not a full INDI client.
"""
from __future__ import annotations

import glob
import os
import subprocess
import time


def getprop(prop: str, timeout: int = 2) -> str | None:
    """Value of one property element, e.g. 'ZWO EFW.FILTER_SLOT.FILTER_SLOT_VALUE'."""
    r = subprocess.run(["indi_getprop", "-t", str(timeout), "-1", prop],
                       capture_output=True, text=True)
    out = r.stdout.strip()
    return out if r.returncode == 0 and out else None


def setprop(assignment: str) -> None:
    """Set a property, e.g. 'ZWO EFW.FILTER_SLOT.FILTER_SLOT_VALUE=2'."""
    subprocess.run(["indi_setprop", assignment], check=True, capture_output=True)


def connected(device: str) -> bool:
    return getprop(f"{device}.CONNECTION.CONNECT") == "On"


def connect(device: str, wait: float = 10) -> bool:
    if connected(device):
        return True
    setprop(f"{device}.CONNECTION.CONNECT=On")
    end = time.time() + wait
    while time.time() < end:
        if connected(device):
            return True
        time.sleep(0.5)
    return False


def wait_state(prop: str, wanted: str = "Ok", timeout: float = 60) -> bool:
    """Wait for a property vector's state, e.g. 'ZWO EFW.FILTER_SLOT'."""
    end = time.time() + timeout
    while time.time() < end:
        if getprop(f"{prop}._STATE") == wanted:
            return True
        time.sleep(0.3)
    return False


def set_filter(wheel: str, slot: int, timeout: float = 60) -> None:
    setprop(f"{wheel}.FILTER_SLOT.FILTER_SLOT_VALUE={slot}")
    end = time.time() + timeout
    while time.time() < end:
        if (getprop(f"{wheel}.FILTER_SLOT.FILTER_SLOT_VALUE") == str(slot)
                and getprop(f"{wheel}.FILTER_SLOT._STATE") == "Ok"):
            time.sleep(0.5)  # let the wheel settle
            return
        time.sleep(0.3)
    raise TimeoutError(f"{wheel} did not reach slot {slot}")


def expose(camera: str, seconds: float, folder: str, prefix: str,
           frame_type: str = "FRAME_LIGHT") -> str:
    """Take one frame, saved on the box. Returns the new file's path."""
    os.makedirs(folder, exist_ok=True)
    before = set(glob.glob(os.path.join(folder, "*.fits")))
    setprop(f"{camera}.UPLOAD_MODE.UPLOAD_LOCAL=On")
    setprop(f"{camera}.UPLOAD_SETTINGS.UPLOAD_DIR={folder};UPLOAD_PREFIX={prefix}_XXX")
    setprop(f"{camera}.CCD_FRAME_TYPE.{frame_type}=On")
    setprop(f"{camera}.CCD_EXPOSURE.CCD_EXPOSURE_VALUE={seconds}")
    end = time.time() + seconds + 60
    while time.time() < end:
        new = set(glob.glob(os.path.join(folder, "*.fits"))) - before
        if new:
            path = new.pop()
            size = -1
            while size != os.path.getsize(path):  # wait until it stops growing
                size = os.path.getsize(path)
                time.sleep(0.2)
            return path
        time.sleep(0.1)
    raise TimeoutError(f"no frame from {camera} after a {seconds} s exposure")
