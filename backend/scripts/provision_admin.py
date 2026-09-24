"""
Script to provision the initial administrator account.

Usage:
    cd backend
    export PYTHONPATH=.
    .venv/bin/python scripts/provision_admin.py
"""

import sys
import os

# Add the backend directory to python path if not already there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.config import settings


def provision_admin():
    db = SessionLocal()
    try:
        admin_email = settings.admin_email.lower()
        print(f"Configured admin email: {admin_email}")

        # 1. Deactivate obsolete admin
        obsolete_email = "admin@poornima.org"
        obsolete_admin = db.query(User).filter(User.email == obsolete_email).first()
        if obsolete_admin and obsolete_admin.is_active:
            print(f"Deactivating obsolete admin account: {obsolete_email}")
            obsolete_admin.is_active = False

        # 2. Create or update true admin
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if admin_user:
            print(f"Admin user {admin_email} already exists. Updating role and status.")
            admin_user.role = UserRole.ADMIN
            admin_user.is_active = True
        else:
            print(f"Creating new admin user: {admin_email}")
            admin_user = User(
                email=admin_email,
                role=UserRole.ADMIN,
                is_active=True,
                google_subject_id=None,
            )
            db.add(admin_user)

        db.commit()
        print("Provisioning completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error provisioning admin: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    provision_admin()
