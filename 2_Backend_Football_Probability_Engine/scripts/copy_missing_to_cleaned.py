"""
Copy missing CSV files from ingestion to cleaned_data folders
"""
from pathlib import Path
import shutil
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def copy_missing_folders():
    """Copy missing folders from ingestion to cleaned_data"""
    backend_root = Path(__file__).parent.parent
    
    ingestion_dir = backend_root / "data" / "1_data_ingestion" / "Draw_structural"
    cleaned_dir = backend_root / "data" / "2_Cleaned_data" / "Draw_structural"
    
    # Ensure cleaned directory exists
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("COPYING MISSING FOLDERS TO CLEANED_DATA")
    print("=" * 80)
    
    # Folders that need to be copied
    folders_to_copy = ["Referee", "XG Data"]
    
    copied_count = 0
    skipped_count = 0
    
    for folder_name in folders_to_copy:
        ingestion_folder = ingestion_dir / folder_name
        cleaned_folder = cleaned_dir / folder_name
        
        if not ingestion_folder.exists():
            print(f"\n⊘ {folder_name}: Not found in ingestion folder, skipping")
            skipped_count += 1
            continue
        
        csv_files = list(ingestion_folder.glob("*.csv"))
        if len(csv_files) == 0:
            print(f"\n⊘ {folder_name}: No CSV files in ingestion folder, skipping")
            skipped_count += 1
            continue
        
        # Create cleaned folder
        cleaned_folder.mkdir(parents=True, exist_ok=True)
        
        # Copy CSV files
        copied_files = 0
        for csv_file in csv_files:
            dest_file = cleaned_folder / csv_file.name
            if not dest_file.exists():
                shutil.copy2(csv_file, dest_file)
                copied_files += 1
        
        if copied_files > 0:
            print(f"\n✓ {folder_name}: Copied {copied_files} CSV files")
            print(f"  From: {ingestion_folder}")
            print(f"  To: {cleaned_folder}")
            copied_count += copied_files
        else:
            existing_count = len(list(cleaned_folder.glob("*.csv")))
            print(f"\n✓ {folder_name}: Already exists ({existing_count} files), skipped")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files copied: {copied_count}")
    print(f"Folders skipped: {skipped_count}")
    
    return copied_count

if __name__ == "__main__":
    copied = copy_missing_folders()
    sys.exit(0 if copied > 0 else 1)

