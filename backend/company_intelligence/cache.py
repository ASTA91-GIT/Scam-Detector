"""
MongoDB Cache Layer for Company & Domain Intelligence
Caches RDAP, DNS, website checks, and company profile data in the
'domain_intelligence' collection with a 24-hour TTL.
Prevents redundant external queries while never caching fabricated data.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from backend.database import get_database

logger = logging.getLogger("scamguard.company_intelligence.cache")

CACHE_COLLECTION = "domain_intelligence"
CACHE_TTL_HOURS = 24


def get_cache_collection():
    """Returns the MongoDB collection for domain intelligence cache."""
    try:
        db = get_database()
        col = db[CACHE_COLLECTION]
        # Ensure index on domain and expires_at if possible
        try:
            col.create_index("domain", background=True)
            col.create_index("expires_at", expireAfterSeconds=0, background=True)
        except Exception:
            pass
        return col
    except Exception as e:
        logger.warning(f"Could not connect to cache collection: {e}")
        return None


def get_cached_intelligence(domain: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves fresh cached intelligence for a domain.
    Returns None if cache is missing, expired, or unavailable.
    """
    if not domain:
        return None

    clean_dom = domain.lower().strip()
    try:
        col = get_cache_collection()
        if col is None:
            return None

        record = col.find_one({"domain": clean_dom})
        if not record:
            return None

        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = record.get("expires_at")
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                logger.info(f"Cache expired for domain: {clean_dom}")
                return None

        logger.info(f"Cache hit for domain: {clean_dom}")
        # Strip mongo internal _id
        record.pop("_id", None)
        return record

    except Exception as e:
        logger.warning(f"Cache retrieval error for {clean_dom}: {e}")
        return None


def save_cached_intelligence(domain: str,
                             company_name: Optional[str],
                             rdap_data: Dict[str, Any],
                             website_data: Dict[str, Any],
                             dns_data: Dict[str, Any],
                             email_data: Optional[Dict[str, Any]] = None,
                             sources: Optional[list] = None) -> bool:
    """
    Stores verified domain & company intelligence in MongoDB with a 24-hour expiration.
    Only caches actual query outputs, never fabricated data.
    """
    if not domain:
        return False

    clean_dom = domain.lower().strip()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)

    cache_doc = {
        "domain": clean_dom,
        "company_name": company_name,
        "rdap_data": rdap_data,
        "website_data": website_data,
        "dns_data": dns_data,
        "email_data": email_data or {},
        "sources": sources or [],
        "retrieved_at": now.isoformat(),
        "expires_at": expires_at
    }

    try:
        col = get_cache_collection()
        if col is None:
            return False

        col.update_one(
            {"domain": clean_dom},
            {"$set": cache_doc},
            upsert=True
        )
        logger.info(f"Cached fresh intelligence for domain: {clean_dom} (expires in {CACHE_TTL_HOURS}h)")
        return True
    except Exception as e:
        logger.warning(f"Failed to cache intelligence for {clean_dom}: {e}")
        return False
