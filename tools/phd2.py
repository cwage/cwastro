#!/usr/bin/env python3
"""Talk to PHD2's server (port 4400) from the command line.

  phd2.py state                 application state and what is connected
  phd2.py connect | disconnect  connect PHD2 to the guide camera and mount
  phd2.py loop [MS]             start looping exposures, optionally set MS
  phd2.py stop                  stop looping or guiding
  phd2.py guide                 pick a star, calibrate if needed, and guide
  phd2.py call METHOD [JSON]    any other server method, params as JSON
"""
from __future__ import annotations

import json
import socket
import sys


class Phd2:
    def __init__(self, host: str = "localhost", port: int = 4400) -> None:
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(60)
        self.buf = b""
        self.n = 0

    def call(self, method: str, params=None):
        self.n += 1
        msg = {"method": method, "params": params if params is not None else [], "id": self.n}
        self.sock.sendall((json.dumps(msg) + "\r\n").encode())
        while True:
            while b"\n" not in self.buf:
                self.buf += self.sock.recv(65536)
            line, self.buf = self.buf.split(b"\n", 1)
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("id") == self.n:   # anything else is an event; skip it
                if "error" in d:
                    raise RuntimeError(f"{method}: {d['error']}")
                return d.get("result")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    p = Phd2()
    if cmd == "state":
        print("state:", p.call("get_app_state"))
        print("equipment:", json.dumps(p.call("get_current_equipment")))
        print("pixel scale:", p.call("get_pixel_scale"), "arcsec/px")
    elif cmd == "connect":
        p.call("set_connected", [True]); print("connected:", p.call("get_connected"))
    elif cmd == "disconnect":
        p.call("set_connected", [False]); print("connected:", p.call("get_connected"))
    elif cmd == "loop":
        if args:
            p.call("set_exposure", [int(args[0])])
        p.call("loop"); print("state:", p.call("get_app_state"))
    elif cmd == "stop":
        p.call("stop_capture"); print("state:", p.call("get_app_state"))
    elif cmd == "guide":
        settle = {"pixels": 1.5, "time": 10, "timeout": 120}
        p.call("guide", {"settle": settle, "recalibrate": False}); print("state:", p.call("get_app_state"))
    elif cmd == "call":
        print(json.dumps(p.call(args[0], json.loads(args[1]) if len(args) > 1 else None)))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
