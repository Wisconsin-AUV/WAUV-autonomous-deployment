"""
edge_detect.py — vertical edge-pair pole detector
--------------------------------------------------
Detects slalom poles and gate posts in underwater AUV imagery.

Usage:
    python edge_detect.py image_cross.png
    python edge_detect.py "image (2).png"
    python edge_detect.py gate_task.png

How it works:
  Each thin PVC pole creates TWO parallel vertical edges — a brightening
  boundary on its left side and a darkening boundary on its right side,
  roughly 3-10 pixels apart. This detector:

    1. Extracts positive and negative Sobel-X edges separately
    2. Enforces tall vertical continuity (80-px morphological open) so
       scattered noise is eliminated while real pole edges survive
    3. Looks for matching left+right edge columns within the expected
       pole-width range (3-10 px apart) that both persist strongly
       in the LOWER portion of the frame (where the poles are anchored)
    4. Merges overlapping column-pairs, filters by position and size,
       and draws the final pole mask

Gate mode uses the same core but keeps only the leftmost and rightmost
detected poles (= the two outer gate frame posts).
"""

import os
import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Core detector
# ---------------------------------------------------------------------------

def find_poles(image,
               sobel_thresh=20,
               continuity_px=80,
               min_lower_rows=80,
               min_pole_width=3,
               max_pole_width=11,
               lower_frac=0.30,
               border_frac=0.03):
    """
    Detect poles via vertical edge pairing.

    Parameters
    ----------
    sobel_thresh      : Sobel-X magnitude threshold (0-255 after normalise)
    continuity_px     : morphological-open height — edge must span this many
                        rows without a gap to survive
    min_lower_rows    : minimum number of rows (in the lower `1-lower_frac`
                        portion of the image) where the edge must be active
    min/max_pole_width: expected pole width in pixels
    lower_frac        : ignore the top `lower_frac` fraction for row-counting
    border_frac       : ignore detected poles whose x-centre is within this
                        fraction of the image edge (lens border / frame)

    Returns
    -------
    intermediates : dict of labelled diagnostic images
    pole_spans    : list of (xl, xr, y_top, y_bot) for each detected pole
    pole_mask     : uint8 binary mask, 255 on detected poles
    """
    h, w = image.shape[:2]
    lower_start = int(h * lower_frac)
    border_px   = int(w * border_frac)

    # ------------------------------------------------------------------
    # 1. CLAHE on grayscale → slight blur to reduce 1-pixel noise
    # ------------------------------------------------------------------
    gray     = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred  = cv2.GaussianBlur(enhanced, (3, 3), 0.8)

    # ------------------------------------------------------------------
    # 2. Sobel-X: detect horizontal brightness transitions
    #    Positive = left edge of pole (dark-to-bright going right)
    #    Negative = right edge of pole (bright-to-dark going right)
    # ------------------------------------------------------------------
    sobelx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)

    def to_binary(arr, t):
        mx = arr.max()
        if mx < 1e-6:
            return np.zeros(arr.shape, dtype=np.uint8)
        normed = (arr / mx * 255).astype(np.uint8)
        _, binary = cv2.threshold(normed, t, 255, cv2.THRESH_BINARY)
        return binary

    left_bin  = to_binary(np.clip( sobelx, 0, None), sobel_thresh)
    right_bin = to_binary(np.clip(-sobelx, 0, None), sobel_thresh)

    # ------------------------------------------------------------------
    # 3. Enforce vertical continuity
    #    Close small gaps first (small kernel), then open with a tall
    #    narrow kernel to require a minimum unbroken vertical run.
    # ------------------------------------------------------------------
    close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 10))
    open_k  = cv2.getStructuringElement(cv2.MORPH_RECT, (1, continuity_px))

    def enforce(b):
        closed = cv2.morphologyEx(b, cv2.MORPH_CLOSE, close_k, iterations=2)
        return  cv2.morphologyEx(closed, cv2.MORPH_OPEN,  open_k,  iterations=1)

    left_cont  = enforce(left_bin)
    right_cont = enforce(right_bin)

    # ------------------------------------------------------------------
    # 4. Column-wise row counts in the LOWER portion of the frame
    #    (where poles are anchored — ignores water-surface ripple noise)
    # ------------------------------------------------------------------
    left_lower  = (left_cont [lower_start:, :] > 0).sum(axis=0)
    right_lower = (right_cont[lower_start:, :] > 0).sum(axis=0)

    # ------------------------------------------------------------------
    # 5. Pair left-edge columns with right-edge columns
    #    Both sides must meet the min_lower_rows threshold.
    #    Take the closest right-edge match within the width range.
    # ------------------------------------------------------------------
    active_left = np.where(left_lower >= min_lower_rows)[0]
    right_set   = set(np.where(right_lower >= min_lower_rows)[0].tolist())

    raw_pairs = []   # (xl, xr, left_count, right_count)
    for xl in active_left:
        if xl < border_px or xl > w - border_px:
            continue
        for d in range(min_pole_width, max_pole_width + 1):
            xr = xl + d
            if xr in right_set and right_lower[xr] >= min_lower_rows:
                raw_pairs.append((xl, xr,
                                  int(left_lower[xl]),
                                  int(right_lower[xr])))
                break

    # ------------------------------------------------------------------
    # 6. Merge overlapping / adjacent column pairs into single pole spans
    # ------------------------------------------------------------------
    raw_pairs.sort()
    merged = []
    if raw_pairs:
        xl0, xr0, ll0, rl0 = raw_pairs[0]
        for xl, xr, ll, rl in raw_pairs[1:]:
            if xl <= xr0 + 5:               # overlap / adjacent — expand
                xr0 = max(xr0, xr)
                ll0 = max(ll0, ll)
                rl0 = max(rl0, rl)
            else:
                merged.append((xl0, xr0, ll0, rl0))
                xl0, xr0, ll0, rl0 = xl, xr, ll, rl
        merged.append((xl0, xr0, ll0, rl0))

    # ------------------------------------------------------------------
    # 7. Find vertical extent for each merged span and build the mask
    # ------------------------------------------------------------------
    pole_spans = []
    pole_mask  = np.zeros((h, w), dtype=np.uint8)

    for xl, xr, ll, rl in merged:
        cx = (xl + xr) // 2

        # Skip anything too close to the image border
        if cx < border_px or cx > w - border_px:
            continue

        # Get rows where either edge is active (whole-image, not just lower)
        rows_l = np.where(left_cont [:, xl] > 0)[0]
        rows_r = np.where(right_cont[:, xr] > 0)[0]
        all_rows = np.concatenate([rows_l, rows_r])
        if len(all_rows) == 0:
            continue

        y_top = int(all_rows.min())
        y_bot = int(all_rows.max())
        span  = y_bot - y_top

        # Must span at least 20 % of image height
        if span < h * 0.20:
            continue

        # Must NOT start at the very top of the frame
        # (frame edges / water-surface artifacts always originate at y≈0)
        if y_top < h * 0.05:
            continue

        pole_spans.append((xl, xr, y_top, y_bot))
        cv2.rectangle(pole_mask,
                      (xl, y_top),
                      (xr, y_bot),
                      255, -1)

    intermediates = {
        "enhanced":      enhanced,
        "left_cont":     left_cont,
        "right_cont":    right_cont,
        "edge_combined": cv2.add(left_cont, right_cont),
    }
    return intermediates, pole_spans, pole_mask


