import os
import uuid
import time
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from flask import Flask, request, render_template, send_from_directory, jsonify
from ultralytics import YOLO
import requests

# --- 1. CONFIGURATION ---
from contacts import CONTACTS_DB  # Import your contact database

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join('static', 'results'), exist_ok=True)

model = YOLO('best.pt')

# --- Agent Configuration ---
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/65dc76d9-b318-47c7-aa16-919906ec5d94"
MIN_CONFIDENCE_TO_PROCESS = 0.75

# --- Animal Alert Level Classification ---
ANIMAL_ALERT_LEVELS = {
    "tiger": "Red",
    "elephant": "Orange",
    "leopard": "Orange",
    "rhino": "Orange",
    "wolf": "Orange",
    "deer": "Yellow",
}

# --- 2. IN-MEMORY STATE ---
APP_STATE = {
    "cameras": {
        "CAM001": {"lat": 12.9716, "lon": 77.5946, "last_detection": None, "last_animal_in_zone": None},
        "CAM002": {"lat": 12.9791, "lon": 77.5929, "last_detection": None, "last_animal_in_zone": None},
        "CAM003": {"lat": 12.9515, "lon": 77.6322, "last_detection": None, "last_animal_in_zone": None},
        "CAM004": {"lat": 13.0356, "lon": 77.5623, "last_detection": None, "last_animal_in_zone": None},
    },
    "active_zones": {},
    "alerts": [],
    "events": []
}
ACTIVE_ZONE_RADIUS_KM = 2.0
ACTIVE_ZONE_DURATION_HOURS = 1

# --- 3. HELPER FUNCTIONS ---
def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great-circle distance between two points on the earth."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers.
    return c * r

def add_event(message, is_threat=False):
    """Adds a new event to the state, keeping only the last 20."""
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "is_threat": is_threat
    }
    APP_STATE["events"].insert(0, event)
    APP_STATE["events"] = APP_STATE["events"][:20]

def add_alert(message, camera_id):
    """Adds a new high-priority alert."""
    alert = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "camera_id": camera_id,
        "message": message
    }
    APP_STATE["alerts"].insert(0, alert)
    APP_STATE["alerts"] = APP_STATE["alerts"][:10]

# --- 4. AGENT LOGIC ---
def trigger_agentic_alert(alert_level, animal_type, camera_id, location_name):
    """
    Looks up contacts from the DB, builds the phone number list,
    and sends it to the n8n agent workflow.
    """
    
    phone_numbers = []
    contacts = CONTACTS_DB.get(camera_id)
    
    if not contacts:
        print(f"❌ Error: No contacts found for camera_id {camera_id}")
        return

    # Build the alert list based on level
    if alert_level == "Yellow":
        phone_numbers.append(contacts["guard"])
        
    elif alert_level == "Orange":
        phone_numbers.append(contacts["guard"])
        phone_numbers.append(contacts["deputy_ranger"])
        
    elif alert_level == "Red":
        phone_numbers.append(contacts["guard"])
        phone_numbers.append(contacts["deputy_ranger"])
        phone_numbers.append(contacts["range_officer"])

    # Send the list of numbers to n8n
    message = f"{alert_level} ALERT! Human spotted in {animal_type.capitalize()} zone at {location_name}."
    payload = {
        "message": message,
        "phone_numbers": phone_numbers  # Pass the whole list
    }
    
    try:
        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=3)
        print(f"✅ Agentic alert triggered: {alert_level} at {location_name}. Notifying {len(phone_numbers)} officer(s).")
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED TO TRIGGER N8N AGENT: {e}")

# --- 5. CORE EVENT LOGIC ---
def process_event(data):
    camera_id = data.get("camera_id")
    detection = data.get("detection")
    confidence = data.get("confidence", 0.0)
    timestamp = datetime.now()

    if confidence <= MIN_CONFIDENCE_TO_PROCESS:
        return
    if not all([camera_id, detection, camera_id in APP_STATE["cameras"]]):
        return

    cam_info = APP_STATE["cameras"][camera_id]
    cam_location_name = CONTACTS_DB.get(camera_id, {}).get("location_name", "Unknown Zone")
    cam_info["last_detection"] = {"type": detection, "timestamp": timestamp.isoformat()}
    
    # Clean expired zones
    expired_zones = [
        cid for cid, z in APP_STATE["active_zones"].items()
        if datetime.fromisoformat(z["timestamp"]) < timestamp - timedelta(hours=ACTIVE_ZONE_DURATION_HOURS)
    ]
    for cid in expired_zones:
        if cid in APP_STATE["active_zones"]:
            del APP_STATE["active_zones"][cid]
            APP_STATE["cameras"][cid]["last_animal_in_zone"] = None
            expired_location = CONTACTS_DB.get(cid, {}).get("location_name", "Unknown Zone")
            add_event(f"Active Zone at {expired_location} has expired.")

    # Main Event Logic
    if detection in ANIMAL_ALERT_LEVELS:
        animal_type = detection.capitalize()
        APP_STATE["active_zones"][camera_id] = {
            "timestamp": timestamp.isoformat(), "lat": cam_info["lat"], "lon": cam_info["lon"]
        }
        cam_info["last_animal_in_zone"] = detection
        add_event(f"🐾 {animal_type} spotted at {cam_location_name}. Area is now an Active Zone.")
    
    elif detection == 'human':
        threat_location_name = cam_location_name
        active_zone_animal = None
        origin_camera_id = camera_id  # The camera that saw the human
        
        for zone_cam_id, zone_data in APP_STATE["active_zones"].items():
            distance = haversine(cam_info["lon"], cam_info["lat"], zone_data["lon"], zone_data["lat"])
            if distance <= ACTIVE_ZONE_RADIUS_KM:
                active_zone_animal = APP_STATE["cameras"][zone_cam_id].get("last_animal_in_zone")
                origin_camera_id = zone_cam_id
                zone_location_name = CONTACTS_DB.get(zone_cam_id, {}).get("location_name", "Unknown Zone")
                threat_location_name = f"{cam_location_name} (near {zone_location_name} zone)"
                break
        
        if active_zone_animal:
            alert_level = ANIMAL_ALERT_LEVELS.get(active_zone_animal, "Yellow")
            message = f"🚨 THREAT: Human detected at {threat_location_name}. Animal in zone: {active_zone_animal.capitalize()}"
            
            add_alert(message, camera_id)
            add_event(message, is_threat=True)
            
            # AGENT ACTION
            trigger_agentic_alert(alert_level, active_zone_animal, origin_camera_id, threat_location_name)
        else:
            add_event(f"🚶‍♂️ Human detected at {cam_location_name} (not in active zone). Monitoring.", is_threat=True)

# --- 6. ROUTES ---
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/test')
def test_model_page():
    return render_template('test_model.html')

@app.route('/api/event', methods=['POST'])
def handle_event():
    process_event(request.json)
    return jsonify({"status": "success"}), 200

@app.route('/api/get_state')
def get_state():
    # This is the line that was fixed (removed the extra '.')
    return jsonify(APP_STATE)

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        ext = os.path.splitext(file.filename)[1]
        unique_filename = str(uuid.uuid4()) + ext
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        results = model.predict(source=filepath, save=True, project='static', name='results', exist_ok=True)
        return send_from_directory(results[0].save_dir, os.path.basename(filepath))
    return "Error processing file", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
