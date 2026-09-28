"""
Seed Development Test User
Idempotent script to create or update the dedicated testing account:
Email: test@scamdetector.local
Password: Test@12345
Name: Scam Detector Test User
"""
import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import (
    init_db,
    get_users_collection,
    get_preferences_collection
)

TEST_USER_EMAIL = "test@scamdetector.local"
TEST_USER_PASSWORD = "Test@12345"
TEST_USER_NAME = "Scam Detector Test User"

def seed_test_user():
    init_db()
    users_col = get_users_collection()
    pref_col = get_preferences_collection()

    now = datetime.utcnow()
    hashed_password = generate_password_hash(TEST_USER_PASSWORD)

    existing_user = users_col.find_one({"email": TEST_USER_EMAIL})

    if existing_user:
        user_id = str(existing_user["_id"])
        users_col.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {
                "username": TEST_USER_NAME,
                "password": hashed_password,
                "updated_at": now,
                "token_version": existing_user.get("token_version", 1)
            }}
        )
        print(f"[OK] Existing test user updated: {TEST_USER_EMAIL} (ID: {user_id})")
    else:
        user_doc = {
            "username": TEST_USER_NAME,
            "email": TEST_USER_EMAIL,
            "password": hashed_password,
            "avatar_url": None,
            "created_at": now,
            "updated_at": now,
            "last_login": now,
            "token_version": 1
        }
        res = users_col.insert_one(user_doc)
        user_id = str(res.inserted_id)
        print(f"[OK] Created new test user: {TEST_USER_EMAIL} (ID: {user_id})")

    # Ensure preferences record exists
    pref_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "theme": "dark",
            "email_notifications": True,
            "analysis_notifications": True,
            "security_notifications": True,
            "density": "comfortable",
            "default_mode": "text",
            "updated_at": now
        }},
        upsert=True
    )
    print(f"[OK] Preferences ensured for test user (ID: {user_id})")
    return user_id

if __name__ == "__main__":
    try:
        uid = seed_test_user()
        print(f"[SUCCESS] Test user ready: {TEST_USER_EMAIL} (User ID: {uid})")
    except Exception as e:
        print(f"[ERROR] Failed to seed test user: {e}", file=sys.stderr)
        sys.exit(1)
