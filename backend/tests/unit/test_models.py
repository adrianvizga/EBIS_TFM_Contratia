import pytest
from pydantic import ValidationError
from models.models import (
    UserRegisterRequest,
    UserLoginRequest,
    ChangePasswordRequest,
    UserSettingsUpdateRequest,
    DeleteAccountRequest,
)

pytestmark = pytest.mark.unit


class TestPasswordValidation:

    def test_valid_password_accepted(self):
        req = ChangePasswordRequest(current_password="old", new_password="Test1234")
        assert req.new_password == "Test1234"

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password="Te1")

    def test_password_too_long(self):
        long_pw = "A1a" + "x" * 126  # 129 chars
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password=long_pw)

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password="test1234")

    def test_password_no_lowercase(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password="TEST1234")

    def test_password_no_digit(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="old", new_password="Testtest")


class TestRegistrationValidation:

    def test_register_valid_data(self):
        req = UserRegisterRequest(
            email="user@example.com",
            password="Test1234",
            first_name="Juan",
            last_name="García",
            terms_accepted=True,
            terms_version="terms-2026-06-20",
            privacy_version="privacy-2026-06-20",
        )
        assert req.email == "user@example.com"
        assert req.first_name == "Juan"

    def test_register_invalid_email(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="not-an-email",
                password="Test1234",
                first_name="Juan",
                last_name="García",
            )

    def test_register_empty_first_name(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="user@example.com",
                password="Test1234",
                first_name="",
                last_name="García",
            )


class TestSettingsValidation:

    def test_settings_valid_theme(self):
        for theme in ("dark", "light"):
            req = UserSettingsUpdateRequest(theme=theme)
            assert req.theme == theme

    def test_settings_invalid_theme(self):
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(theme="blue")

    def test_settings_valid_language(self):
        for lang in ("es", "en", "fr", "de", "pt"):
            req = UserSettingsUpdateRequest(language=lang)
            assert req.language == lang

    def test_settings_invalid_language(self):
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(language="xx")

    def test_settings_valid_currency(self):
        for cur in ("EUR", "USD", "GBP"):
            req = UserSettingsUpdateRequest(currency=cur)
            assert req.currency == cur

    def test_settings_invalid_currency(self):
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(currency="BTC")


class TestDeleteAccountRequest:

    def test_delete_account_requires_email(self):
        with pytest.raises(ValidationError):
            DeleteAccountRequest()

    def test_delete_account_valid_email(self):
        req = DeleteAccountRequest(email="test@example.com")
        assert req.email == "test@example.com"

    def test_delete_account_invalid_email(self):
        with pytest.raises(ValidationError):
            DeleteAccountRequest(email="not-an-email")
