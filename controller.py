#!/usr/bin/env python3
"""Run on the laptop. Receives a single hip point from the Jetson over UDP and
turns its movement into jump / duck / left / right key presses so you can play
games like Subway Surfers.

A baseline (resting hip position) is calibrated fresh every time a new player
is detected, and every direction is measured as a deviation from that baseline.
Crossing a direction's trigger distance fires its key once. It will not fire
again until the hip returns toward the baseline (hysteresis) AND a short
refractory time has passed, so holding a pose or jittering on the threshold
cannot spam. All knobs are in the tunable-parameters block below.
"""

import json
import socket
import threading
import time
from collections import deque
from datetime import datetime
from evdev import UInput, ecodes as e

# ============ tunable parameters =========================================
# --- network ---
PORT           = 9999    # UDP port the Jetson streams hip points to
STALE_AFTER    = 0.30    # s: forget the player if no packet arrives for this long

# --- baseline: recalibrated fresh for each newly detected player ---
CALIB_FRAMES   = 30      # poses averaged to fix a new player's baseline
LOST_AFTER     = 120     # missing loop frames before the player counts as gone;
                         # the next arrival then recalibrates. Higher = brief
                         # dropouts won't trigger a recalibration mid-play.

# --- signal conditioning ---
SMOOTH_FRAMES  = 3       # distinct poses averaged to kill jitter (1 = no smoothing)

# --- trigger distance: how far the hip must move FROM BASELINE to fire (meters) ---
JUMP_RISE      = 0.10    # move up       -> JUMP
DUCK_DROP      = 0.12    # move down     -> DUCK
LANE_SHIFT     = 0.08    # move sideways -> LEFT / RIGHT

# --- re-arm (hysteresis): after firing, the hip must come back to within this
#     fraction of the trigger distance before that direction can fire again ---
RELEASE_FRAC   = 0.5     # 0.5 = halfway back to baseline; lower = stricter

# --- refractory: minimum seconds between two fires of the SAME direction ---
REFRACTORY     = 0.35    # hard cap on how fast one direction can repeat

# --- orientation / debug ---
INVERT_LR      = True    # flip if leaning left moves you right
PRINT_LEVELS   = False   # True: print live dy/dx a few times a second (for tuning)
# =========================================================================

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
                    parsed = json.loads(newest.decode())
                    with self._lock:
                        self._latest = parsed
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
    """Hip point -> discrete key events.

    Calibrates a baseline, smooths the signal, then for each direction fires
    once when the deviation from baseline crosses that direction's trigger
    distance. It stays latched until the hip returns toward baseline
    (RELEASE_FRAC) and REFRACTORY seconds have elapsed."""

    # (direction, axis, sign): which axis and which way counts as "toward" it.
    _RULES = (
        (JUMP,  "y",  1),
        (DUCK,  "y", -1),
        (LEFT,  "x", -1),
        (RIGHT, "x",  1),
    )
    _DIST = {JUMP: "JUMP_RISE", DUCK: "DUCK_DROP", LEFT: "LANE_SHIFT", RIGHT: "LANE_SHIFT"}

    def __init__(self):
        self._bx = self._by = None          # baseline
        self._cx, self._cy = [], []          # calibration accumulators
        self._sx = deque(maxlen=SMOOTH_FRAMES)
        self._sy = deque(maxlen=SMOOTH_FRAMES)
        self._engaged   = {k: False for k in KEYMAP}
        self._last_fire = {k: -1e9  for k in KEYMAP}
        self._prev = None
        self.dx = self.dy = 0.0              # last deviations (for the tuning readout)

    def reset(self):
        self.__init__()

    @property
    def calibrated(self):
        return self._by is not None

    def update(self, pose):
        # only act on genuinely new packets; duplicates carry no new information
        # and would corrupt the smoothing window and refractory timing
        if pose is None or pose is self._prev:
            return []
        self._prev = pose

        x, y = pose["hip"][0], pose["hip"][1]

        # calibrate the baseline from the first CALIB_FRAMES distinct poses
        if self._by is None:
            self._cx.append(x); self._cy.append(y)
            if len(self._cy) >= CALIB_FRAMES:
                self._bx = sum(self._cx) / len(self._cx)
                self._by = sum(self._cy) / len(self._cy)
            return []

        # smooth, then measure deviation from the baseline
        self._sx.append(x); self._sy.append(y)
        dx = sum(self._sx) / len(self._sx) - self._bx
        dy = sum(self._sy) / len(self._sy) - self._by
        if INVERT_LR:
            dx = -dx
        self.dx, self.dy = dx, dy

        thresholds = {JUMP: JUMP_RISE, DUCK: DUCK_DROP, LEFT: LANE_SHIFT, RIGHT: LANE_SHIFT}
        now = time.monotonic()
        fired = []
        for name, axis, sign in self._RULES:
            dev = (dy if axis == "y" else dx) * sign     # deviation toward this direction
            thr = thresholds[name]
            if dev >= thr:
                armed = not self._engaged[name] and now - self._last_fire[name] >= REFRACTORY
                if armed:
                    self._engaged[name]   = True
                    self._last_fire[name] = now
                    fired.append(name)
            elif dev <= thr * RELEASE_FRAC:
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


def log(msg):
    print(datetime.now().strftime("%H:%M:%S.%f")[:-3], msg, flush=True)


def main():
    recv, interp, game = PoseReceiver(), GestureInterpreter(), GameInput()
    active   = False     # is a player currently engaged with the booth
    ready    = False     # have we announced "ready" for this player yet
    absent   = 0         # consecutive missing frames while a player was active
    tele     = 0.0

    log("waiting for player...")
    try:
        while True:
            pose = recv.get_latest()

            if pose is not None:
                if not active:               # fresh arrival -> recalibrate for THIS person
                    interp.reset()
                    active, ready = True, False
                    log("player detected, calibrating...")
                absent = 0
            elif active:
                absent += 1
                if absent > LOST_AFTER:      # gone long enough -> they've left
                    active, ready = False, False
                    log("player left")

            actions = interp.update(pose)
            game.apply(actions)

            if active and interp.calibrated and not ready:
                log("calibrated, ready")
                ready = True

            for a in actions:                # one line per registered move
                log(f"-> {a}")

            if PRINT_LEVELS and interp.calibrated:
                t = time.monotonic()
                if t - tele >= 0.25:
                    log(f"   dy={interp.dy:+.3f}  dx={interp.dx:+.3f}")
                    tele = t

            time.sleep(1 / 100)
    except KeyboardInterrupt:
        pass
    finally:
        game.close()
        log("stopped")


if __name__ == "__main__":
    main()