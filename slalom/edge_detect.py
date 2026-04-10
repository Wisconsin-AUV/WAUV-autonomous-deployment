import os
import sys
import cv2
import matplotlib.pyplot as plt
# from google.colab import files
import numpy as np

def show_image(img, **kwargs):
    """
    Display an image with Matplotlib, converting BGR to RGB if needed.
    If the image has 3 channels, assume BGR and convert to RGB.
    If the image has 1 channel, display as grayscale.
    """
    if len(img.shape) == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        plt.imshow(img, **kwargs)
    else:
        plt.imshow(img, cmap='gray', **kwargs)

# Read the uploaded image
# image_path = next(iter(uploaded))
# image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# image = cv2.imread("./media/gate_task.png", cv2.IMREAD_GRAYSCALE)
script_dir = os.path.dirname(os.path.abspath(__file__))
image_name = sys.argv[1] if len(sys.argv) > 1 else "gate_task.png"
image_path = os.path.join(script_dir, "media", image_name)
image = cv2.imread(image_path)

if image is None:
    raise FileNotFoundError(f"Image not found at '{image_path}'. Check the file path and try again.")

# simple white balance
def correct_underwater(image):
    b, g, r = cv2.split(image)
    r = cv2.equalizeHist(r)
    b = cv2.equalizeHist(b) # reduce the blue dominance
    return cv2.merge([b, g, r])

correct = correct_underwater(image)

# =====================================================
# STEP 1: Convert to grayscale
# =====================================================
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# =====================================================
# STEP 2: Apply CLAHE for local contrast enhancement
# This makes the dark columns stand out more against
# the blue water, even with uneven lighting.
# =====================================================
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)

# =====================================================
# STEP 3: Threshold to get black/white mask of dark regions
# Low pixel values = dark columns
# =====================================================
_, dark_thresh = cv2.threshold(enhanced, 60, 255, cv2.THRESH_BINARY_INV)

# =====================================================
# STEP 4: Vertical morphological filtering
# Use a tall, narrow kernel to keep only vertical structures
# and remove horizontal noise, crosses, etc.
# =====================================================
vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
vertical_mask = cv2.morphologyEx(dark_thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

# Close small gaps in the vertical structures
close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 5))
vertical_mask = cv2.morphologyEx(vertical_mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)

# =====================================================
# STEP 4b: Isolate only the slalom columns
# - Focus on the lower half of the image
# - Keep only structures near the left and right edges
# =====================================================
img_height, img_width = image.shape[:2]

# Find contours in the vertical mask
contours, _ = cv2.findContours(vertical_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Create a new mask with only the slalom columns
slalom_mask = np.zeros_like(vertical_mask)
print(f"\n=== Contour Debug Info ===")
print(f"Image size: {img_width}x{img_height}")
print(f"Lower region cutoff (40%): y > {img_height * 0.4:.0f}")
print(f"Left edge cutoff (35%):  x < {img_width * 0.35:.0f}")
print(f"Right edge cutoff (65%): x > {img_width * 0.65:.0f}")
print(f"Total contours found: {len(contours)}\n")

for i, c in enumerate(contours):
    x, y, w, h = cv2.boundingRect(c)
    center_x = x + w // 2
    bottom_y = y + h

    # Must START in the lower half (eliminates reflections in upper half)
    starts_in_lower_half = y > img_height * 0.4

    # Must be near the left or right edge of the image (not in the center)
    in_left = center_x < img_width * 0.35
    in_right = center_x > img_width * 0.65

    # Must be tall enough to be a slalom pole
    is_tall = h > 50

    # Must be a reasonable width (not a huge edge blob, not a thin noise line)
    reasonable_width = 5 < w < 60

    kept = starts_in_lower_half and (in_left or in_right) and is_tall and reasonable_width
    print(f"  Contour {i}: pos=({x},{y}) size=({w}x{h}) center_x={center_x} bottom_y={bottom_y} | starts_lower={starts_in_lower_half} left={in_left} right={in_right} tall={is_tall} width_ok={reasonable_width} → {'✅ KEPT' if kept else '❌ rejected'}")

    if kept:
        cv2.drawContours(slalom_mask, [c], -1, 255, -1)

# Replace the vertical mask with just the slalom columns
vertical_mask = slalom_mask

# =====================================================
# STEP 5: Canny edge detection on enhanced image
# =====================================================
blurred = cv2.GaussianBlur(enhanced, (5, 5), 1.4)
edges = cv2.Canny(blurred, 30, 100)

# Only keep edges within the vertical column mask
column_edges = cv2.bitwise_and(edges, edges, mask=vertical_mask)

# =====================================================
# STEP 6: Hough Line Transform to detect vertical lines
# This finds the straight slalom pole lines
# =====================================================
lines_image = image.copy()
lines = cv2.HoughLinesP(
    column_edges,
    rho=1,
    theta=np.pi / 180,
    threshold=15,
    minLineLength=25,
    maxLineGap=30
)

# Filter to keep only near-vertical lines and draw them
vertical_lines = []
if lines is not None:
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
        # Keep lines that are close to vertical (between 70-110 degrees)
        if 70 < angle < 110:
            vertical_lines.append(line[0])
            cv2.line(lines_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

# =====================================================
# DISPLAY RESULTS
# =====================================================
plt.figure(figsize=(18, 12))

plt.subplot(2, 4, 1)
plt.title('1. Original')
show_image(image)
plt.axis('off')

plt.subplot(2, 4, 2)
plt.title('2. Grayscale')
show_image(gray)
plt.axis('off')

plt.subplot(2, 4, 3)
plt.title('3. CLAHE Enhanced')
show_image(enhanced)
plt.axis('off')

plt.subplot(2, 4, 4)
plt.title('4. Dark Threshold (B&W)')
show_image(dark_thresh)
plt.axis('off')

plt.subplot(2, 4, 5)
plt.title('5. Vertical Mask')
show_image(vertical_mask)
plt.axis('off')

plt.subplot(2, 4, 6)
plt.title('6. Column Edges')
show_image(column_edges)
plt.axis('off')

plt.subplot(2, 4, 7)
plt.title(f'7. Hough Lines ({len(vertical_lines)} found)')
show_image(lines_image)
plt.axis('off')

# Show the columns overlaid on original
overlay = image.copy()
overlay[vertical_mask > 0] = [0, 255, 0]  # green overlay on columns
blended = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
plt.subplot(2, 4, 8)
plt.title('8. Columns Overlay')
show_image(blended)
plt.axis('off')

plt.tight_layout()
plt.show()

# Print summary
print(f"\n=== Slalom Column Detection Summary ===")
print(f"Vertical lines detected: {len(vertical_lines)}")
for i, (x1, y1, x2, y2) in enumerate(vertical_lines):
    angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
    print(f"  Line {i+1}: ({x1},{y1}) -> ({x2},{y2}), angle={angle:.1f}°")