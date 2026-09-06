#!/usr/bin/env python3
"""Run on the Jetson.

This script tracks the closest person with WAUV's ZED X Mini and the Stereolabs
prebuilt body tracking neural networks (18 keypointss). This script only exports the hip coord
since it is most representative on overall body movement.

Can be ran with --debug to open a camera view with the keypoints overlayed on
the Jetson (over VNC).

Requirements:
numpy 
"""

import json
import os
import socket
import sys
import time
import numpy as np
import pyzed.sl as sl

# ---- config ------------------------------------------------------
DEFAULT_TARGET = "192.168.55.100"
TARGET_IP = os.environ.get("TARGET_IP", DEFAULT_TARGET)
PORT = int(os.environ.get("PORT", "9999"))
DEBUG = ("--debug" in sys.argv[1:])

R_HIP, L_HIP = 8, 11   # BODY_18 (COCO) hip keypoint indices

if DEBUG:
    import cv2
    BONES_18 = [(0, 1), (1, 2), (2, 3), (3, 4), (1, 5), (5, 6), (6, 7),
                (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13),
                (0, 14), (14, 16), (0, 15), (15, 17)]

def hip_center(kp):
    """BODY_18 presents a left hip point and a right hip point. Find the middle point
    for simplicity. None if both are missing."""
    pair = np.array([kp[R_HIP], kp[L_HIP]], dtype=float)
    if np.all(np.isnan(pair)):
        return None
    return np.nanmean(pair, axis=0)

def _ok(pt):
    return pt is not None and np.all(np.isfinite(pt)) and pt[0] > 0 and pt[1] > 0

def _draw_body(frame, kp2d, color, thick):
    for a, b in BONES_18:
        pa, pb = kp2d[a], kp2d[b]
        if _ok(pa) and _ok(pb):
            cv2.line(frame, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])), color, thick)
    for pt in kp2d:
        if _ok(pt):
            cv2.circle(frame, (int(pt[0]), int(pt[1])), 3, color, -1)

def main():
    dest = (socket.gethostbyname(TARGET_IP), PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    zed = sl.Camera()
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.SVGA
    init.depth_mode        = sl.DEPTH_MODE.PERFORMANCE
    init.coordinate_units  = sl.UNIT.METER
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP

    if zed.open(init) != sl.ERROR_CODE.SUCCESS:
        raise SystemExit("Could not open ZED camera")

    zed.enable_positional_tracking(sl.PositionalTrackingParameters())

    bt = sl.BodyTrackingParameters()
    bt.enable_tracking     = True
    bt.enable_body_fitting = False
    bt.detection_model     = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
    bt.body_format         = sl.BODY_FORMAT.BODY_18
    zed.enable_body_tracking(bt)

    runtime = sl.BodyTrackingRuntimeParameters()
    runtime.detection_confidence_threshold = 40

    bodies  = sl.Bodies()
    img_mat = sl.Mat()
    print(f"Streaming hip point to {TARGET_IP}:{PORT} ...{'  [DEBUG VIEW ON]' if DEBUG else ''}")

    while True:
        if zed.grab() != sl.ERROR_CODE.SUCCESS:
            continue
        zed.retrieve_bodies(bodies, runtime)

        # Closest tracked person -> rejects the crowd standing behind.
        nearest, best_d = None, 1e9
        for b in bodies.body_list:
            p = np.array(b.position, dtype=float)
            if not np.all(np.isfinite(p)):
                continue
            d = float(np.linalg.norm(p))
            if d < best_d:
                nearest, best_d = b, d

        hip = hip_center(np.array(nearest.keypoint, dtype=float)) if nearest is not None else None

        if DEBUG:
            zed.retrieve_image(img_mat, sl.VIEW.LEFT)
            frame = cv2.cvtColor(img_mat.get_data(), cv2.COLOR_BGRA2BGR)
            for b in bodies.body_list:
                kp2d = np.array(b.keypoint_2d, dtype=float)
                sel  = (nearest is not None and b.id == nearest.id)
                _draw_body(frame, kp2d, (0, 255, 0) if sel else (120, 120, 120), 2 if sel else 1)
                if sel:
                    rh, lh = kp2d[R_HIP], kp2d[L_HIP]
                    if _ok(rh) and _ok(lh):
                        hx, hy = int((rh[0] + lh[0]) / 2), int((rh[1] + lh[1]) / 2)
                        cv2.circle(frame, (hx, hy), 8, (0, 0, 255), -1)
            label = (f"hip x:{hip[0]:+.2f}  y:{hip[1]:.2f}  dist:{best_d:.2f} m"
                     if hip is not None else "no player")
            cv2.putText(frame, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)
            cv2.imshow("ZED keypoints (q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if nearest is None or hip is None:
            sock.sendto(json.dumps({"player": False}).encode(), dest)
            continue

        packet = {"player": True, "t": time.monotonic(), "hip": [float(x) for x in hip]}
        sock.sendto(json.dumps(packet).encode(), dest)

    if DEBUG:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()