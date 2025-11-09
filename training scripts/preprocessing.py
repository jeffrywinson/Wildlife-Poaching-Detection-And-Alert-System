import os
import shutil
import glob
import random
import math

# --- 1. DEFINE CORRECT PATHS ---
# This is the path to your ORIGINAL 7-class dataset
SOURCE_DATA_PATH = 'G:/Poaching_Project/final_dataset/kaggle/working/final_dataset'

# This is the path to your main project folder
PROJECT_PATH = 'G:/Poaching_Project'

# This is the NEW folder we will create for the 5-class dataset
OUTPUT_PATH = os.path.join(PROJECT_PATH, 'final_dataset_5_class')

print(f"🧹 Starting clean... Deleting old '{OUTPUT_PATH}' if it exists.")
shutil.rmtree(OUTPUT_PATH, ignore_errors=True)

# --- 2. CONFIGURATION (5-CLASS, BALANCED) ---
CLASS_NAMES = ['elephant', 'tiger', 'wolf', 'leopard', 'jeep']
TRAIN_LIMIT = 1800  # Balance for training
VAL_TEST_LIMIT = 300 # Balance for validation and testing

# This dictionary defines the *source* files to look for
DATASETS = {
    'elephant': {'prefix': 'e_', 'id': 0, 'name': 'ELEPHANT'},
    'tiger':    {'prefix': 't_', 'id': 1, 'name': 'TIGER'},
    'wolf':     {'prefix': 'w_', 'id': 2, 'name': 'WOLF'},
    'leopard':  {'prefix': 'l_', 'id': 3, 'name': 'LEOPARD'},
    'jeep':     {'prefix': 'j_', 'id': 4, 'name': 'JEEP'},
}

print(f"🚀 Creating new, clean 5-class directory structure at: {OUTPUT_PATH}")
for split in ['train', 'val', 'test']:
    os.makedirs(os.path.join(OUTPUT_PATH, 'images', split), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_PATH, 'labels', split), exist_ok=True)

# --- 3. HELPER FUNCTION TO COPY AND REMAP ---
def copy_and_remap(img_paths_list, source_label_dir, dest_img_dir, dest_lbl_dir, new_id):
    copied_count = 0
    for img_path in img_paths_list:
        try:
            # Get paths for old img/label
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            lbl_path = os.path.join(source_label_dir, f"{base_name}.txt")
            
            if not os.path.exists(lbl_path):
                continue
            
            # Define new paths
            new_img_path = os.path.join(dest_img_dir, os.path.basename(img_path))
            new_lbl_path = os.path.join(dest_lbl_dir, f"{base_name}.txt")

            # 1. Copy the image
            shutil.copy(img_path, new_img_path)
            
            # 2. Read old label, rewrite ID, and save to new location
            with open(lbl_path, 'r') as f_in:
                lines = f_in.readlines()
            
            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) > 1:
                    # This is the remap: we set the class ID to the new one (0-4)
                    new_lines.append(f"{new_id} {' '.join(parts[1:])}\n")
            
            if new_lines: # Only write if we have labels
                with open(new_lbl_path, 'w') as f_out:
                    f_out.writelines(new_lines)
                copied_count += 1
                
        except Exception as e:
            print(f"    - ERROR processing {img_path}: {e}")
    return copied_count

# --- 4. MAIN PROCESSING LOOP ---
for split in ['train', 'val', 'test']:
    print(f"\n🚀 Processing {split.upper()} set...")
    
    # Set the limit for the current split
    if split == 'train':
        limit = TRAIN_LIMIT
        print(f"   - Train limit set to {limit}")
    else:
        limit = VAL_TEST_LIMIT
        print(f"   - Val/Test limit set to {limit}")

    for key, details in DATASETS.items():
        print(f"\nProcessing: {details['name']} (New ID {details['id']}) for {split}")
        
        # Define source paths
        src_img_glob = os.path.join(SOURCE_DATA_PATH, 'images', split, f"{details['prefix']}*.*")
        src_lbl_dir = os.path.join(SOURCE_DATA_PATH, 'labels', split)
        
        # Get all image files for this class
        src_img_paths = [f for f in glob.glob(src_img_glob) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(src_img_paths)
        
        print(f"    - Found {len(src_img_paths)} original images.")
        
        # Apply the balance limit (unless it's 'train' and we have fewer than the limit)
        if split != 'train' or len(src_img_paths) > limit:
            src_img_paths = src_img_paths[:limit]
            print(f"    - Limiting to {len(src_img_paths)} images.")
        
        # Define destination paths
        dest_img_dir = os.path.join(OUTPUT_PATH, 'images', split)
        dest_lbl_dir = os.path.join(OUTPUT_PATH, 'labels', split)
        
        count = copy_and_remap(src_img_paths, src_lbl_dir, dest_img_dir, dest_lbl_dir, details['id'])
        print(f"    - Copied {count} files to '{split}'.")

print("\n\n🎉 --- ALL DONE! ---")
print(f"Your new, clean, 5-class dataset is ready in '{OUTPUT_PATH}'.")
print("All splits (train, val, test) are now balanced.")