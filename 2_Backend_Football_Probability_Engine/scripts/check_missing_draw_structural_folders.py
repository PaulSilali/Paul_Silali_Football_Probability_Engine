"""
Check which Draw Structural folders are missing in cleaned_data
"""
from pathlib import Path
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Expected folders based on code
EXPECTED_FOLDERS = [
    "Team_Form",
    "Rest_Days",
    "Odds_Movement",
    "h2h_stats",
    "Elo_Rating",
    "XG Data",  # Note: capital X, space
    "Weather",
    "League_structure",
    "Referee",
    "League_Priors"
]

def check_missing_folders():
    """Check which folders are missing in cleaned_data"""
    backend_root = Path(__file__).parent.parent
    
    ingestion_dir = backend_root / "data" / "1_data_ingestion" / "Draw_structural"
    cleaned_dir = backend_root / "data" / "2_Cleaned_data" / "Draw_structural"
    
    print("=" * 80)
    print("DRAW STRUCTURAL FOLDERS ANALYSIS")
    print("=" * 80)
    
    print("\n1. INGESTION FOLDER STATUS (1_data_ingestion/Draw_structural)")
    print("-" * 80)
    
    ingestion_folders = {}
    if ingestion_dir.exists():
        for folder in ingestion_dir.iterdir():
            if folder.is_dir() and folder.name != "01_logs":
                csv_count = len(list(folder.glob("*.csv")))
                ingestion_folders[folder.name] = csv_count
                status = "✓" if csv_count > 0 else "⊘ (empty)"
                print(f"  {status} {folder.name}: {csv_count} CSV files")
    else:
        print(f"  ✗ Directory does not exist: {ingestion_dir}")
    
    print("\n2. CLEANED FOLDER STATUS (2_Cleaned_data/Draw_structural)")
    print("-" * 80)
    
    cleaned_folders = {}
    if cleaned_dir.exists():
        for folder in cleaned_dir.iterdir():
            if folder.is_dir() and folder.name != "01_logs":
                csv_count = len(list(folder.glob("*.csv")))
                cleaned_folders[folder.name] = csv_count
                status = "✓" if csv_count > 0 else "⊘ (empty)"
                print(f"  {status} {folder.name}: {csv_count} CSV files")
    else:
        print(f"  ✗ Directory does not exist: {cleaned_dir}")
    
    print("\n3. MISSING FOLDERS ANALYSIS")
    print("-" * 80)
    
    missing_folders = []
    for folder_name in EXPECTED_FOLDERS:
        in_ingestion = folder_name in ingestion_folders
        in_cleaned = folder_name in cleaned_folders
        
        if in_ingestion and not in_cleaned:
            ingestion_count = ingestion_folders[folder_name]
            missing_folders.append({
                "folder": folder_name,
                "status": "MISSING",
                "reason": f"Exists in ingestion ({ingestion_count} CSV files) but NOT in cleaned_data",
                "ingestion_count": ingestion_count,
                "cleaned_count": 0
            })
            print(f"  ✗ {folder_name}: MISSING in cleaned_data")
            print(f"    → Has {ingestion_count} CSV files in ingestion folder")
            print(f"    → Should be copied to cleaned_data but folder doesn't exist")
        elif not in_ingestion and not in_cleaned:
            print(f"  ⊘ {folder_name}: Not ingested yet (no data in either folder)")
        elif in_ingestion and in_cleaned:
            ingestion_count = ingestion_folders[folder_name]
            cleaned_count = cleaned_folders[folder_name]
            if ingestion_count != cleaned_count:
                print(f"  ⚠ {folder_name}: Count mismatch")
                print(f"    → Ingestion: {ingestion_count} files")
                print(f"    → Cleaned: {cleaned_count} files")
            else:
                print(f"  ✓ {folder_name}: OK ({ingestion_count} files in both)")
    
    print("\n4. SUMMARY")
    print("-" * 80)
    
    if missing_folders:
        print(f"\n⚠ Found {len(missing_folders)} missing folder(s) in cleaned_data:")
        for item in missing_folders:
            print(f"\n  Folder: {item['folder']}")
            print(f"  Status: {item['status']}")
            print(f"  Reason: {item['reason']}")
            print(f"  Ingestion CSV count: {item['ingestion_count']}")
            print(f"  Cleaned CSV count: {item['cleaned_count']}")
        
        print("\n5. POSSIBLE REASONS")
        print("-" * 80)
        print("  • Data was ingested before save_to_cleaned=True was implemented")
        print("  • save_draw_structural_csv() was called with save_to_cleaned=False")
        print("  • Error occurred during CSV save to cleaned folder")
        print("  • Folder creation failed (permissions issue)")
        print("\n  SOLUTION:")
        print("  • Re-run batch ingestion for missing data types")
        print("  • Or manually copy CSV files from ingestion to cleaned folder")
    else:
        print("\n✓ All expected folders exist in cleaned_data!")
    
    return missing_folders

if __name__ == "__main__":
    missing = check_missing_folders()
    sys.exit(0 if len(missing) == 0 else 1)

