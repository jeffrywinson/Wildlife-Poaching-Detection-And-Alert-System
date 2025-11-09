# train_5_class.py
from ultralytics import YOLO
import os
from multiprocessing import freeze_support

# --- 1. SET UP PATHS ---
# Get the full path to the current folder
project_directory = os.path.dirname(os.path.abspath(__file__))
yaml_path = os.path.join(project_directory, 'poaching_5_class.yaml')
runs_path = os.path.join(project_directory, 'runs_5_class') # New runs folder

print(f"Project Directory: {project_directory}")
print(f"YAML Path: {yaml_path}")
print(f"Runs Path: {runs_path}")

# --- THIS IS THE FIX FOR WINDOWS ---
if __name__ == '__main__':
    
    freeze_support() # Add this line for stability

    # --- 2. LOAD MODEL ---
    print("\n🧠 Loading pretrained model (yolov8s.pt)...")
    model = YOLO('yolov8s.pt') 

    # --- 3. START TRAINING ---
    print("\n🚀 Starting 5-Class Training (Max Augmentations, 100 Epochs)...")
    results = model.train(
        data=yaml_path,
        epochs=100,
        imgsz=640,
        batch=8,    # Safe batch size for your 6GB VRAM
        name='poaching_detector_5class_v1', 
        workers=8,  # Use 8 workers for fast data loading
        patience=50,
        save=True,
        project=runs_path,
        
        # --- BASIC AUGMENTATIONS ---
        augment=True,
        
        # --- ADVANCED AUGMENTATIONS ---
        mosaic=1.0,
        mixup=0.2,
        copy_paste=0.3
    )
    
    print("\n🎉 --- 5-CLASS TRAINING COMPLETE! ---")