from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import get_settings

router = APIRouter()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegData(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    password: str


class LoginData(BaseModel):
    email: EmailStr
    password: str


users_db: dict[str, dict[str, str]] = {}


@router.post("/signup")
def signup(data: RegData) -> dict[str, str]:
    if data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password too short")
    users_db[data.email] = {
        "fname": data.fname,
        "lname": data.lname,
        "password": pwd.hash(data.password),
    }
    return {"message": "Account created successfully"}


@router.post("/signin")
def signin(data: LoginData) -> dict[str, str]:
    usr = users_db.get(data.email)
    if not usr or not pwd.verify(data.password, usr["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    exp = datetime.now(UTC) + timedelta(hours=24)
    settings = get_settings()
    token = jwt.encode(
        {"email": data.email, "exp": exp}, settings.secret_key, algorithm="HS256"
    )
    return {"token": token, "email": data.email}
