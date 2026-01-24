from pydantic import BaseModel, EmailStr, ConfigDict, Field

from app.schemas.role import Role


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role_id: int
    role: Role


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    role_id: int | None = None  # If not provided, defaults to "tenant"


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
