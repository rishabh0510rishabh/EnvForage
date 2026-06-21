
# --- Pydantic Validation Suite ---
import re
from datetime import date
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)

# Robust Regex Patterns
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{1,14}$")

class UserProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    username: str = Field(..., pattern=r"^[a-zA-Z0-9_.-]{3,30}$", description="Unique alphanumeric username")
    email: EmailStr = Field(..., description="Valid email address")
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    birth_date: date | None = None
    website: HttpUrl | None = None
    phone_number: str | None = Field(None, description="E.164 formatted phone number")
    metadata_tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v and not PHONE_REGEX.match(v):
            raise ValueError('Invalid phone number format. Must comply with E.164.')
        return v

    @field_validator('birth_date')
    @classmethod
    def validate_age(cls, v: date | None) -> date | None:
        if v:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 13:
                raise ValueError('User must be at least 13 years old.')
            if age > 120:
                raise ValueError('Invalid birth date.')
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_name(self) -> str:
        """Dynamically computes a safe display name based on available fields."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.username

    @computed_field  # type: ignore[prop-decorator]
    @property
    def profile_completeness_score(self) -> int:
        """Calculates profile completion percentage."""
        score = 0
        if self.first_name: score += 20
        if self.last_name: score += 20
        if self.birth_date: score += 20
        if self.website: score += 20
        if self.phone_number: score += 20
        return score

class UserProfileCreate(UserProfileBase):
    password: str = Field(..., description="Strong password")
    password_confirm: str = Field(..., description="Password confirmation")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                'Password must contain at least 8 characters, one uppercase, '
                'one lowercase, one number and one special character.'
            )
        return v

    @model_validator(mode='after')
    def verify_passwords_match(self) -> 'UserProfileCreate':
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    website: HttpUrl | None = None
    metadata_tags: list[str] | None = Field(None, max_length=20)
    preferences: dict[str, Any] | None = None

    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'UserProfileUpdate':
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("At least one field must be provided for update")
        return self
