# cwastro

The software for the computer that runs the EQ6-R imaging rig: a ZWO ASIAIR
Pro (a Raspberry Pi 4 Model B, 4 GB, on ZWO's power board) rebuilt with an
open stack in place of ZWO's closed app, so it can be reached over SSH and
driven from scripts.

Status (2026-11-26): built and bench-tested indoors. Both cameras take
frames, the filter wheel moves, the 12 V outputs switch, the mount connects
and moves, the plate solver solves a 2019 frame from this scope and camera,
and PHD2 loops the guide camera. Nothing has been tested under the sky.

## Hardware

- ZWO ASIAIR Pro: Raspberry Pi 4 Model B Rev 1.4, 12 V input (2 A
  minimum), four switched 12 V outputs (3 A each).
- Boots from a 32 GB microSD. Image ZWO's original card before writing over
  it (the licence file lives on its boot partition); restoring that image
  brings the ASIAIR back.
- Attached gear: ZWO ASI1600MM Pro with the ZWO EFW (8 slots), ZWO
  ASI120MC-S guide camera on a 162 mm guide scope, Sky-Watcher EQ6-R Pro,
  Astro-Tech AT72EDII (430 mm).
- **One of the Pi's two black USB 2.0 ports is dead** (the kernel's
  `1-1.4`). Use the other black port, the blue ports, or the hub on the back
  of the ASI1600.
- The EQ6-R has no USB port. It is reached through the SynScan hand
  controller in PC Direct Mode (its USB socket, a Prolific serial port, 9600
  baud) or with a USB EQDIR cable in the HAND CONTROL socket.

## What is on the box

- Raspberry Pi OS Lite (trixie, 64-bit), hostname `cwastro`, user `cwage`,
  SSH by key only, Ethernet and Wi-Fi by DHCP.
- INDI 2.2.5, built from source: `indi_asi_ccd` (both cameras),
  `indi_asi_wheel`, `indi_eqmod_telescope`, `indi_asi_power` (the 12 V
  outputs, through `pigpiod`). `indiserver` starts at boot on port 7624,
  with no authentication.
- PHD2 2.6.14, built from source, running at boot on a virtual display
  (`:99`) and driven through its server on port 4400. Its window can be seen
  over VNC on localhost:5900, reached through an SSH tunnel.
- astrometry.net with the Tycho-2 index files.

## Layout

- `cloud-init/`: first-boot setup copied to the card's boot partition
  (user, keys, hostname, a network self-report for when the box is not
  reachable). `user-data.example` is the template; the real `user-data`,
  with your SSH keys in it, is not tracked.
- `provision/`: `card.py` writes and verifies a card from the workstation
  without sudo; `write-bootfs.sh` copies the first-boot files;
  `install-indi.sh`, `install-phd2.sh` and `install-tools.sh` run on the Pi,
  in that order.
- `systemd/`: `pigpiod`, `indiserver`, `xvfb`, `phd2`, `x11vnc`.
- `config/`: PHD2's equipment profile.
- `tools/`: scripts that run on the Pi.
  - `indi.py`: read and set INDI properties, take frames to a folder.
  - `flats.py`: flats and dark-flats, with the exposure found per filter.
  - `solve.sh`: plate-solve a main-camera frame.
  - `phd2.py`: PHD2 from the command line (state, connect, loop, guide).

## Rebuilding from scratch

1. On the workstation: copy `cloud-init/user-data.example` to
   `cloud-init/user-data` and add your SSH public keys. Then
   `provision/card.py flash /dev/sdX IMAGE.img.xz` with a Raspberry Pi OS
   Lite arm64 image, and `provision/write-bootfs.sh` on the mounted boot
   partition.
2. Boot the Pi on Ethernet; it sets itself up from `cloud-init/`.
3. Copy this repo to `~/cwastro` on the Pi and run `install-indi.sh` (about
   45 minutes), `install-phd2.sh` (about 20) and `install-tools.sh`.
4. Join Wi-Fi by hand: `sudo nmcli device wifi connect SSID --ask`.

## Things learned the hard way

- The 12 V outputs are off after every boot. `ASI Power` port index 0-3 is
  the output marked 1-4; set its device type before switching it on.
- Always shut down with `sudo systemctl poweroff` before cutting power.
- INDI builds with warnings as errors, and gcc 14 trips one: build with
  `-DFIX_WARNINGS=OFF`.
- The hand controller's USB link needs a good cable; an intermittent one
  looks like a dead port.

## Scope

This is one person's rig, written down so it can be rebuilt. The user name
(`cwage`), the hostname and the device names are hard-coded for it. It is
bench-tested and has not yet been used for a night's imaging.

## Licence

MIT; see `LICENSE`. The scripts here build INDI, PHD2 and astrometry.net,
which carry their own licences, and include none of their code.
