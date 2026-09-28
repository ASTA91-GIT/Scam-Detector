"""
Automatic File Lifecycle & Cleanup Service
Periodically scans upload and temporary directories, pruning files that exceed
the configured FILE_RETENTION_HOURS policy.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger("scamguard.cleanup")


def get_retention_seconds() -> int:
    """Gets file retention period in seconds from environment, default 24 hours."""
    hours = int(os.getenv("FILE_RETENTION_HOURS", "24"))
    return max(1, hours) * 3600


def cleanup_expired_files(directories: List[str] = None, retention_seconds: int = None) -> Dict[str, Any]:
    """
    Cleans up files exceeding retention limits from specified directories.
    Logs each deletion and failure.
    """
    if retention_seconds is None:
        retention_seconds = get_retention_seconds()

    if directories is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        directories = [
            os.path.join(base_dir, "uploads"),
            os.path.join(base_dir, "temporary"),
            os.path.join(base_dir, "processing"),
        ]

    cutoff_time = time.time() - retention_seconds
    deleted_count = 0
    failed_count = 0
    bytes_freed = 0
    errors = []

    for directory in directories:
        if not os.path.exists(directory):
            continue

        try:
            for root, _, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        stat = os.stat(file_path)
                        # Check mtime against cutoff
                        if stat.st_mtime < cutoff_time:
                            size = stat.st_size
                            os.remove(file_path)
                            deleted_count += 1
                            bytes_freed += size
                            logger.info(f"Cleaned expired temporary file: {filename} ({size} bytes)")
                    except Exception as fe:
                        failed_count += 1
                        err_msg = f"Failed to delete {file_path}: {fe}"
                        logger.error(err_msg)
                        errors.append(err_msg)
        except Exception as de:
            logger.error(f"Error accessing cleanup directory {directory}: {de}")
            errors.append(str(de))

    return {
        "status": "success" if failed_count == 0 else "completed_with_errors",
        "deleted_count": deleted_count,
        "failed_count": failed_count,
        "bytes_freed": bytes_freed,
        "retention_hours": retention_seconds // 3600,
        "errors": errors,
        "executed_at": datetime.utcnow().isoformat()
    }
