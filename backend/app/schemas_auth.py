from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validate_password_strength(value: str) -> str:
    if not any(char.islower() for char in value) or not any(char.isupper() for char in value) or not any(char.isdigit() for char in value):
        raise ValueError("Password must include upper-case, lower-case, and numeric characters")
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    identity: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class EmailRequest(BaseModel):
    email: EmailStr


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordResetRequest(TokenRequest):
    password: str = Field(min_length=10, max_length=128)

    _password_strength = field_validator("password")(validate_password_strength)


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=280)
    avatar_url: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    role: str
    email_verified: bool
    profile: ProfileUpdate
