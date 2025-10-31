import cv2
import requests
import time
from ultralytics import YOLO

# --- 1. CONFIGURATION ---
SERVER_URL = "http://10.79.125.60:5000/api/event" # Use Laptop 2's IP
CAMERA_ID = "CAM001"
MODEL_PATH_ANIMALS = 'best.pt'
MODEL_PATH_PEOPLE = 'yolov8n.pt' # Default YOLO model
MIN_CONFIDENCE = 0.75
COOLDOWN_SECONDS = 5 # Reduced cooldown for a faster demo

# --- 2. INITIALIZATION ---
try:
    model_animals = YOLO(MODEL_PATH_ANIMALS)
    model_people = YOLO(MODEL_PATH_PEOPLE)
    print("✅ Animal and People models loaded successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}.")
    exit()

# Get class names for our custom animal model
target_animal_classes = set(model_animals.names.values())
# For the default model, 'person' is class 0
target_human_class_id = 0 

print(f"🎯 Targeting animals: {target_animal_classes}")
print("🎯 Targeting 'person' from the default model.")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Error: Could not open webcam.")
    exit()

print("\n🚀 Hawkeye Camera Client is running...")
print("   Show an animal printout or step in front of the camera.")
print("   Press 'q' to quit.")

last_detection_time = 0

# --- 3. REAL-TIME DETECTION LOOP ---
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Warning: Failed to grab frame.")
            break

        # --- Run Both Models ---
        results_animals = model_animals.predict(frame, verbose=False)
        results_people = model_people.predict(frame, verbose=False)

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
        
        # --- Draw Best Bounding Box ---
        if best_conf > MIN_CONFIDENCE and best_box:
            x1, y1, x2, y2 = best_box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, best_label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv2.imshow('Hawkeye Camera Client (CAM001)', frame)

        # --- 4. SEND ALERT (with Confidence Check) ---
        current_time = time.time()
        
        # Only send if confidence > 0.75 AND cooldown has passed
        if best_detection and best_conf > MIN_CONFIDENCE and (current_time - last_detection_time > COOLDOWN_SECONDS):
            print(f"‼️ Detected {best_detection} (Conf: {best_conf:.2f})! Sending alert...")
            
            payload = {
                "camera_id": CAMERA_ID,
                "detection": best_detection,
                "confidence": best_conf
            }
            
            try:
                response = requests.post(SERVER_URL, json=payload, timeout=3)
                if response.status_code == 200:
                    print("✅ Alert sent successfully.")
                    last_detection_time = current_time
                else:
                    print(f"❌ Failed to send alert. Server responded with: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ CONNECTION ERROR: Could not reach server at {SERVER_URL}")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Camera client shut down.")