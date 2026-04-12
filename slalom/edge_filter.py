"""
Edge-First Pole Detection
==========================
Uses edge detection as the PRIMARY method to find slalom poles.
Instead of thresholding dark regions and hoping they're poles,
we find all edges → keep only vertical ones → cluster into poles.

Usage:
    python slalom/edge_filter.py                    # defaults to gate_task.png
    python slalom/edge_filter.py image_cross.png
    python slalom/edge_filter.py image_diver.png
"""

import os
import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt


# ── Load image ───────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
image_name = sys.argv[1] if len(sys.argv) > 1 else "gate_task.png"
image_path = os.path.join(script_dir, "media", image_name)
image = cv2.imread(image_path)

if image is None:
    raise FileNotFoundError(f"Image not found: {image_path}")

img_height, img_width = image.shape[:2]
print(f"Image: {image_name} ({img_width}x{img_height})")

# =====================================================
# STEP 1: Grayscale + CLAHE (same preprocessing)
# =====================================================
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)

# =====================================================
# STEP 2: Sobel X — find VERTICAL edges only
# Sobel in X direction detects horizontal intensity changes,
# which means it highlights VERTICAL boundaries (pole edges).
# This is more targeted than Canny which finds ALL edges.
# =====================================================
blurred = cv2.GaussianBlur(enhanced, (5, 5), 1.4)
sobel_x = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
sobel_x_abs = np.uint8(np.abs(sobel_x) * 255 / max(np.abs(sobel_x).max(), 1))

# Threshold to keep only strong vertical edges
_, vertical_edges = cv2.threshold(sobel_x_abs, 40, 255, cv2.THRESH_BINARY)

# =====================================================
# STEP 3: Morphological cleanup on edges
# - Use a vertical kernel to connect broken vertical edges
# - Remove short horizontal noise
# =====================================================
# Connect vertical edge fragments
vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))
vertical_edges = cv2.morphologyEx(vertical_edges, cv2.MORPH_CLOSE, vert_kernel)

# Remove small noise blobs
noise_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
vertical_edges = cv2.morphologyEx(vertical_edges, cv2.MORPH_OPEN, noise_kernel)

# =====================================================
# STEP 4: Hough Line Transform on vertical edges
# Find straight line segments directly from edge map
# =====================================================
lines = cv2.HoughLinesP(
    vertical_edges,
    rho=1,
    theta=np.pi / 180,
    threshold=20,
    minLineLength=int(img_height * 0.05),   # at least 5% of image height
    maxLineGap=int(img_height * 0.03)       # bridge gaps up to 3% of height
)

# Filter: keep only near-vertical lines (75-105 degrees)
all_lines = []
vertical_lines = []
if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        all_lines.append((x1, y1, x2, y2, angle))
        if 75 < angle < 105:
            vertical_lines.append((x1, y1, x2, y2, angle))

print(f"\nHough lines found: {len(all_lines)} total, {len(vertical_lines)} vertical")

# =====================================================
# STEP 5: Cluster vertical lines into poles
# Multiple edge lines belong to the same pole if they
# have similar X coordinates. Group by X position.
# =====================================================
poles = []
if vertical_lines:
    # Sort by average X position
    vertical_lines.sort(key=lambda l: (l[0] + l[2]) / 2)

    # Cluster lines within 30px of each other into one pole
    cluster_gap = max(30, int(img_width * 0.025))
    current_cluster = [vertical_lines[0]]

    for line in vertical_lines[1:]:
        avg_x = (line[0] + line[2]) / 2
        cluster_avg_x = np.mean([(l[0] + l[2]) / 2 for l in current_cluster])

        if abs(avg_x - cluster_avg_x) < cluster_gap:
            current_cluster.append(line)
        else:
            poles.append(current_cluster)
            current_cluster = [line]
    poles.append(current_cluster)

print(f"Poles detected: {len(poles)}")

# =====================================================
# STEP 6: Draw results
# =====================================================
# Create output images
result_lines = image.copy()    # all vertical lines
result_poles = image.copy()    # clustered poles with labels

# Colors for different poles
pole_colors = [
    (0, 255, 0),    # green
    (0, 255, 255),  # yellow
    (255, 0, 255),  # magenta
    (0, 165, 255),  # orange
    (255, 255, 0),  # cyan
    (0, 0, 255),    # red
    (255, 0, 0),    # blue
    (128, 255, 0),  # lime
]

for i, pole_lines in enumerate(poles):
    color = pole_colors[i % len(pole_colors)]

    # Get pole bounding info
    all_x = []
    all_y = []
    for (x1, y1, x2, y2, angle) in pole_lines:
        all_x.extend([x1, x2])
        all_y.extend([y1, y2])
        cv2.line(result_lines, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.line(result_poles, (x1, y1), (x2, y2), color, 2)

    # Draw pole center line and label
    center_x = int(np.mean(all_x))
    top_y = min(all_y)
    bot_y = max(all_y)
    pole_height = bot_y - top_y

    cv2.line(result_poles, (center_x, top_y), (center_x, bot_y), color, 3)
    cv2.putText(result_poles, f"Pole {i+1}", (center_x - 20, top_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    print(f"  Pole {i+1}: center_x={center_x}, y={top_y}-{bot_y}, "
          f"height={pole_height}px ({pole_height/img_height*100:.1f}%), "
          f"{len(pole_lines)} edge lines")

# =====================================================
# DISPLAY
# =====================================================
fig, axes = plt.subplots(2, 3, figsize=(20, 12))
fig.suptitle(f'Edge-First Pole Detection — {image_name}', fontsize=14, fontweight='bold')

def show(img, ax, title):
    if len(img.shape) == 3:
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    else:
        ax.imshow(img, cmap='gray')
    ax.set_title(title)
    ax.axis('off')

show(image, axes[0, 0], '1. Original')
show(enhanced, axes[0, 1], '2. CLAHE Enhanced')
show(sobel_x_abs, axes[0, 2], '3. Sobel X (vertical edges)')
show(vertical_edges, axes[1, 0], '4. Thresholded + Cleaned Edges')
show(result_lines, axes[1, 1], f'5. Vertical Hough Lines ({len(vertical_lines)})')
show(result_poles, axes[1, 2], f'6. Detected Poles ({len(poles)})')

plt.tight_layout()

# Save output
output_name = image_name.replace('.png', '_edge_filter.png')
output_path = os.path.join(script_dir, "media", output_name)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✅ Saved to: {output_path}")

plt.show()
