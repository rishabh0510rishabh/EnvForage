
# --- Strict Input Sanitization ---
from pydantic import BaseModel, Field, constr


class ProfileCreateSchema(BaseModel):
    # Using constr with strip_whitespace to auto-sanitize inputs
    username: constr(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$") = Field(..., description="Unique username")  # type: ignore[valid-type]
    bio: constr(strip_whitespace=True, max_length=500) | None = Field(None, description="User biography")  # type: ignore[valid-type]
    company: constr(strip_whitespace=True, max_length=100) | None = Field(None)  # type: ignore[valid-type]

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "bio": "AI Researcher",
                "company": "DeepMind"
            }
        }
