import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

# https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python#live-stream
# Live demo: https://mediapipe-studio.webapps.google.com/demo/hand_landmarker

# ─── Drawing config ───────────────────────────────────────────────────────────

MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)  # vibrant green

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17)
]

# ─── Drawing function (replaces draw_landmarks_on_image) ─────────────────────

def draw_landmarks_on_image(frame, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    annotated_image = np.copy(frame)
    h, w = annotated_image.shape[:2]

    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]

        # Draw connections
        for a, b in CONNECTIONS:
            x1, y1 = int(hand_landmarks[a].x * w), int(hand_landmarks[a].y * h)
            x2, y2 = int(hand_landmarks[b].x * w), int(hand_landmarks[b].y * h)
            cv2.line(annotated_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Draw joints
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(annotated_image, (cx, cy), 5, (0, 0, 255), -1)

        # Draw handedness label (Left/Right)
        x_coordinates = [lm.x for lm in hand_landmarks]
        y_coordinates = [lm.y for lm in hand_landmarks]
        text_x = int(min(x_coordinates) * w)
        text_y = int(min(y_coordinates) * h) - MARGIN

        cv2.putText(annotated_image, f"{handedness[0].category_name}",
                    (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                    FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)

    return annotated_image

# ─── MediaPipe setup ──────────────────────────────────────────────────────────

latest_result = None

def result_callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result

options = vision.HandLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path='hand_landmarker.task'),
    running_mode=vision.RunningMode.LIVE_STREAM,
    num_hands=2,
    result_callback=result_callback
)
detector = vision.HandLandmarker.create_from_options(options)

# ─── Main loop ────────────────────────────────────────────────────────────────

cap = cv2.VideoCapture(1)  # change to 1 or 2 if wrong camera

print("Press 'q' to quit.")

start_time = time.time()
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    # Convert to RGB for MediaPipe
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    # Run detection
    detector.detect_async(mp_image, int((time.time()-start_time) * 1000))

    # Draw landmarks if we have a result
    if latest_result is not None:
        frame = draw_landmarks_on_image(frame, latest_result)

    cv2.imshow("Hand Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
detector.close()