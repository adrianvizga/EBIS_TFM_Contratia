
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response, Cookie
from models.models import UserRegisterRequest, UserLoginRequest, GoogleLoginRequest, UserResponse, TokenResponse, RefreshTokenRequest, TokenRefreshResponse, UserUpdateRequest, ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest, DeleteAccountRequest
from core.database import execute_query, execute_insert, execute_update, execute_transaction, execute_delete
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, get_current_user, create_reset_token
from services.email.email_service import send_password_reset_email
from datetime import timedelta, datetime, timezone
from google.oauth2 import id_token
from google.auth.transport import requests
from core.config import settings
from core.rate_limiter import limiter
from typing import Optional
from services.notifications import create_notification
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
TERMS_VERSION = "terms-2026-06-20"
PRIVACY_VERSION = "privacy-2026-06-20"

REFRESH_COOKIE_NAME = "contratia_refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"
REMEMBER_ME_EXPIRE_DAYS = 30


def _cookie_secure() -> bool:
    return os.getenv("REFRESH_COOKIE_SECURE", "true").strip().lower() not in {
        "false",
        "0",
        "no",
        "off",
    }


def _refresh_expires_delta(remember_me: bool) -> timedelta:
    days = REMEMBER_ME_EXPIRE_DAYS if remember_me else settings.refresh_token_expire_days
    return timedelta(days=days)


def _refresh_cookie_max_age(remember_me: bool) -> Optional[int]:
    if not remember_me:
        return None
    return int(_refresh_expires_delta(True).total_seconds())


def _set_refresh_cookie(response: Response, refresh_token: str, remember_me: bool) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=_refresh_cookie_max_age(remember_me),
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=_cookie_secure(),
        samesite="lax",
        httponly=True,
    )


def _store_session(request: Request, user_id: str, refresh_token: str, remember_me: bool) -> None:
    expires_delta = _refresh_expires_delta(remember_me)
    execute_insert(
        """INSERT INTO sessions (user_id, token, expires_at, ip_address, user_agent)
           VALUES (%(user_id)s, %(token)s, %(expires_at)s, %(ip)s, %(ua)s)
           RETURNING id""",
        {
            "user_id": user_id,
            "token": refresh_token,
            "expires_at": datetime.now(timezone.utc) + expires_delta,
            "ip": request.client.host if request.client else "unknown",
            "ua": (request.headers.get("user-agent", ""))[:500],
        },
    )


def _is_remembered_refresh(payload: dict) -> bool:
    exp = payload.get("exp")
    if not exp:
        return False
    remaining_seconds = exp - datetime.now(timezone.utc).timestamp()
    regular_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
    return remaining_seconds > regular_seconds


@router.post("/register", response_model=TokenResponse, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, response: Response, user_data: UserRegisterRequest):
    
    if user_data.terms_version != TERMS_VERSION or user_data.privacy_version != PRIVACY_VERSION:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Legal document version is not current")

    existing_user = execute_query(
        "SELECT id FROM users WHERE email = %(email)s",
        {"email": user_data.email}
    )
    
    if existing_user:
        logger.warning("Registro fallido: email ya registrado email=%s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    hashed_password = hash_password(user_data.password)
    
    query = """
        WITH new_user AS (
            INSERT INTO users
            (email, password_hash, first_name, last_name, company_name, role, is_active)
            VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(company_name)s, '1', true)
            RETURNING id, email, first_name, last_name, company_name, role, is_active, profile_image_url, created_at, updated_at
        ), consent AS (
            INSERT INTO legal_acceptances (user_id, terms_version, privacy_version, accepted_at)
            SELECT id, %(terms_version)s, %(privacy_version)s, CURRENT_TIMESTAMP FROM new_user
        )
        SELECT * FROM new_user
    """
    
    user = execute_insert(
        query,
        {
            "email": user_data.email,
            "password_hash": hashed_password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "company_name": user_data.company_name,
            "terms_version": user_data.terms_version,
            "privacy_version": user_data.privacy_version
        }
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )
    
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user["id"]), "email": user["email"]},
        expires_delta=_refresh_expires_delta(False),
    )
    
    user_response = UserResponse(
        id=str(user["id"]),
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        company_name=user["company_name"],
        role=user["role"],
        is_active=user["is_active"],
        profile_image_url=user.get("profile_image_url"),
        created_at=user["created_at"],
        updated_at=user["updated_at"]
    )
    
    user_id = str(user["id"])

    try:
        _store_session(request, user_id, refresh_token, remember_me=False)
        _set_refresh_cookie(response, refresh_token, remember_me=False)
    except Exception as _e:
        logger.warning("No se pudo almacenar la sesión tras el registro: %s", _e)

    create_notification(
        user_id=user_id,
        title="¡Bienvenido a ContratIA!",
        message="Tu cuenta ha sido creada exitosamente. Comienza a analizar contratos ahora.",
        notification_type="success"
    )
    logger.info("Registro exitoso: user_id=%s, email=%s", user_id, user_data.email)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
