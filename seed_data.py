"""
Seed script to populate database with test data
Run with: python seed_data.py
"""
import sys
from datetime import datetime, timedelta
from app.db.base import SessionLocal
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.deal import Deal, DealType, DealStatus
from app.models.correspondence import Correspondence, CorrespondenceType
from app.core.security import get_password_hash


def seed_database():
    db = SessionLocal()

    try:
        print("Creating test organization...")
        org = Organization(
            name="ASEDO Energy Group",
            letterhead_config={
                "company_name": "ASEDO Energy Group",
                "address": "Lagos, Nigeria",
                "logo_url": None
            }
        )
        db.add(org)
        db.flush()

        print("Creating test users...")
        password = "password123"
        users = [
            User(
                email="duna@asedo.com",
                hashed_password=get_password_hash(password),
                full_name="Duna Jilang",
                role=UserRole.ADMIN,
                organization_id=org.id
            ),
            User(
                email="reviewer@asedo.com",
                hashed_password=get_password_hash(password),
                full_name="Legal Reviewer",
                role=UserRole.REVIEWER,
                organization_id=org.id
            ),
            User(
                email="agent@asedo.com",
                hashed_password=get_password_hash(password),
                full_name="Ground Agent",
                role=UserRole.AGENT,
                organization_id=org.id
            ),
        ]
        for user in users:
            db.add(user)
        db.flush()

        print("Creating test deals...")
        deal1 = Deal(
            organization_id=org.id,
            creator_id=users[0].id,
            deal_type=DealType.PROPERTY,
            status=DealStatus.NEGOTIATING,
            title="Reign Restaurant Property Acquisition",
            asset_description="Commercial property including restaurant building and land, located in prime Lagos district. Total plot size 5,000 sqm.",
            agreed_price=4450000000,
            currency="NGN",
            parties={
                "buyer": "ASEDO Energy Group",
                "seller": "Reign Holdings Limited"
            },
            terms={
                "payment_schedule": "30% deposit, 70% on completion",
                "closing_date": "2026-09-30"
            }
        )
        db.add(deal1)
        db.flush()

        deal2 = Deal(
            organization_id=org.id,
            creator_id=users[0].id,
            deal_type=DealType.JV_AGREEMENT,
            status=DealStatus.DRAFT,
            title="Project Teranga - Senegal Upstream JV",
            asset_description="Joint venture agreement for upstream oil & gas exploration in Senegal concession area",
            parties={
                "party_a": "ASEDO Energy Group",
                "party_b": "Petrosen (National Oil Company of Senegal)"
            }
        )
        db.add(deal2)
        db.flush()

        print("Creating sample correspondence...")
        corr1 = Correspondence(
            deal_id=deal1.id,
            correspondence_type=CorrespondenceType.OFFER,
            sender="ASEDO Energy Group",
            recipient="Reign Holdings Limited",
            subject="Offer to Purchase - Reign Restaurant Property",
            content="""Dear Reign Holdings,

We are pleased to submit our formal offer to acquire the commercial property known as Reign Restaurant, located at [ADDRESS].

Proposed Purchase Price: ₦4,450,000,000 (Four Billion, Four Hundred and Fifty Million Naira)

Payment Terms:
- 30% deposit upon execution of Sale and Purchase Agreement
- Remaining 70% upon completion and transfer of title

We propose a closing date of September 30, 2026.

This offer is subject to satisfactory due diligence and verification of all title documents.

Best regards,
Duna Jilang
Chief of Staff
ASEDO Energy Group""",
            correspondence_date=datetime.now() - timedelta(days=45)
        )
        db.add(corr1)

        corr2 = Correspondence(
            deal_id=deal1.id,
            correspondence_type=CorrespondenceType.COUNTER_OFFER,
            sender="Reign Holdings Limited",
            recipient="ASEDO Energy Group",
            subject="Re: Offer to Purchase - Reign Restaurant Property",
            content="""Dear ASEDO Energy Group,

Thank you for your offer. We accept the proposed price of ₦4,450,000,000.

However, we request the following modifications to payment terms:
- 40% deposit (instead of 30%)
- Remaining 60% upon completion

We agree to the September 30, 2026 closing date.

Please confirm acceptance of these revised terms.

Regards,
Reign Holdings Limited""",
            correspondence_date=datetime.now() - timedelta(days=38)
        )
        db.add(corr2)

        corr3 = Correspondence(
            deal_id=deal1.id,
            correspondence_type=CorrespondenceType.ANSWER,
            sender="ASEDO Energy Group",
            recipient="Reign Holdings Limited",
            subject="Re: Offer to Purchase - Reign Restaurant Property",
            content="""Dear Reign Holdings,

We accept the revised payment terms:
- 40% deposit upon execution of SPA
- 60% upon completion

We will proceed with preparation of the Sale and Purchase Agreement reflecting these terms.

Best regards,
Duna Jilang
ASEDO Energy Group""",
            correspondence_date=datetime.now() - timedelta(days=35)
        )
        db.add(corr3)

        db.commit()
        print("\n✅ Database seeded successfully!")
        print("\nTest credentials:")
        print("  Email: duna@asedo.com")
        print("  Password: password123")
        print("\nOther test users:")
        print("  reviewer@asedo.com / password123")
        print("  agent@asedo.com / password123")

    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
