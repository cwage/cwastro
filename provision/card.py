#!/usr/bin/env python3
"""Read, verify and write a removable card through UDisks, without sudo.

UDisks can open a removable drive for backup or restore on the desktop
user's behalf (it is what GNOME Disks uses). The desktop asks for the user's
password in its own dialog; nothing here runs as root. It refuses anything
that is not a removable USB device. `write` opens the card for reading and
for writing before it starts, so the password is asked for once.

  card.py probe  DEVICE
  card.py sha256 DEVICE                      checksum of the whole device
  card.py write  DEVICE IMAGE.xz EXPECT_SHA  write only if the device's
                                             current checksum is EXPECT_SHA
                                             (proof it is the card that was
                                             backed up), then read back and
                                             compare with the image
  card.py flash  DEVICE IMAGE.xz             write and read back, with no
                                             check of what is on the card
"""
from __future__ import annotations

import hashlib
import lzma
import os
import sys
import time

from gi.repository import Gio, GLib

CHUNK = 4 * 1024 * 1024
BUS = Gio.bus_get_sync(Gio.BusType.SYSTEM)


def _prop(path: str, iface: str, name: str):
    res = BUS.call_sync(
        "org.freedesktop.UDisks2", path, "org.freedesktop.DBus.Properties", "Get",
        GLib.Variant("(ss)", (iface, name)), GLib.VariantType("(v)"),
        Gio.DBusCallFlags.NONE, -1, None,
    )
    return res.unpack()[0]


def _path(device: str) -> str:
    return "/org/freedesktop/UDisks2/block_devices/" + os.path.basename(device)


def describe(device: str) -> dict:
    path = _path(device)
    drive = _prop(path, "org.freedesktop.UDisks2.Block", "Drive")
    info = {
        "size": _prop(path, "org.freedesktop.UDisks2.Block", "Size"),
        "removable": _prop(drive, "org.freedesktop.UDisks2.Drive", "MediaRemovable"),
        "bus": _prop(drive, "org.freedesktop.UDisks2.Drive", "ConnectionBus"),
        "model": _prop(drive, "org.freedesktop.UDisks2.Drive", "Model"),
    }
    return info


def check_removable(device: str) -> dict:
    info = describe(device)
    if info["bus"] != "usb" or not info["removable"]:
        sys.exit(f"{device} is not a removable USB device: {info}")
    return info


def open_device(device: str, method: str, ask: bool = True) -> int:
    """method: OpenForBackup (read) or OpenForRestore (write).

    ask: let the desktop show its password dialog if it needs to.
    """
    opts = GLib.Variant("(a{sv})", ({"auth.no_user_interaction": GLib.Variant("b", not ask)},))
    res, fds = BUS.call_with_unix_fd_list_sync(
        "org.freedesktop.UDisks2", _path(device), "org.freedesktop.UDisks2.Block", method,
        opts, GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, -1, None, None,
    )
    return fds.get(res.unpack()[0])


def open_rw(device: str) -> int:
    """One exclusive read-write handle; exclusive keeps the desktop from
    mounting the card's partitions while it is held."""
    opts = GLib.Variant("(sa{sv})", ("rw", {"flags": GLib.Variant("i", os.O_EXCL)}))
    res, fds = BUS.call_with_unix_fd_list_sync(
        "org.freedesktop.UDisks2", _path(device), "org.freedesktop.UDisks2.Block", "OpenDevice",
        opts, GLib.VariantType("(h)"), Gio.DBusCallFlags.NONE, -1, None, None,
    )
    return fds.get(res.unpack()[0])


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def sha256_device(device: str, nbytes: int | None = None, fd: int | None = None) -> str:
    """Checksum the device from its start; a caller's fd is rewound and left open."""
    own = fd is None
    if own:
        fd = open_device(device, "OpenForBackup")
    os.lseek(fd, 0, os.SEEK_SET)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    h = hashlib.sha256()
    done = 0
    last = time.time()
    try:
        while nbytes is None or done < nbytes:
            want = CHUNK if nbytes is None else min(CHUNK, nbytes - done)
            buf = os.read(fd, want)
            if not buf:
                break
            h.update(buf)
            done += len(buf)
            if time.time() - last > 60:
                log(f"  read {done / 1e9:.1f} GB")
                last = time.time()
    finally:
        if own:
            os.close(fd)
    if nbytes is not None and done != nbytes:
        sys.exit(f"short read: {done} of {nbytes} bytes")
    return h.hexdigest()


def write_image(fd: int, image_xz: str) -> tuple[int, str]:
    """Write the decompressed image to fd; return its length and checksum."""
    os.lseek(fd, 0, os.SEEK_SET)  # the handle is shared with the reads
    h = hashlib.sha256()
    done = 0
    last = time.time()
    try:
        with lzma.open(image_xz, "rb") as src:
            while True:
                buf = src.read(CHUNK)
                if not buf:
                    break
                h.update(buf)
                view = memoryview(buf)
                while view:
                    n = os.write(fd, view)
                    view = view[n:]
                done += len(buf)
                if time.time() - last > 30:
                    log(f"  written {done / 1e9:.2f} GB")
                    last = time.time()
        os.fsync(fd)
        # Drop the cached pages so the read-back comes from the card itself.
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    except BaseException:
        os.close(fd)
        raise
    # fd stays open: while the whole card is held for writing the desktop
    # cannot mount its new partitions, which would alter them before the
    # read-back.
    return done, h.hexdigest()


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, device = sys.argv[1], sys.argv[2]
    info = check_removable(device)
    if cmd == "probe":
        fd = open_device(device, "OpenForBackup", ask=False)
        os.close(fd)
        log(f"{device}: {info}; readable through UDisks")
    elif cmd == "sha256":
        log(f"{device}: {info}")
        print(sha256_device(device))
    elif cmd in ("write", "flash"):
        image = sys.argv[3]
        log(f"{device}: {info}")
        log("asking the desktop for access (a password dialog may appear)")
        # One exclusive read-write handle for the whole job. (UDisks opens
        # OpenForBackup and OpenForRestore exclusively too, so two handles
        # at once fail with "Device or resource busy".)
        rfd = wfd = open_rw(device)
        log("access granted")
        if cmd == "write":
            expect = sys.argv[4]
            log("step 1: checksum of the card as it is now")
            got = sha256_device(device, fd=rfd)
            if got != expect:
                sys.exit(f"card checksum {got} is not the backup's {expect}: nothing written")
            log("  MATCH: the card is identical to the backup")
        log(f"step 2: writing {image}")
        nbytes, want = write_image(wfd, image)
        log(f"  wrote {nbytes} bytes")
        log("step 3: reading back")
        back = sha256_device(device, nbytes, fd=rfd)
        os.close(wfd)
        if back != want:
            sys.exit(f"read-back {back} differs from the image {want}")
        log("  VERIFIED: the card matches the image")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
