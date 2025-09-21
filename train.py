from ultralytics import YOLO
import torch

def main():
    """
    Main function to train the YOLOv8 model.
    """
    # Check for GPU availability
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🚀 Using device: {device}")

    # Load a pretrained YOLOv8 model
    # yolov8n.pt is small and fast, great for starting
    model = YOLO('yolov8n.pt')

    # Train the model on your dataset
    print("🔥 Starting model training...")
    results = model.train(
        data='data.yaml',
        epochs=50,
        imgsz=640,
        batch=16,  # Adjust if you get memory errors
        name='wildlife_detector_4_classes_v1'
    )
    print("✅ Training complete!")
    print(f"✨ Model and results saved to: {results.save_dir}")

if __name__ == '__main__':
    main()