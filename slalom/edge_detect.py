from numpy import result_type
import cv2
import matplotlib.pyplot as plt
# from google.colab import files
import numpy as np

# Read the uploaded image
# image_path = next(iter(uploaded))
# image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# image = cv2.imread("./media/gate_task.png", cv2.IMREAD_GRAYSCALE)
image = cv2.imread("./media/gate_task.png")

# coverting it to HSV

hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# white detection
lower_white = np.array([0, 0, 180])
upper_white = np.array([180, 30, 225])
white_mask = cv2.inRange(hsv, lower_white, upper_white)

# simple white balance
def correct_underwater(image):
    b, g, r = cv2.split(image)
    r = cv2.equalizeHist(r)
    b = cv2.equalizeHist(b) # reduce the blue dominance

    return cv2.merge([b, g, r])

correct = correct_underwater(image)

# get the color mask
# combined_mask = cv2.bitwise_or(white_mask)

# applying gaussian blur to reduce noise
blurred_image = cv2.GaussianBlur(image, (5, 5), 1.4)

# applying canny edge detector
edges = cv2.Canny(blurred_image, 50, 100)

# Only keep edges that are near your colors
result = cv2.bitwise_and(edges, edges, mask=white_mask)

# display the original image and the edge-detected image
plt.figure(figsize=(10, 5))
plt.subplot(1, 3, 1)
plt.title('Original Image')
plt.imshow(image, cmap='gray')
plt.axis('off')

plt.subplot(1, 3, 2)
plt.title('Blurred Image')
plt.imshow(blurred_image, cmap='gray')
plt.axis('off')

plt.subplot(1, 3, 3)
plt.title('Edge Detected Image')
plt.imshow(edges, cmap='gray')
plt.axis('off')
plt.show()