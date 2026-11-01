from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
import re


def _validate_password_strength(password: str) -> str:
    if not re.search(r'[A-Z]', password):
        raise ValueError('La contraseña debe contener al menos una letra mayúscula')
    if not re.search(r'[a-z]', password):
        raise ValueError('La contraseña debe contener al menos una letra minúscula')
    if not re.search(r'[0-9]', password):
        raise ValueError('La contraseña debe contener al menos un número')
    if len(password) > 128:
        raise ValueError('La contraseña no puede superar los 128 caracteres')
    return password


class UserRegisterRequest(BaseModel):

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = None
    terms_accepted: bool
    terms_version: str
    privacy_version: str

    @field_validator('terms_accepted')
    @classmethod
    def validate_terms_accepted(cls, value):
        if value is not True:
            raise ValueError('La aceptación de términos y privacidad es obligatoria')
        return value

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password_strength(v)

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "first_name": "Juan",
                "last_name": "García",
                "company_name": "TFM Jurídico"
            }
        })


class UserLoginRequest(BaseModel):

    email: EmailStr
    password: str
    remember_me: bool = False

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        })


class GoogleLoginRequest(BaseModel):

    token: str = Field(..., description="Google ID Token")
    remember_me: bool = False
    terms_accepted: bool = False
    terms_version: Optional[str] = None
    privacy_version: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEifQ..."
            }
        })


class UserResponse(BaseModel):

    id: str
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str]
    role: str
    is_active: bool
    profile_image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "first_name": "Juan",
                "last_name": "García",
                "company_name": "TFM Jurídico",
                "role": "0",
                "is_active": True,
                "profile_image_url": "https://lh3.googleusercontent.com/a/default-user",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        })


class TokenResponse(BaseModel):

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: UserResponse

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "first_name": "Juan",
                    "last_name": "García",
                    "company_name": "TFM Jurídico",
                    "role": "0",
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00",
                    "updated_at": "2024-01-15T10:30:00"
                }
            }
        })


class RefreshTokenRequest(BaseModel):

    refresh_token: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "refresh_token": "solo para compatibilidad; preferir cookie HttpOnly"
            }
        })


class TokenRefreshResponse(BaseModel):

    access_token: str
    token_type: str

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        })


class UserSettingsResponse(BaseModel):

    id: str
    user_id: str
    theme: str
    language: str
    currency: str
    email_notifications: bool
    push_notifications: bool
    allow_analytics: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "theme": "dark",
                "language": "es",
                "currency": "EUR",
                "email_notifications": True,
                "push_notifications": False,
                "allow_analytics": True,
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00"
            }
        })


class UserSettingsUpdateRequest(BaseModel):

    theme: Optional[str] = Field(None, pattern="^(light|dark)$")
    language: Optional[str] = Field(None, pattern="^(es|en|fr|de|pt)$")
    currency: Optional[str] = Field(None, pattern="^(EUR|USD|GBP|JPY|CNY|CHF|CAD|AUD)$")
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    allow_analytics: Optional[bool] = None

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "theme": "dark",
                "language": "es",
                "currency": "EUR",
                "email_notifications": True,
                "push_notifications": False,
                "allow_analytics": True
            }
        })


class UserUpdateRequest(BaseModel):

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    company_name: Optional[str] = None
    profile_image_url: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "first_name": "Juan",
                "last_name": "García",
                "company_name": "TFM Jurídico",
                "profile_image_url": "https://example.com/profile.jpg"
            }
        })


class ChangePasswordRequest(BaseModel):

    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password_strength(v)

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword123"
            }
        })


class ForgotPasswordRequest(BaseModel):

    email: EmailStr

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        })


class ResetPasswordRequest(BaseModel):

    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return _validate_password_strength(v)

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "newpassword123"
            }
        })


class DeleteAccountRequest(BaseModel):

    email: EmailStr

    model_config = ConfigDict(json_schema_extra={
            "example": {
                "email": "user@example.com"
            }
        })
