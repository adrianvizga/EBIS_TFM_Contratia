
import logging
from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.usage_service import get_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("")
async def get_current_usage(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["id"])
    role = str(current_user.get("role", "1"))
    logger.debug("Consultando uso para usuario %s (role=%s)", user_id, role)
    return get_usage(user_id, role)
