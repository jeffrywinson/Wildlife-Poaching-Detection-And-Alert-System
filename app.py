import os
import uuid
import time
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from flask import Flask, request, render_template, send_from_directory, jsonify
from ultralytics import YOLO

app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join('static', 'results'), exist_ok=True)

model = YOLO('best.pt')

# --- In-Memory Application State ---
APP_STATE = {
    "cameras": {
        "CAM001": {"lat": 12.9716, "lon": 77.5946, "name": "Koramangala Reserve", "last_detection": None},
        "CAM002": {"lat": 12.9791, "lon": 77.5929, "name": "Cubbon Park Outskirts", "last_detection": None},
        "CAM003": {"lat": 12.9515, "lon": 77.6322, "name": "Bellandur Wetlands", "last_detection": None},
        "CAM004": {"lat": 13.0356, "lon": 77.5623, "name": "Hebbal Lake North", "last_detection": None},
    },
    "active_zones": {},
    "alerts": [],
    "events": []
}
ACTIVE_ZONE_RADIUS_KM = 2.0
ACTIVE_ZONE_DURATION_HOURS = 1

# --- Helper Functions ---
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1; dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)); r = 6371
    return c * r

def add_event(message, is_threat=False):
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "is_threat": is_threat
    }
    APP_STATE["events"].insert(0, event)
    APP_STATE["events"] = APP_STATE["events"][:20]

def add_alert(message, camera_id):
    alert = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "camera_id": camera_id,
        "message": message
    }
    APP_STATE["alerts"].insert(0, alert)
    APP_STATE["alerts"] = APP_STATE["alerts"][:10]

def process_event(data):
    camera_id = data.get("camera_id")
    detection = data.get("detection")
    timestamp = datetime.now()

    if not all([camera_id, detection, camera_id in APP_STATE["cameras"]]):
        return

    cam_info = APP_STATE["cameras"][camera_id]
    cam_location = f"{cam_info['name']} ({camera_id})"
    
    # Update last detection for this camera
    cam_info["last_detection"] = {"type": detection, "timestamp": timestamp.isoformat()}
    
    # Clean up expired active zones
    expired_zones = [
        cid for cid, z in APP_STATE["active_zones"].items()
        if datetime.fromisoformat(z["timestamp"]) < timestamp - timedelta(hours=ACTIVE_ZONE_DURATION_HOURS)
    ]
    for cid in expired_zones:
        if cid in APP_STATE["active_zones"]:
            del APP_STATE["active_zones"][cid]
            add_event(f"Active Zone at {APP_STATE['cameras'][cid]['name']} has expired.")

    # Main Event Logic
    if detection in ['elephant', 'tiger', 'wolf', 'leopard']:
        APP_STATE["active_zones"][camera_id] = {
            "timestamp": timestamp.isoformat(), "lat": cam_info["lat"], "lon": cam_info["lon"]
        }
        add_event(f"🐾 {detection.capitalize()} spotted at {cam_location}. Area is now an Active Zone.")
    
    elif detection in ['human', 'vehicle']:
        is_in_active_zone = any(
            haversine(cam_info["lon"], cam_info["lat"], z["lon"], z["lat"]) <= ACTIVE_ZONE_RADIUS_KM
            for z in APP_STATE["active_zones"].values()
        )
        
        if is_in_active_zone:
            message = f"🚨 THREAT: Human/Vehicle detected at {cam_location} inside an active animal zone. Potential poacher."
            add_alert(message, camera_id)
            add_event(message, is_threat=True)
        else:
            add_event(f"🚶‍♂️ Human/Vehicle detected at {cam_location} (not in active zone). Monitoring.", is_threat=True)

# --- Routes (No changes here needed) ---
@app.route('/')
def dashboard(): return render_template('dashboard.html')

@app.route('/test')
def test_model_page(): return render_template('test_model.html')

@app.route('/api/event', methods=['POST'])
def handle_event():
    process_event(request.json)
    return jsonify({"status": "success"}), 200

@app.route('/api/get_state')
def get_state():
    return jsonify(APP_STATE)

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files: return "No file part", 400
    file = request.files['file']
    if file.filename == '': return "No selected file", 400
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