from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
import logging
from core.database import execute_query, execute_update
from core.security import get_current_user
from services.notifications import create_notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)

class NotificationResponse(BaseModel):

    id: str
    user_id: str
    title: str
    message: str
    notification_type: str
    is_read: bool
    related_entity_type: Optional[str]
    related_entity_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Contrato actualizado",
                "message": "Tu contrato 'Acuerdo de Servicios' ha sido actualizado",
                "notification_type": "info",
                "is_read": False,
                "related_entity_type": "contract",
                "related_entity_id": "550e8400-e29b-41d4-a716-446655440002",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        })


class CreateNotificationRequest(BaseModel):

    title: str
    message: str
    notification_type: str = "info"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "title": "Contrato actualizado",
                "message": "Tu contrato 'Acuerdo de Servicios' ha sido actualizado",
                "notification_type": "info",
                "related_entity_type": "contract",
                "related_entity_id": "550e8400-e29b-41d4-a716-446655440002"
            }
        })


@router.post("")
async def create_notification_endpoint(
    notification: CreateNotificationRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["id"])
    logger.debug(f"Creating notification for user {user_id}")
    
    success = create_notification(
        user_id=user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        related_entity_type=notification.related_entity_type,
        related_entity_id=notification.related_entity_id
    )
    
    if success:
        logger.debug("Notification created successfully")
        return {"message": "Notification created successfully"}
    else:
        logger.warning("Failed to create notification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating notification"
        )


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    skip: int = 0
):
    user_id = str(current_user["id"])
    logger.debug("get_notifications: user_id=%s, limit=%d, skip=%d", user_id, limit, skip)
    
    try:
        notifications = execute_query(
            """
            SELECT id, user_id, title, message, notification_type, is_read,
                   related_entity_type, related_entity_id, created_at, updated_at
            FROM notifications
            WHERE user_id = %(user_id)s
            ORDER BY
              floor(extract(epoch from created_at) / 120) DESC,
              CASE title
                WHEN 'Análisis completado'  THEN 1
                WHEN 'Contrato generado'    THEN 1
                WHEN 'Contrato no soportado' THEN 1
                WHEN 'Error en el análisis' THEN 1
                WHEN 'Error en la generación' THEN 1
                WHEN 'Análisis iniciado'    THEN 2
                WHEN 'Generación iniciada'  THEN 2
                WHEN 'Archivo subido'       THEN 3
                WHEN 'File uploaded'        THEN 3
                ELSE 2
              END ASC,
              created_at DESC
            LIMIT %(limit)s OFFSET %(skip)s
            """,
            {"user_id": user_id, "limit": limit, "skip": skip}
        )
        
        return [
            NotificationResponse(
                id=str(notif["id"]),
                user_id=str(notif["user_id"]),
                title=notif["title"],
                message=notif["message"],
                notification_type=notif["notification_type"],
                is_read=notif["is_read"],
                related_entity_type=notif.get("related_entity_type"),
                related_entity_id=notif.get("related_entity_id"),
                created_at=notif["created_at"],
                updated_at=notif["updated_at"]
            )
            for notif in notifications
        ]
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching notifications"
        )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["id"])
    logger.debug("get_unread_count: user_id=%s", user_id)
    
    try:
        result = execute_query(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id = %(user_id)s AND is_read = false",
            {"user_id": user_id}
        )
        
        count = result[0]["count"] if result else 0
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error fetching unread count: {e}")
        return {"unread_count": 0}


@router.put("/mark-all-read")
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["id"])
    
    try:
        execute_update(
            "UPDATE notifications SET is_read = true WHERE user_id = %(user_id)s AND is_read = false",
            {"user_id": user_id}
        )
        
        logger.debug(f"All notifications for user {user_id} marked as read")
        return {"message": "All notifications marked as read"}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marking all notifications as read"
        )


@router.delete("/delete-all")
async def delete_all_notifications(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["id"])
    
    try:
        execute_update(
            "DELETE FROM notifications WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        
        logger.debug(f"All notifications for user {user_id} deleted")
        return {"message": "All notifications deleted"}
    except Exception as e:
        logger.error(f"Error deleting all notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting all notifications"
        )


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["id"])
    
    try:
        notif = execute_query(
            "SELECT id FROM notifications WHERE id = %(id)s AND user_id = %(user_id)s",
            {"id": notification_id, "user_id": user_id}
        )
        
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        execute_update(
            "UPDATE notifications SET is_read = true WHERE id = %(id)s",
            {"id": notification_id}
        )
        
        logger.debug(f"Notification {notification_id} marked as read")
        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error marking notification as read"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["id"])
    
    try:
        notif = execute_query(
            "SELECT id FROM notifications WHERE id = %(id)s AND user_id = %(user_id)s",
            {"id": notification_id, "user_id": user_id}
        )
        
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        execute_update(
            "DELETE FROM notifications WHERE id = %(id)s",
            {"id": notification_id}
        )
        
        logger.debug(f"Notification {notification_id} deleted")
        return {"message": "Notification deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting notification"
        )
