
from fastapi import APIRouter, Depends, HTTPException, status
import logging
from core.database import execute_query, execute_insert
from core.security import get_current_user
from models.models import UserSettingsResponse, UserSettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger(__name__)

ALLOWED_SETTINGS_FIELDS = {
    'theme', 'language', 'currency',
    'email_notifications', 'push_notifications', 'allow_analytics',
}


@router.get("", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = str(current_user['id'])
        logger.debug("get_user_settings: user_id=%s", user_id)
        settings = execute_query("""
            SELECT id, user_id, theme, language, currency,
                   email_notifications, push_notifications,
                   allow_analytics,
                   created_at, updated_at
            FROM user_settings
            WHERE user_id = %(user_id)s
        """, {"user_id": user_id})

        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )

        row = settings[0]
        return UserSettingsResponse(
            id=str(row['id']),
            user_id=str(row['user_id']),
            theme=row['theme'],
            language=row['language'],
            currency=row['currency'],
            email_notifications=row['email_notifications'],
            push_notifications=row['push_notifications'],
            allow_analytics=row['allow_analytics'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user settings"
        )


@router.put("", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        update_fields = []
        user_id = str(current_user['id'])
        params = {"user_id": user_id}
        logger.info("update_user_settings: user_id=%s", user_id)

        # Solo se incluyen campos permitidos para no interpolar nombres arbitrarios.
        field_mapping = {
            'theme': settings_update.theme,
            'language': settings_update.language,
            'currency': settings_update.currency,
            'email_notifications': settings_update.email_notifications,
            'push_notifications': settings_update.push_notifications,
            'allow_analytics': settings_update.allow_analytics,
        }

        for field_name, field_value in field_mapping.items():
            if field_value is not None:
                if field_name not in ALLOWED_SETTINGS_FIELDS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Field '{field_name}' is not allowed"
                    )
                update_fields.append(f"{field_name} = %({field_name})s")
                params[field_name] = field_value

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        query = f"""
            UPDATE user_settings
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %(user_id)s
            RETURNING id, user_id, theme, language, currency,
                      email_notifications, push_notifications,
                      allow_analytics,
                      created_at, updated_at
        """

        updated_settings = execute_insert(query, params)

        if not updated_settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )

        return UserSettingsResponse(
            id=str(updated_settings['id']),
            user_id=str(updated_settings['user_id']),
            theme=updated_settings['theme'],
            language=updated_settings['language'],
            currency=updated_settings['currency'],
            email_notifications=updated_settings['email_notifications'],
            push_notifications=updated_settings['push_notifications'],
            allow_analytics=updated_settings['allow_analytics'],
            created_at=updated_settings['created_at'],
            updated_at=updated_settings['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user settings"
        )
