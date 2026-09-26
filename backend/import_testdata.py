import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.services.import_excel import process_excel_import

def seed():
    db = SessionLocal()
    try:
        # Create admin
        admin = User(
            email="piyushagarwalnew@gmail.com",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()

        # Import excel
        file_path = "../Test Data/TestData1.xlsx"
        with open(file_path, "rb") as f:
            content = f.read()
            
        summary = process_excel_import(
            db=db,
            file_bytes=content,
            original_filename="TestData1.xlsx",
            campaign_name="Test Campaign 1",
            admin_id=admin.id
        )
        db.commit()
        print("Successfully imported!")
        print(summary)
    except Exception as e:
        db.rollback()
        print("Import failed:", e)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
