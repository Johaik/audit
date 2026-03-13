from datetime import datetime
from typing import Optional
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def parse_cursor(cursor: Optional[str]) -> Optional[datetime]:
    if not cursor:
        return None

    try:
        cursor_cleaned = cursor.replace(" ", "+")
        if cursor_cleaned.endswith("Z"):
            cursor_cleaned = cursor_cleaned.replace("Z", "+00:00")

        return datetime.fromisoformat(cursor_cleaned)
    except ValueError as e:
        logger.warning(f"Cursor parse error: {e}, cursor: {cursor}")
        raise HTTPException(status_code=400, detail="Invalid cursor format")