@limiter.limit("5/minute")
async def login(request: Request, response: Response, credentials: UserLoginRequest):
    
    users = execute_query(
        "SELECT * FROM users WHERE email = %(email)s",
        {"email": credentials.email}
    )
    
    if not users:
        logger.warning("Login fallido: email no encontrado email=%s", credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user = users[0]
    
    if not verify_password(credentials.password, user["password_hash"]):
        logger.warning("Login fallido: password incorrecto email=%s", credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user["is_active"]:
        logger.warning("Login fallido: cuenta inactiva email=%s", credentials.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user["id"]), "email": user["email"]},
        expires_delta=_refresh_expires_delta(credentials.remember_me),
    )
    
    user_response = UserResponse(
        id=str(user["id"]),
        email=user["email"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        company_name=user["company_name"],
        role=user["role"],
        is_active=user["is_active"],
        profile_image_url=user.get("profile_image_url"),
        created_at=user["created_at"],
        updated_at=user["updated_at"]
    )
    
    try:
        _store_session(request, str(user["id"]), refresh_token, remember_me=credentials.remember_me)
        _set_refresh_cookie(response, refresh_token, remember_me=credentials.remember_me)
    except Exception as _e:
        logger.warning("No se pudo almacenar la sesión tras el login: %s", _e)

    logger.info("Login exitoso: user_id=%s, email=%s", str(user["id"]), credentials.email)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    response: Response,
    body: Optional[RefreshTokenRequest] = None,
    refresh_cookie: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
):
    
    refresh_token = refresh_cookie or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token"
        )

    payload = decode_token(refresh_token)
    
    if not payload:
        logger.warning("Refresh token invalido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # La sesión confirma que el token sigue vigente y no se ha revocado.
    sessions = execute_query(
        "SELECT id FROM sessions WHERE token = %(token)s AND expires_at > NOW()",
        {"token": refresh_token}
    )
    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    user_id = payload.get("sub")
    email = payload.get("email")
    remember_me = _is_remembered_refresh(payload)
    
    access_token = create_access_token(
        data={"sub": user_id, "email": email}
    )

    new_refresh_token = create_refresh_token(
        data={"sub": user_id, "email": email},
        expires_delta=_refresh_expires_delta(remember_me),
    )
    execute_delete(
        "DELETE FROM sessions WHERE token = %(token)s",
        {"token": refresh_token}
    )
    _store_session(request, user_id, new_refresh_token, remember_me=remember_me)
    _set_refresh_cookie(response, new_refresh_token, remember_me=remember_me)
    
    logger.debug("Token refrescado para user_id=%s", user_id)
    
    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user["id"]),
        email=current_user["email"],
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        company_name=current_user["company_name"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        profile_image_url=current_user.get("profile_image_url"),
        created_at=current_user["created_at"],
        updated_at=current_user["updated_at"]
    )


