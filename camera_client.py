import cv2
import requests
import time
from ultralytics import YOLO

# --- 1. CONFIGURATION ---

# !! CRITICAL: Change this to the IP address of Laptop 2 (your server) !!
#    Find it by running 'ipconfig' (Windows) or 'ifconfig' (macOS/Linux)
#    on Laptop 2. DO NOT use 'localhost' or '127.0.0.1'.
SERVER_URL = "http://<LAPTOP_2_IP_ADDRESS>:5000/api/event"

# The name of the camera this laptop represents
CAMERA_ID = "CAM001"

# Path to your trained model
MODEL_PATH = 'best.pt'

# Cooldown (in seconds) to prevent spamming the server
COOLDOWN_SECONDS = 10 

# --- 2. INITIALIZATION ---

try:
    model = YOLO(MODEL_PATH)
    print(f"✅ Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    print(f"❌ Error loading model: {e}. Make sure 'best.pt' is in the same folder.")
    exit()

# Get class names from the model (e.g., ['elephant', 'tiger', 'wolf', 'leopard'])
target_classes = set(model.names.values())
print(f"🎯 Targeting {len(target_classes)} classes: {target_classes}")

cap = cv2.VideoCapture(0)  # Open default webcam (usually 0)
if not cap.isOpened():
    print("❌ Error: Could not open webcam.")
    exit()

print("\n🚀 Hawkeye Camera Client is running...")
print("   Point your tiger printout at the webcam.")
print("   Press 'q' to quit.")

last_detection_time = 0

# --- 3. REAL-TIME DETECTION LOOP ---

try:
    while True:
        # Read a frame from the webcam
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Warning: Failed to grab frame.")
            break

        # Run YOLOv8 prediction on the frame
        # verbose=False silences the per-frame console logs
        results = model.predict(frame, verbose=False)

        detected_animal = None
        
        # Process results
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                
                # Check if the detected object is one of our targets
                if class_name in target_classes:
                    detected_animal = class_name
                    
                    # Draw a bounding box for your demo
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    label = f"{class_name} {conf:.2f}"
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    
                    # Found one, stop looping for this frame
                    break
            if detected_animal:
                break

        # Show the live feed in a window
        cv2.imshow('Hawkeye Camera Client (CAM001)', frame)

        # --- 4. SEND ALERT (WITH COOLDOWN) ---
        
        current_time = time.time()
        # Check if we detected an animal AND the cooldown has passed
        if detected_animal and (current_time - last_detection_time > COOLDOWN_SECONDS):
            print(f"‼️ Detected {detected_animal}! Sending alert to server...")
            
            payload = {
                "camera_id": CAMERA_ID,
                "detection": detected_animal
            }
            
            try:
                # Send the detection to the server
                response = requests.post(SERVER_URL, json=payload, timeout=3)
                
                if response.status_code == 200:
                    print(f"✅ Alert for {detected_animal} sent successfully.")
                    last_detection_time = current_time  # Reset the cooldown timer
                else:
                    print(f"❌ Failed to send alert. Server responded with: {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                print(f"❌ CONNECTION ERROR: Could not reach server at {SERVER_URL}")
                print("   1. Is the server running on Laptop 2?")
                print(f"   2. Is the IP address '{SERVER_URL}' correct?")
                print(f"   3. Are both laptops on the same Wi-Fi network?")

        # Check for 'q' key press to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Camera client shut down.")