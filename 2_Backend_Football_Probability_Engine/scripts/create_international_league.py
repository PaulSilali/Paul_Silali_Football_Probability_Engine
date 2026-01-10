"""
Create International League for handling international matches
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.models import League
from app.core.database import SessionLocal

def create_international_league():
    """Create INT league if it doesn't exist"""
    db: Session = SessionLocal()
    try:
        # Check if INT league exists
        existing = db.query(League).filter(League.code == 'INT').first()
        
        if existing:
            print("✓ International League (INT) already exists")
            print(f"  ID: {existing.id}")
            print(f"  Name: {existing.name}")
            print(f"  Country: {existing.country}")
            return existing
        
        # Create INT league
        int_league = League(
            code='INT',
            name='International Matches',
            country='World',
            tier=0,  # Special tier for international
            is_active=True
        )
        db.add(int_league)
        db.commit()
        db.refresh(int_league)
        
        print("✓ Created International League (INT)")
        print(f"  ID: {int_league.id}")
        print(f"  Code: {int_league.code}")
        print(f"  Name: {int_league.name}")
        print(f"  Country: {int_league.country}")
        print(f"  Tier: {int_league.tier}")
        
        return int_league
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating International League: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_international_league()

