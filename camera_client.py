import cv2
import requests
import time
from ultralytics import YOLO
import threading  # <-- 1. IMPORT THREADING

# --- 1. CONFIGURATION ---
SERVER_URL = "http://10.79.125.60:5000/api/event" # Use Laptop 2's IP
CAMERA_ID = "CAM001"
MODEL_PATH_ANIMALS = 'best.pt'
MODEL_PATH_PEOPLE = 'yolov8n.pt' # Default YOLO model
MIN_CONFIDENCE = 0.75
COOLDOWN_SECONDS = 5 # Reduced cooldown for a faster demo

# --- NEW OPTIMIZATIONS ---
FRAME_SKIP = 3      # Only run detection every 3rd frame
PREDICT_IMG_SIZE = 320 # Resize image to 320x320 for much faster inference

# --- 2. ASYNC NETWORK FUNCTION ---
def send_alert_async(payload):
    """
    Sends the HTTP request in a separate thread
    to prevent the main loop from blocking.
    """
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=3)
        if response.status_code == 200:
            print("✅ Alert sent successfully (async).")
        else:
            print(f"❌ Failed to send alert (async). Server responded with: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ CONNECTION ERROR (async): Could not reach server at {SERVER_URL}")

# --- 3. INITIALIZATION ---
try:
    model_animals = YOLO(MODEL_PATH_ANIMALS)
    model_people = YOLO(MODEL_PATH_PEOPLE)
    print("✅ Animal and People models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}.")
    exit()

target_animal_classes = set(model_animals.names.values())
target_human_class_id = 0 

print(f"🎯 Targeting animals: {target_animal_classes}")
print("🎯 Targeting 'person' from the default model.")
print(f"⚡ Optimizations: Frame Skip={FRAME_SKIP}, Inference Size={PREDICT_IMG_SIZE}")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Error: Could not open webcam.")
    exit()

print("\n🚀 Hawkeye Camera Client is running...")
print("   Show an animal printout or step in front of the camera.")
print("   Press 'q' to quit.")

last_detection_time = 0
frame_count = 0  # <-- For frame skipping
last_known_box = []
last_known_label = ""

# --- 4. REAL-TIME DETECTION LOOP (OPTIMIZED) ---
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Warning: Failed to grab frame.")
            break
        
        frame_count += 1
        best_detection_this_frame = None # Holds detection *only* for this loop
        
        # --- Run models only every N frames ---
        if frame_count % FRAME_SKIP == 0:
            # --- Run Both Models (with faster inference size) ---
            results_animals = model_animals.predict(frame, imgsz=PREDICT_IMG_SIZE, verbose=False)
            results_people = model_people.predict(frame, imgsz=PREDICT_IMG_SIZE, verbose=False)

            best_detection = None
            best_conf = 0.0
            best_label = ""
            best_box = []

            # --- Process Animal Detections ---
            for res in results_animals:
                for box in res.boxes:
                    conf = float(box.conf[0])
                    if conf > best_conf:
                        best_conf = conf
                        best_detection = model_animals.names[int(box.cls[0])]
                        best_label = f"{best_detection} {conf:.2f}"
                        best_box = list(map(int, box.xyxy[0]))

            # --- Process People Detections ---
            for res in results_people:
                for box in res.boxes:
                    if int(box.cls[0]) == target_human_class_id:
                        conf = float(box.conf[0])
                        if conf > best_conf:
                            best_conf = conf
                            best_detection = "human" # Send "human" as the detection type
                            best_label = f"Human {conf:.2f}"
                            best_box = list(map(int, box.xyxy[0]))
            
            # --- Store results for drawing ---
            if best_conf > MIN_CONFIDENCE and best_box:
                last_known_box = best_box
                last_known_label = best_label
                best_detection_this_frame = best_detection # We found one!
            else:
                last_known_box = [] # Clear old box if nothing is found
                last_known_label = ""

        # --- Draw Best Bounding Box (runs every frame) ---
        if last_known_box:
            x1, y1, x2, y2 = last_known_box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, last_known_label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # --- Display the frame (runs every frame, so it's smooth) ---
        cv2.imshow('Hawkeye Camera Client (CAM001)', frame)

        # --- 5. SEND ALERT (with Confidence Check) ---
        current_time = time.time()
        
        # Check if we found a new detection on this specific frame
        if best_detection_this_frame and best_conf > MIN_CONFIDENCE and (current_time - last_detection_time > COOLDOWN_SECONDS):
            print(f"‼️ Detected {best_detection_this_frame} (Conf: {best_conf:.2f})! Sending alert...")
            
            payload = {
                "camera_id": CAMERA_ID,
                "detection": best_detection_this_frame,
                "confidence": best_conf
            }
            
            # --- NON-BLOCKING NETWORK CALL ---
            # Start the network request in a separate thread and DO NOT wait for it
            threading.Thread(target=send_alert_async, args=(payload,)).start()
            last_detection_time = current_time # Reset cooldown immediately

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Camera client shut down.")

