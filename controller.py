#!/usr/bin/env python3
""" Run on the laptop. This receives the singular hip point from the Jetson
through UDP and interprets its movement overtime as jump, duck, move left,
or move right. It then uses Pyautogui to input these commands into the
system. This allows for playing games like Subway Surfers.

Requirements:
# TODO
"""

import json
import os
import socket
import sys
import threading
import time
from collections import deque
from evdev import UInput, ecodes as e

# ---- config -------------------------------------------------------------
PORT           = 9999
STALE_AFTER    = 0.3
JUMP_RISE      = 0.08    # meters
DUCK_DROP      = 0.15    # meters
JUMP_LAND_LOCK = 0.25    # seconds - cooldown to prevent dip after jumping causing a roll
LANE_EDGE      = 0.20    # meters
LANE_SMOOTH    = 5       # frames of x averaged to kill jitter
INVERT_LR      = True    # manually fix lane movement orientation

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

    Jump / roll: fixed calibrated height + threshold + hysteresis.
    Lanes: smoothed X -> absolute target lane (0/1/2)."""

    def __init__(self):
        self._nx = self._ny = None
        self._cx, self._cy = [], []
        self._xbuf = deque(maxlen=LANE_SMOOTH)
        self._jump_on   = False
        self._duck_on   = False
        self._last_jump = -1e9
        self._lane      = 1

    def reset(self):
        self.__init__()

    def update(self, pose):
        if pose is None:
            return []
        x, y = pose["hip"][0], pose["hip"][1]
        now  = pose.get("t", time.monotonic())
        self._xbuf.append(x)

        if self._ny is None:
            self._cx.append(x); self._cy.append(y)
            if len(self._cy) >= 20:
                self._nx = sum(self._cx) / len(self._cx)
                self._ny = sum(self._cy) / len(self._cy)
            return []

        fired = []

        # jumping logic
        if y > self._ny + JUMP_RISE:
            if not self._jump_on:
                self._jump_on = True
                self._last_jump = now
                fired.append(JUMP)
        elif y < self._ny + JUMP_RISE * 0.4:
            self._jump_on = False

        # rolling logic
        if now - self._last_jump > JUMP_LAND_LOCK:
            if y < self._ny - DUCK_DROP:
                if not self._duck_on:
                    self._duck_on = True
                    fired.append(DUCK)
            elif y > self._ny - DUCK_DROP * 0.4:
                self._duck_on = False
        elif y > self._ny - DUCK_DROP * 0.4:
            self._duck_on = False

        # lane logic
        raw = (sum(self._xbuf) / len(self._xbuf)) - self._nx
        if INVERT_LR:
            raw = -raw
        target = 0 if raw < -LANE_EDGE else 2 if raw > LANE_EDGE else 1
        while self._lane < target:
            self._lane += 1; fired.append(RIGHT)
        while self._lane > target:
            self._lane -= 1; fired.append(LEFT)

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
    missing = 0
    was_present = False
    try:
        while True:
            pose    = recv.get_latest()
            actions = interp.update(pose)
            game.apply(actions)

            missing = missing + 1 if pose is None else 0
            if missing > 120:
                interp.reset()

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