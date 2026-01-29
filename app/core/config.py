from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")

    # JWT Configuration
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(alias="ALGORITHM")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # First Admin User
    first_admin_email: str = Field(alias="FIRST_ADMIN_EMAIL")
    first_admin_password: str = Field(alias="FIRST_ADMIN_PASSWORD")

    # Password Reset
    password_reset_token_expire_minutes: int = Field(
        default=60, alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES"
    )

    # Resend Configuration
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    resend_from_email: str | None = Field(default=None, alias="RESEND_FROM_EMAIL")

    # Frontend URL for password reset links
    frontend_url: str | None = Field(default=None, alias="FRONTEND_URL")

    # RapidAPI Configuration
    rapidapi_key: str | None = Field(default=None, alias="RAPIDAPI_KEY")

    @field_validator(
        "resend_api_key", "resend_from_email", mode="before"
    )
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for optional string fields and strip whitespace."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