# ---------------------------------------------------------------------------
# Gate mode: run detector then keep only leftmost + rightmost poles
# ---------------------------------------------------------------------------

def detect_gate_poles(image):
    """
    Gate-specific detector using column brightness dips.

    The inner gate posts appear DARK against the bright pool floor.
    Averaging brightness over the lower half of the frame and finding
    local minima in the column profile reliably locates both posts.
    The Sobel edge approach fails here because the post edges are too
    similar in strength to the surrounding lane-line noise.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Build intermediates for the display panel
    clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred  = cv2.GaussianBlur(enhanced, (3, 3), 0.8)
    sobelx   = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)

    def to_binary(arr, t):
        mx = arr.max()
        if mx < 1e-6:
            return np.zeros(arr.shape, dtype=np.uint8)
        normed = (arr / mx * 255).astype(np.uint8)
        _, binary = cv2.threshold(normed, t, 255, cv2.THRESH_BINARY)
        return binary

    inter = {
        "enhanced":      enhanced,
        "left_cont":     to_binary(np.clip( sobelx, 0, None), 12),
        "right_cont":    to_binary(np.clip(-sobelx, 0, None), 12),
        "edge_combined": to_binary(np.abs(sobelx), 12),
    }

    # ------------------------------------------------------------------
    # Column brightness-dip approach
    # Average grayscale over y=50-90% of frame (below crossbar, above floor).
    # Inner posts are darker than the bright pool floor → local minima.
    # ------------------------------------------------------------------
    y1, y2     = int(h * 0.50), int(h * 0.90)
    col_mean   = gray[y1:y2, :].astype(float).mean(axis=0)
    col_smooth = np.convolve(col_mean, np.ones(7) / 7, mode='same')

    # Search only in the inner gate region (x: 40-68% of frame width)
    x_lo, x_hi = int(w * 0.40), int(w * 0.68)

    dips = []
    for x in range(x_lo + 20, x_hi - 20):
        if col_smooth[x] == col_smooth[x - 20: x + 20].min():
            dips.append((float(col_smooth[x]), x))

    dips.sort()   # darkest first
    print(f"  [gate] Brightness dips in x={x_lo}→{x_hi}:")
    for bri, x in dips[:6]:
        print(f"         x={x}  brightness={bri:.1f}")

    if len(dips) < 2:
        print("  [gate] Not enough dips — falling back to edge method")
        _, spans, mask = find_poles(image, sobel_thresh=12, continuity_px=50,
                                    min_lower_rows=40, border_frac=0.30)
        return inter, spans, mask

    # Two darkest dips = left and right inner posts
    selected_x = sorted([dips[0][1], dips[1][1]])
    print(f"  [gate] Inner posts at x={selected_x[0]} (LEFT) and x={selected_x[1]} (RIGHT)")

    # Draw boxes from crossbar level down to pool floor
    crossbar_y = int(h * 0.50)
    pole_bot   = int(h * 0.96)
    half_w     = 12

    spans     = []
    gate_mask = np.zeros((h, w), dtype=np.uint8)
    for cx in selected_x:
        xl   = max(0, cx - half_w)
        xr   = min(w - 1, cx + half_w)
        side = "LEFT" if cx < w // 2 else "RIGHT"
        print(f"  [gate] {side} pole: cx={cx}, y={crossbar_y}→{pole_bot}")
        spans.append((xl, xr, crossbar_y, pole_bot))
        cv2.rectangle(gate_mask, (xl, crossbar_y), (xr, pole_bot), 255, -1)

    return inter, spans, gate_mask


# ---------------------------------------------------------------------------
# Overlay builder
# ---------------------------------------------------------------------------

def build_overlay(image, pole_spans):
    """Green tint on pole regions + red bounding box around each pole."""
    overlay = image.copy()

    for xl, xr, yt, yb in pole_spans:
        overlay[yt:yb+1, xl:xr+1] = [0, 255, 0]

    blended = cv2.addWeighted(image, 0.5, overlay, 0.5, 0)

    for xl, xr, yt, yb in pole_spans:
        cv2.rectangle(blended, (xl, yt), (xr, yb), (0, 0, 255), 2)

    return blended


# ---------------------------------------------------------------------------
# Display helper
# ---------------------------------------------------------------------------

def show_image(img, title, ax):
    if len(img.shape) == 3:
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    else:
        ax.imshow(img, cmap="gray")
    ax.set_title(title, fontsize=9)
    ax.axis("off")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(image_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "media", image_name)
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Not found: '{image_path}'")

    h, w = image.shape[:2]
    mode = "gate" if "gate" in image_name.lower() else "slalom"
    print(f"=== {mode.upper()} | {image_name} ({w}×{h}) ===")

    if mode == "gate":
        inter, spans, _ = detect_gate_poles(image)
    else:
        inter, spans, _ = find_poles(image)

    print(f"  Poles found: {len(spans)}")
    for i, (xl, xr, yt, yb) in enumerate(spans):
        print(f"    pole {i+1}: cx={(xl+xr)//2}  x={xl}→{xr}  y={yt}→{yb}  h={yb-yt}px")

    result = build_overlay(image, spans)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f"{image_name}  [{mode}]  — {len(spans)} poles detected",
                 fontsize=13, fontweight="bold")

    show_image(image,                   "1. Original",                 axes[0, 0])
    show_image(inter["enhanced"],       "2. CLAHE Grayscale",          axes[0, 1])
    show_image(inter["left_cont"],      "3. Left edges (sustained)",   axes[0, 2])
    show_image(inter["right_cont"],     "4. Right edges (sustained)",  axes[1, 0])
    show_image(inter["edge_combined"],  "5. Both edges combined",      axes[1, 1])
    show_image(result,                  f"6. Result — {len(spans)} poles", axes[1, 2])

    plt.tight_layout()

    base     = os.path.splitext(image_name)[0].replace(" ", "_")
    out_path = os.path.join(script_dir, "media", f"{base}_poles.png")
    cv2.imwrite(out_path, result)
    print(f"  Saved → {out_path}")
    plt.show()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "image (2).png"
    run(target)
