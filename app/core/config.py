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

    # SMTP Configuration (optional for now)
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int | None = Field(default=None, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    
    # Frontend URL for password reset links
    frontend_url: str | None = Field(default=None, alias="FRONTEND_URL")

    @field_validator("smtp_host", "smtp_user", "smtp_password", "smtp_from_email", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for optional string fields."""
        if v == "":
            return None
        return v

    @field_validator("smtp_port", mode="before")
    @classmethod
    def empty_str_to_none_int(cls, v: str | int | None) -> int | None:
        """Convert empty strings to None for optional integer fields."""
        if v == "":
            return None
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return None
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