@router.put("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        update_fields = []
        user_id = str(current_user['id'])
        params = {"user_id": user_id}
        logger.info("Actualizacion de perfil: user_id=%s", user_id)
        
        if user_update.first_name is not None:
            update_fields.append("first_name = %(first_name)s")
            params["first_name"] = user_update.first_name
        
        if user_update.last_name is not None:
            update_fields.append("last_name = %(last_name)s")
            params["last_name"] = user_update.last_name
        
        if user_update.company_name is not None:
            update_fields.append("company_name = %(company_name)s")
            params["company_name"] = user_update.company_name
        
        if user_update.profile_image_url is not None:
            update_fields.append("profile_image_url = %(profile_image_url)s")
            params["profile_image_url"] = user_update.profile_image_url if user_update.profile_image_url else None
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # El perfil y su notificación deben guardarse juntos.
        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %(user_id)s
            RETURNING id, email, first_name, last_name, company_name, 
                      role, is_active, profile_image_url, created_at, updated_at
        """
        
        notification_query = """
            INSERT INTO notifications (user_id, title, message, notification_type)
            VALUES (%(user_id)s, %(title)s, %(message)s, %(notification_type)s)
        """
        
        notification_params = {
            "user_id": user_id,
            "title": "Información actualizada",
            "message": "Tu información personal ha sido actualizada exitosamente.",
            "notification_type": "success"
        }
        
        results = execute_transaction([
            (query, params),
            (notification_query, notification_params)
        ])
        
        updated_user = results[0]
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=str(updated_user['id']),
            email=updated_user['email'],
            first_name=updated_user['first_name'],
            last_name=updated_user['last_name'],
            company_name=updated_user['company_name'],
            role=updated_user['role'],
            is_active=updated_user['is_active'],
            profile_image_url=updated_user.get('profile_image_url'),
            created_at=updated_user['created_at'],
            updated_at=updated_user['updated_at']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error actualizando perfil user_id=%s: %s", str(current_user.get('id')), e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user"
        )


@router.post("/google-login", response_model=TokenResponse, response_model_exclude_none=True)
@limiter.limit("5/minute")
async def google_login(request: Request, response: Response, body: GoogleLoginRequest):
    
    try:
        if not settings.google_client_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google login is not configured. Set GOOGLE_CLIENT_ID in environment."
            )
        
        # La librería valida la firma del token de Google.
        try:
            idinfo = id_token.verify_oauth2_token(
                body.token,
                requests.Request(),
                settings.google_client_id,
                clock_skew_in_seconds=30
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            decoded_token = idinfo
            logger.info("Google token verified successfully")
            
        except ValueError as e:
            logger.warning(f"Google token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google token"
            )
        
        email = decoded_token.get('email')
        first_name = decoded_token.get('given_name', '').strip() or 'Usuario de Google'
        last_name = decoded_token.get('family_name', '').strip() or ''
        profile_image_url = decoded_token.get('picture', '').strip() or None
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Google token"
            )
        
        client_ip = request.client.host if request.client else "unknown"
        client_ua = (request.headers.get("user-agent", ""))[:500]
        
        existing_users = execute_query(
            "SELECT id, email, password_hash, first_name, last_name, company_name, role, is_active, profile_image_url, created_at, updated_at FROM users WHERE email = %(email)s",
            {"email": email}
        )
        
        if existing_users:
            existing_user = existing_users[0]
            
            if profile_image_url and existing_user.get('profile_image_url') != profile_image_url:
                try:
                    execute_update(
                        "UPDATE users SET profile_image_url = %(profile_image_url)s WHERE id = %(user_id)s",
                        {"user_id": existing_user['id'], "profile_image_url": profile_image_url}
                    )
                    existing_user['profile_image_url'] = profile_image_url
                except Exception as update_error:
                    logger.warning(f"Failed to update profile image: {update_error}")
            
            user_id = str(existing_user['id'])
            access_token = create_access_token(
                data={"sub": user_id}
            )
            refresh_token = create_refresh_token(
                data={"sub": user_id},
                expires_delta=_refresh_expires_delta(body.remember_me)
            )
            
            try:
                _store_session(request, user_id, refresh_token, remember_me=body.remember_me)
                _set_refresh_cookie(response, refresh_token, remember_me=body.remember_me)
            except Exception as session_error:
                logger.warning(f"Failed to store session token: {session_error}")
            
            response = TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=UserResponse(
                    id=user_id,
                    email=existing_user['email'],
                    first_name=existing_user['first_name'],
                    last_name=existing_user['last_name'],
                    company_name=existing_user.get('company_name'),
                    role=existing_user['role'],
                    is_active=existing_user['is_active'],
                    profile_image_url=existing_user.get('profile_image_url'),
                    created_at=existing_user['created_at'],
                    updated_at=existing_user['updated_at']
                )
            )
            create_notification(
                user_id=user_id,
                title="Inicio de sesi\u00f3n exitoso",
                message="Has iniciado sesi\u00f3n en ContratIA con tu cuenta de Google.",
                notification_type="success"
            )
            return response
        
        if not body.terms_accepted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found. Please sign up to create an account.")
        if body.terms_version != TERMS_VERSION or body.privacy_version != PRIVACY_VERSION:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Explicit acceptance of current legal documents is required")
        query = """
            WITH new_user AS (
                INSERT INTO users
                (email, password_hash, first_name, last_name, role, is_active, profile_image_url)
                VALUES (%(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(role)s, true, %(profile_image_url)s)
                RETURNING id, email, first_name, last_name, company_name, role, is_active, profile_image_url, created_at, updated_at
            ), consent AS (
                INSERT INTO legal_acceptances (user_id, terms_version, privacy_version, accepted_at)
                SELECT id, %(terms_version)s, %(privacy_version)s, CURRENT_TIMESTAMP FROM new_user
            )
            SELECT * FROM new_user
        """
        
        import secrets as _secrets
        new_user = execute_insert(
            query,
            {
                "email": email,
                "password_hash": hash_password(_secrets.token_urlsafe(32)),
                "first_name": first_name,
                "last_name": last_name,
                "role": '1',
                "profile_image_url": profile_image_url
                ,"terms_version": body.terms_version
                ,"privacy_version": body.privacy_version
            }
        )
        
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        user_id = str(new_user['id'])
        access_token = create_access_token(
            data={"sub": user_id}
        )
        refresh_token = create_refresh_token(
            data={"sub": user_id},
            expires_delta=_refresh_expires_delta(body.remember_me)
        )
        
        try:
            _store_session(request, user_id, refresh_token, remember_me=body.remember_me)
            _set_refresh_cookie(response, refresh_token, remember_me=body.remember_me)
        except Exception as session_error:
            logger.warning(f"Failed to store session token for new user: {session_error}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user_id,
                email=new_user['email'],
                first_name=new_user['first_name'],
                last_name=new_user['last_name'],
                company_name=new_user.get('company_name'),
                role=new_user['role'],
                is_active=new_user['is_active'],
                profile_image_url=new_user.get('profile_image_url'),
                created_at=new_user['created_at'],
                updated_at=new_user['updated_at']
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in Google login"
        )


@router.put("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    
    try:
        user_id = current_user['id']
        logger.info("Cambio de password: user_id=%s", user_id)
        
        users = execute_query(
            "SELECT password_hash FROM users WHERE id = %(id)s",
            {"id": user_id}
        )
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = users[0]
        
        if not verify_password(password_data.current_password, user['password_hash']):
            logger.warning("Cambio de password fallido: password actual incorrecto user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        new_password_hash = hash_password(password_data.new_password)
        
        execute_update(
            "UPDATE users SET password_hash = %(password_hash)s, updated_at = NOW() WHERE id = %(id)s",
            {
                "password_hash": new_password_hash,
                "id": user_id
            }
        )
        
        # El cambio de contraseña cierra las sesiones de todos los dispositivos.
        execute_delete(
            "DELETE FROM sessions WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        
        create_notification(
            user_id=str(user_id),
            title="Contraseña cambiada",
            message="Tu contraseña ha sido cambiada exitosamente.",
            notification_type="success"
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cambiando password user_id=%s: %s", current_user.get('id'), e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password"
        )


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    
    try:
        users = execute_query(
            "SELECT id, email, first_name FROM users WHERE email = %(email)s",
            {"email": body.email}
        )
        
        # La respuesta no revela si el correo está registrado.
        generic_message = "Si el correo está registrado, recibirás un enlace de restablecimiento"
        
        if not users:
            logger.debug("Forgot-password: email no encontrado email=%s", body.email)
            return {"message": generic_message}
        
        user = users[0]
        
        reset_token = create_reset_token(str(user['id']), user['email'])
        
        email_sent = await send_password_reset_email(
            user['email'],
            user['first_name'],
            reset_token
        )
        
        if not email_sent:
            logger.warning("Email de reset no enviado (SMTP no configurado) para email=%s", body.email)
        else:
            logger.info("Email de reset enviado a email=%s", body.email)
        
        return {"message": generic_message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing password reset request"
        )


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    
    try:
        payload = decode_token(body.token)
        
        if not payload:
            logger.warning("Reset-password: token invalido o expirado")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        if payload.get("type") != "reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token data"
            )
        
        users = execute_query(
            "SELECT id FROM users WHERE id = %(id)s AND email = %(email)s",
            {"id": user_id, "email": email}
        )
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        new_password_hash = hash_password(body.new_password)
        
        execute_update(
            "UPDATE users SET password_hash = %(password_hash)s, updated_at = NOW() WHERE id = %(id)s",
            {
                "password_hash": new_password_hash,
                "id": user_id
            }
        )
        
        # Restablecer la contraseña invalida el resto de sesiones.
        execute_delete(
            "DELETE FROM sessions WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        
        create_notification(
            user_id=user_id,
            title="Contraseña restablecida",
            message="Tu contraseña ha sido restablecida exitosamente. Ahora puedes iniciar sesión con la nueva contraseña.",
            notification_type="success"
        )
        
        logger.info("Password restablecido exitosamente: user_id=%s", user_id)
        
        return {"message": "Password has been reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )


@router.delete("/delete-account")
async def delete_account(
    body: DeleteAccountRequest,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    
    try:
        user_id = current_user['id']
        user_email = current_user['email']
        
        if body.email.lower() != user_email.lower():
            logger.warning("Delete-account: email no coincide user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico no coincide con la cuenta actual"
            )
        
        try:
            contracts = execute_query(
                "SELECT file_path FROM contracts WHERE user_id = %(user_id)s",
                {"user_id": user_id}
            )
            for contract in contracts:
                file_path = contract.get('file_path')
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error cleaning up contract files: {e}")
        
        execute_delete(
            "DELETE FROM sessions WHERE user_id = %(user_id)s",
            {"user_id": user_id}
        )
        _clear_refresh_cookie(response)
        
        # Las relaciones de la cuenta se eliminan en cascada.
        execute_delete(
            "DELETE FROM users WHERE id = %(id)s",
            {"id": user_id}
        )
        
        logger.info("Cuenta eliminada: user_id=%s, email=%s", user_id, user_email)
        
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting account"
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    refresh_cookie: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
):
    try:
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            payload = decode_token(auth_header.split(" ", 1)[1])
            if payload and payload.get("type") == "access":
                user_id = payload.get("sub")

        if refresh_cookie:
            execute_delete(
                "DELETE FROM sessions WHERE token = %(token)s",
                {"token": refresh_cookie}
            )
        elif user_id:
            execute_delete(
                "DELETE FROM sessions WHERE user_id = %(user_id)s",
                {"user_id": user_id}
            )
        _clear_refresh_cookie(response)
        logger.info("Logout: user_id=%s", user_id)
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )
