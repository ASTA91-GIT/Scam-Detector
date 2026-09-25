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

        # Indexes
        db.users.create_index("email", unique=True)
        db.analyses.create_index([("user_id", 1), ("created_at", -1)])
        db.analyses.create_index("risk_level")
        db.saved_reports.create_index([("user_id", 1), ("created_at", -1)])
        db.notifications.create_index([("user_id", 1), ("read", 1), ("created_at", -1)])
        db.activity_logs.create_index([("user_id", 1), ("created_at", -1)])
        db.user_preferences.create_index("user_id", unique=True)
        # CaseAI Collections
        db.case_chat_messages.create_index([("case_id", 1), ("user_id", 1), ("created_at", 1)])
        db.case_memory.create_index([("case_id", 1), ("user_id", 1)], unique=True)

    except Exception as e:
        print(f"[ERROR] MongoDB connection error: {e}")
        raise


def get_db():
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

def get_preferences_collection():
    return db.user_preferences

def get_case_chat_messages_collection():
    return db.case_chat_messages

def get_case_memory_collection():
    return db.case_memory
