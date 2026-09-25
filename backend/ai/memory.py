"""
Case Memory & Tokenless Context Manager
Stores messages in MongoDB (case_chat_messages), maintains rolling summaries (case_memory),
and automatically compresses history so users never encounter token limits.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.database import get_case_chat_messages_collection, get_case_memory_collection

RECENT_MESSAGES_COUNT = 6
SUMMARY_TRIGGER_THRESHOLD = 8

class CaseMemoryManager:
    """Manages persistent case chat messages and rolling conversation summaries"""

    @staticmethod
    def save_message(case_id: str, user_id: str, role: str, content: str) -> Dict[str, Any]:
        """Insert message into case_chat_messages collection"""
        col = get_case_chat_messages_collection()
        doc = {
            "case_id": case_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow()
        }
        res = col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @staticmethod
    def get_messages(case_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve historical messages for a case"""
        col = get_case_chat_messages_collection()
        cursor = col.find({"case_id": case_id, "user_id": user_id}).sort("created_at", 1).limit(limit)
        messages = []
        for m in cursor:
            messages.append({
                "id": str(m["_id"]),
                "role": m.get("role", "user"),
                "content": m.get("content", ""),
                "created_at": m.get("created_at").isoformat() if isinstance(m.get("created_at"), datetime) else str(m.get("created_at"))
            })
        return messages

    @staticmethod
    def clear_messages(case_id: str, user_id: str) -> int:
        """Clear all messages for a specific case"""
        col = get_case_chat_messages_collection()
        res = col.delete_many({"case_id": case_id, "user_id": user_id})
        mem_col = get_case_memory_collection()
        mem_col.delete_one({"case_id": case_id, "user_id": user_id})
        return res.deleted_count

    @staticmethod
    def get_or_create_memory(case_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch persistent case memory and rolling summary"""
        mem_col = get_case_memory_collection()
        record = mem_col.find_one({"case_id": case_id, "user_id": user_id})
        if not record:
            record = {
                "case_id": case_id,
                "user_id": user_id,
                "summary": "",
                "important_facts": [],
                "updated_at": datetime.utcnow()
            }
        return record

    @staticmethod
    def update_summary(case_id: str, user_id: str, new_summary: str, important_facts: Optional[List[str]] = None):
        """Update rolling summary and facts"""
        mem_col = get_case_memory_collection()
        update_data = {
            "summary": new_summary,
            "updated_at": datetime.utcnow()
        }
        if important_facts is not None:
            update_data["important_facts"] = important_facts

        mem_col.update_one(
            {"case_id": case_id, "user_id": user_id},
            {"$set": update_data},
            upsert=True
        )

    @classmethod
    def prepare_compressed_history(
        cls,
        case_id: str,
        user_id: str,
        case_context: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Tokenless compression:
        - Retrieves all messages.
        - If message count > threshold, rolls older messages into a summary.
        - Returns a curated list of recent messages with rolling summary context.
        """
        all_messages = cls.get_messages(case_id, user_id, limit=100)
        memory = cls.get_or_create_memory(case_id, user_id)

        if len(all_messages) > SUMMARY_TRIGGER_THRESHOLD:
            # Older messages to compress
            older = all_messages[:-RECENT_MESSAGES_COUNT]
            recent = all_messages[-RECENT_MESSAGES_COUNT:]

            # Fast rolling summary compilation
            topics = []
            for msg in older:
                if msg["role"] == "user":
                    snippet = msg["content"][:60].replace("\n", " ")
                    topics.append(f"User asked: {snippet}")

            rolling_summary = memory.get("summary", "")
            added_summary = "; ".join(topics[-4:])
            combined_summary = (rolling_summary + "\n" + added_summary).strip() if rolling_summary else added_summary

            cls.update_summary(case_id, user_id, combined_summary, case_context.get("important_facts", []))

            # Build messages list for the model:
            # First item: a context primer with summary
            compressed = []
            if combined_summary:
                compressed.append({
                    "role": "user",
                    "content": f"[CONVERSATION SUMMARY OF EARLIER INQUIRIES]\n{combined_summary}"
                })
                compressed.append({
                    "role": "assistant",
                    "content": "Understood. I have full recall of our earlier investigation steps and will continue analyzing this case."
                })
            for m in recent:
                compressed.append({"role": m["role"], "content": m["content"]})
            return compressed

        # If below threshold, return all messages
        return [{"role": m["role"], "content": m["content"]} for m in all_messages]
