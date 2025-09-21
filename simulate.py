import requests
import json
import time
import random

FLASK_SERVER_URL = "http://127.0.0.1:5000/api/event"

CAMERAS = ["CAM001", "CAM002", "CAM003", "CAM004"]
DETECTIONS = ['elephant', 'tiger', 'wolf', 'leopard', 'human', 'vehicle']
# Increase weight for non-alerting events to make alerts more special
EVENT_WEIGHTS = [1, 1, 1, 1, 0.5, 0.5] 

def send_event():
    """Sends a randomly generated detection event to the server."""
    try:
        camera = random.choice(CAMERAS)
        # Use weights to make human/vehicle detections less frequent
        detection = random.choices(DETECTIONS, weights=EVENT_WEIGHTS, k=1)[0]
        
        payload = {
            "camera_id": camera,
            "detection": detection
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(FLASK_SERVER_URL, data=json.dumps(payload), headers=headers)
        
        if response.status_code == 200:
            print(f"✅  Event sent successfully: {payload}")
        else:
            print(f"❌  Failed to send event. Status: {response.status_code}, Response: {response.text}")

    except requests.exceptions.ConnectionError as e:
        print(f"🔌  Connection Error. Is the Flask server running? Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("🚀 Starting Hawkeye Camera Trap Simulator...")
    print(f"Will send events to {FLASK_SERVER_URL}")
    while True:
        send_event()
        sleep_duration = random.uniform(5, 15) # Send event every 5-15 seconds
        print(f"   ...sleeping for {sleep_duration:.1f} seconds...")
        time.sleep(sleep_duration)