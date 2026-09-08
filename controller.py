#!/usr/bin/env python3
""" Run on the laptop. This receives the singular hip point from the Jetson
through UDP and interprets its movement overtime as jump, duck, move left,
or move right. It then uses Pyautogui to input these commands into the
system. This allows for playing games like Subway Surfers.

Requirements:
# TODO
"""

import json
import socket
import sys
import threading
import time
from collections import deque
from evdev import UInput, ecodes as e

# ---- config -------------------------------------------------------------
PORT          = 9999
STALE_AFTER   = 0.3
CALIB_FRAMES  = 20      # poses averaged to set a new player's baseline
LOST_AFTER    = 120     # frames absent before the next player recalibrates
SMOOTH        = 5       # frames of hip averaged to kill jitter
JUMP_RISE     = 0.08    # meters
DUCK_DROP     = 0.15    # meters
LANE_SHIFT    = 0.20    # meters
RELEASE_FRAC  = 0.5     # fraction of a threshold needed to re-arm a direction
REFRACTORY    = 0.35    # seconds between repeats of one direction
INVERT_LR     = True    # manually fix lane movement orientation

DEBUG = ("--debug" in sys.argv[1:])

JUMP, DUCK, LEFT, RIGHT = "JUMP", "DUCK", "LEFT", "RIGHT"
KEYMAP = {JUMP: e.KEY_UP, DUCK: e.KEY_DOWN, LEFT: e.KEY_LEFT, RIGHT: e.KEY_RIGHT}

class PoseReceiver:
    """Non-blocking UDP receiver. Exposes only the newest packet, so lag never
    accumulates."""

    def __init__(self, port=PORT):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", port))
        self._sock.setblocking(False)
        self._lock   = threading.Lock()
        self._latest = None
        self._stamp  = 0.0
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            newest = None
            while True:
                try:
                    data, _ = self._sock.recvfrom(4096)
                    newest = data
                except BlockingIOError:
                    break
            if newest is not None:
                try:
                    with self._lock:
                        self._latest = json.loads(newest.decode())
                        self._stamp  = time.monotonic()
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            time.sleep(0.002)

    def get_latest(self):
        with self._lock:
            if self._latest is None:
                return None
            if time.monotonic() - self._stamp > STALE_AFTER:
                return None
            return self._latest if self._latest.get("player") else None

class GestureInterpreter:
    """Hip point -> list of discrete events this frame.

    Baseline recalibrated per player. Each direction fires once when its
    smoothed deviation crosses the threshold, and re-arms only after returning
    within RELEASE_FRAC of it plus a REFRACTORY gap, so held poses never repeat."""

    _RULES = ((JUMP, "y", 1), (DUCK, "y", -1), (LEFT, "x", -1), (RIGHT, "x", 1))

    def __init__(self):
        self._bx = self._by = None
        self._cx, self._cy = [], []
        self._sx = deque(maxlen=SMOOTH)
        self._sy = deque(maxlen=SMOOTH)
        self._engaged   = {k: False for k in KEYMAP}
        self._last_fire = {k: -1e9  for k in KEYMAP}
        self._prev = None
        self.dx = self.dy = 0.0

    def reset(self):
        self.__init__()

    @property
    def calibrated(self):
        return self._by is not None

    def update(self, pose):
        if pose is None or pose is self._prev:
            return []
        self._prev = pose
        x, y = pose["hip"][0], pose["hip"][1]

        if self._by is None:
            self._cx.append(x); self._cy.append(y)
            if len(self._cy) >= CALIB_FRAMES:
                self._bx = sum(self._cx) / len(self._cx)
                self._by = sum(self._cy) / len(self._cy)
            return []

        self._sx.append(x); self._sy.append(y)
        dx = sum(self._sx) / len(self._sx) - self._bx
        dy = sum(self._sy) / len(self._sy) - self._by
        if INVERT_LR:
            dx = -dx
        self.dx, self.dy = dx, dy

        thr = {JUMP: JUMP_RISE, DUCK: DUCK_DROP, LEFT: LANE_SHIFT, RIGHT: LANE_SHIFT}
        now = time.monotonic()
        fired = []
        for name, axis, sign in self._RULES:
            dev = (dy if axis == "y" else dx) * sign
            t = thr[name]
            if dev >= t:
                if not self._engaged[name] and now - self._last_fire[name] >= REFRACTORY:
                    self._engaged[name]   = True
                    self._last_fire[name] = now
                    fired.append(name)
            elif dev <= t * RELEASE_FRAC:
                self._engaged[name] = False
        return fired

class GameInput:
    """Kernel-level virtual keyboard. Every action is a single arrow-key tap."""

    def __init__(self):
        self._ui = UInput({e.EV_KEY: list(KEYMAP.values())}, name="booth-runner-kbd")

    def apply(self, actions):
        for a in actions:
            k = KEYMAP.get(a)
            if k is not None:
                self._ui.write(e.EV_KEY, k, 1)
                self._ui.write(e.EV_KEY, k, 0)
        if actions:
            self._ui.syn()

    def close(self):
        self._ui.close()

def main():
    recv, interp, game = PoseReceiver(), GestureInterpreter(), GameInput()
    active = False
    absent = 0
    was_present = False
    try:
        while True:
            pose = recv.get_latest()

            if pose is not None:
                if not active:
                    interp.reset()
                    active = True
                absent = 0
            elif active:
                absent += 1
                if absent > LOST_AFTER:
                    active = False

            actions = interp.update(pose)
            game.apply(actions)

            if DEBUG:
                if pose is not None and not was_present:
                    print("player detected")
                elif pose is None and was_present:
                    print("player left")
                for a in actions:
                    print(f"move: {a}")
                was_present = pose is not None
            else:
                label = ",".join(actions) if actions else ("no player" if pose is None else "-")
                print(f"\r{label:>18}", end="", flush=True)
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
    finally:
        game.close()
        print("\nstopped")

if __name__ == "__main__":
    main()