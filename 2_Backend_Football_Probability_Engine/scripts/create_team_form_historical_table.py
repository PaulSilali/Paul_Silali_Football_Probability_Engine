"""
Script to create team_form_historical table if it doesn't exist
Run this before batch ingesting team form data
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import get_db
from app.db.base import Base
from app.db.models import TeamFormHistorical

def create_table():
    """Create team_form_historical table if it doesn't exist"""
    db = next(get_db())
    try:
        # Check if table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'team_form_historical'
            );
        """))
        table_exists = result.scalar()
        
        if table_exists:
            print("✓ Table 'team_form_historical' already exists")
            
            # Check row count
            count_result = db.execute(text("SELECT COUNT(*) FROM team_form_historical"))
            count = count_result.scalar()
            print(f"  Current row count: {count:,}")
        else:
            print("✗ Table 'team_form_historical' does NOT exist")
            print("  Creating table...")
            
            # Create table using SQLAlchemy
            TeamFormHistorical.__table__.create(db.bind, checkfirst=True)
            db.commit()
            
            print("✓ Table 'team_form_historical' created successfully")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Checking team_form_historical table...")
    create_table()
    print("\nDone! You can now run the batch ingestion.")

