"""
Create Admin User Script

Creates a system admin account with full access to the admin portal.

Usage:
    python -m scripts.create_admin
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.user import User, UserRole, UserType
from app.models.organization import Organization
from app.core.security import get_password_hash
import uuid


def create_admin_user(db: Session):
    """Create the admin user if it doesn't exist."""

    admin_email = "admin@example.com"
    admin_password = "password"

    # Check if admin already exists
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        print(f"✓ Admin user already exists: {admin_email}")
        print(f"  Role: {existing_admin.role}")
        return existing_admin

    # Create System organization for admin
    system_org = db.query(Organization).filter(Organization.name == "System").first()
    if not system_org:
        system_org = Organization(
            name="System",
            credit_balance=999999,  # Unlimited credits for admin
            is_early_adopter=False,
        )
        db.add(system_org)
        db.flush()
        print(f"✓ Created System organization")

    # Create admin user
    admin_user = User(
        email=admin_email,
        hashed_password=get_password_hash(admin_password),
        full_name="System Administrator",
        phone=None,
        user_type=UserType.INTERNAL,
        role=UserRole.ADMIN,  # ADMIN role (not OWNER)
        organization_id=system_org.id,
        email_verified=True,  # Pre-verified
        is_active=True,
    )
    db.add(admin_user)
    db.commit()

    print("✓ Admin user created successfully!")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"  Role: {admin_user.role}")
    print(f"  Organization: {system_org.name}")
    print()
    print("⚠️  IMPORTANT: Change the password after first login!")
    print("   Access admin portal at: http://localhost:3000/admin")

    return admin_user


def main():
    """Main execution."""
    print("Creating admin user...")
    print()

    db = SessionLocal()
    try:
        create_admin_user(db)
    except Exception as e:
        print(f"✗ Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
