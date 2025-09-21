import os
import shutil

# --- 1. Define Paths ---
# Note: These paths are relative to the root of your project folder.
RAW_DATA_BASE = 'data/raw/'
PROCESSED_DATA_BASE = 'data/processed/'

# Paths for each raw dataset
base_paths = {
    'elephant': os.path.join(RAW_DATA_BASE, 'elephant-detection-dataset/'),
    'leopard': os.path.join(RAW_DATA_BASE, 'leopard-detection-dataset/'),
    'wolf': os.path.join(RAW_DATA_BASE, 'wolf-detection-dataset/'),
    'tiger': os.path.join(RAW_DATA_BASE, 'tiger-detection-dataset/final_data/dataset/')
}

# Prefixes for renaming files to avoid name conflicts
class_prefixes = {
    'elephant': 'e',
    'leopard': 'l',
    'wolf': 'w',
    'tiger': 't'
}

# --- 2. Create the Destination Directory Structure ---
def setup_directories():
    """Creates the necessary output directories for the processed dataset."""
    print("🚀 Creating processed dataset directory structure...")
    for split in ['train', 'val']:
        os.makedirs(os.path.join(PROCESSED_DATA_BASE, 'images', split), exist_ok=True)
        os.makedirs(os.path.join(PROCESSED_DATA_BASE, 'labels', split), exist_ok=True)
    print("✅ Created directory structure in 'data/processed/'.")

# --- 3. Define the Core Processing Functions ---
def process_and_copy_files(src_img_dir, src_lbl_dir, dest_img_dir, dest_lbl_dir, class_prefix, dest_split_name, start_index=0):
    """Copies and renames all images and labels from a source to a destination directory."""
    if not os.path.exists(src_img_dir):
        print(f"❌ ERROR: Source directory not found, skipping: {src_img_dir}")
        return start_index

    image_filenames = [f for f in os.listdir(src_img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    current_index = start_index
    
    for img_filename in image_filenames:
        base_name, img_ext = os.path.splitext(img_filename)
        current_index += 1
        new_base_name = f"{class_prefix}_{dest_split_name}_{current_index:05d}"
        
        old_img_path = os.path.join(src_img_dir, img_filename)
        old_lbl_path = os.path.join(src_lbl_dir, base_name + '.txt')
        
        new_img_path = os.path.join(dest_img_dir, new_base_name + img_ext)
        new_lbl_path = os.path.join(dest_lbl_dir, new_base_name + '.txt')
        
        if os.path.exists(old_lbl_path):
            shutil.copy2(old_img_path, new_img_path)
            shutil.copy2(old_lbl_path, new_lbl_path)
        else:
            print(f"⚠️ Warning: Label not found for image, skipping: {old_img_path}")
            
    copied_count = len(image_filenames)
    print(f"  - Copied {copied_count} files using prefix '{class_prefix}' to '{dest_split_name}'.")
    return current_index

def update_labels_by_prefix(directory, file_prefix, new_id):
    """Updates the class ID in label files that start with a specific prefix."""
    count = 0
    if not os.path.isdir(directory):
        print(f"⚠️ Warning: Directory not found, skipping: {directory}")
        return

    for filename in os.listdir(directory):
        if filename.startswith(file_prefix):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            new_lines = [f"{new_id} {' '.join(line.strip().split()[1:])}\n" for line in lines]
            
            with open(filepath, 'w') as f:
                f.writelines(new_lines)
            count += 1
    print(f"  - Updated {count} files starting with '{file_prefix}' to class ID {new_id}.")


# --- Main Execution Block ---
def main():
    """Main function to run the full data preparation pipeline."""
    setup_directories()

    # --- 4. Process and Combine All Datasets ---
    print("\n🚀 Starting file processing...")
    counters = {key: 0 for key in [f"{p}_{s}" for p in class_prefixes.values() for s in ['train', 'val']]}

    for animal in ['elephant', 'leopard', 'wolf']:
        print(f"\nProcessing {animal.capitalize()}...")
        for src_split in ['train', 'valid', 'test']:
            dest_split = 'val' if src_split in ['valid', 'test'] else 'train'
            src_img_dir = os.path.join(base_paths[animal], src_split, 'images')
            src_lbl_dir = os.path.join(base_paths[animal], src_split, 'labels')
            dest_img_dir = os.path.join(PROCESSED_DATA_BASE, 'images', dest_split)
            dest_lbl_dir = os.path.join(PROCESSED_DATA_BASE, 'labels', dest_split)
            counter_key = f"{class_prefixes[animal]}_{dest_split}"
            new_count = process_and_copy_files(
                src_img_dir, src_lbl_dir, dest_img_dir, dest_lbl_dir,
                class_prefixes[animal], dest_split, counters[counter_key]
            )
            counters[counter_key] = new_count

    print(f"\nProcessing Tiger...")
    for src_split in ['train', 'val', 'test']:
        dest_split = 'val' if src_split in ['val', 'test'] else 'train'
        src_img_dir = os.path.join(base_paths['tiger'], 'images', src_split)
        src_lbl_dir = os.path.join(base_paths['tiger'], 'labels', src_split)
        dest_img_dir = os.path.join(PROCESSED_DATA_BASE, 'images', dest_split)
        dest_lbl_dir = os.path.join(PROCESSED_DATA_BASE, 'labels', dest_split)
        counter_key = f"{class_prefixes['tiger']}_{dest_split}"
        new_count = process_and_copy_files(
            src_img_dir, src_lbl_dir, dest_img_dir, dest_lbl_dir,
            class_prefixes['tiger'], dest_split, counters[counter_key]
        )
        counters[counter_key] = new_count
    
    print("\n\n🎉 All files have been copied and renamed successfully!")

    # --- 5. Adjust Class Labels ---
    print("\n🚀 Adjusting class labels...")
    labels_base_path = os.path.join(PROCESSED_DATA_BASE, 'labels/')
    
    # Class mapping: 0: elephant, 1: tiger, 2: wolf, 3: leopard
    print("\nProcessing Tigers:")
    update_labels_by_prefix(os.path.join(labels_base_path, 'train'), 't_', 1)
    update_labels_by_prefix(os.path.join(labels_base_path, 'val'), 't_', 1)

    print("\nProcessing Wolves:")
    update_labels_by_prefix(os.path.join(labels_base_path, 'train'), 'w_', 2)
    update_labels_by_prefix(os.path.join(labels_base_path, 'val'), 'w_', 2)

    print("\nProcessing Leopards:")
    update_labels_by_prefix(os.path.join(labels_base_path, 'train'), 'l_', 3)
    update_labels_by_prefix(os.path.join(labels_base_path, 'val'), 'l_', 3)
    
    print("\n\n✅ Finished adjusting all class labels.")
    print("\n✨ Dataset preparation complete! ✨")


if __name__ == '__main__':
    main()