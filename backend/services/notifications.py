
from typing import Optional
import logging
from core.database import execute_insert_returning

logger = logging.getLogger(__name__)

def create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None
) -> bool:
    try:
        result = execute_insert_returning(
            """
            INSERT INTO notifications (user_id, title, message, notification_type, related_entity_type, related_entity_id)
            VALUES (%(user_id)s, %(title)s, %(message)s, %(notification_type)s, %(related_entity_type)s, %(related_entity_id)s)
            RETURNING id::text
            """,
            {
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id
            }
        )
        logger.debug(f"Created notification for user {user_id}: {title}")
        return True
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return False
