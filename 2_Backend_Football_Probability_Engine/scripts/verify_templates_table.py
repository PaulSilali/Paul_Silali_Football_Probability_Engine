"""
Quick script to verify the saved_jackpot_templates table exists
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from sqlalchemy import inspect

def check_table_exists():
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'saved_jackpot_templates' in tables:
            print("✅ Table 'saved_jackpot_templates' exists")
            
            # Check columns
            columns = inspector.get_columns('saved_jackpot_templates')
            print(f"\nColumns ({len(columns)}):")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")
            
            return True
        else:
            print("❌ Table 'saved_jackpot_templates' does NOT exist")
            print(f"\nAvailable tables: {', '.join(tables)}")
            print("\n⚠️  Please run the migration:")
            print("   3_Database_Football_Probability_Engine/migrations/add_saved_jackpot_templates.sql")
            return False
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    check_table_exists()

