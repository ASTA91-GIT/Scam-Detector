"""
Database Configuration and Models
"""
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

client = None
db = None

def init_db():
    """Initialize MongoDB connection"""
    global client, db

    mongodb_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb://127.0.0.1:27017/"
    database_name = os.getenv("DATABASE_NAME", "job_scam_detector")

    try:
        client = MongoClient(mongodb_uri)
        db = client[database_name]

        # Test connection
        client.admin.command("ping")
        print(f"[OK] Connected to MongoDB: {database_name}")

        # Indexes (Phase 34: Database Indexes)
        db.users.create_index("email", unique=True)
        db.users.create_index("created_at")
        db.analyses.create_index([("user_id", 1), ("created_at", -1)])
        db.analyses.create_index("status")
        db.analyses.create_index("risk_level")
        db.shared_reports.create_index("token_hash", unique=True)
        db.shared_reports.create_index("public_id")
        db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
        db.audit_logs.create_index("event_type")
        db.sessions.create_index([("user_id", 1), ("session_id", 1)])
        db.saved_reports.create_index([("user_id", 1), ("created_at", -1)])
        db.notifications.create_index([("user_id", 1), ("read", 1), ("created_at", -1)])
        db.activity_logs.create_index([("user_id", 1), ("created_at", -1)])
        db.user_preferences.create_index("user_id", unique=True)
        # CaseAI Collections
        db.case_chat_messages.create_index([("case_id", 1), ("user_id", 1), ("created_at", 1)])
        db.case_memory.create_index([("case_id", 1), ("user_id", 1)], unique=True)
        # API Keys & Webhooks Collections
        db.api_keys.create_index([("user_id", 1), ("revoked", 1)])
        db.api_keys.create_index("key_hash", unique=True)
        db.webhooks.create_index([("user_id", 1), ("created_at", -1)])
        db.webhook_deliveries.create_index([("webhook_id", 1), ("created_at", -1)])

    except Exception as e:
        print(f"[ERROR] MongoDB connection error: {e}")
        raise


def get_db():
    return db

def get_database():
    return db

def get_users_collection():
    return db.users

def get_analyses_collection():
    return db.analyses

def get_offers_collection():
    return db.offers

def get_files_collection():
    return db.uploaded_files

def get_saved_reports_collection():
    return db.saved_reports

def get_notifications_collection():
    return db.notifications

def get_activity_logs_collection():
    return db.activity_logs

def get_audit_logs_collection():
    return db.audit_logs

def get_preferences_collection():
    return db.user_preferences

def get_case_chat_messages_collection():
    return db.case_chat_messages

def get_case_memory_collection():
    return db.case_memory

def get_api_keys_collection():
    return db.api_keys

def get_webhooks_collection():
    return db.webhooks

def get_webhook_deliveries_collection():
    return db.webhook_deliveries
