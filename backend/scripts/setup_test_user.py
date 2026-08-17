from backend.database.session import SessionLocal
from backend.database.models import User, Organization
import uuid

db = SessionLocal()
org = db.query(Organization).first()
if not org:
    org = Organization(name="Test Org")
    db.add(org)
    db.commit()
    db.refresh(org)

user = db.query(User).first()
if not user:
    user = User(
        organization_id=org.id,
        email="test@example.com",
        hashed_password="dummy",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

print(f"{user.id},{org.id}")
