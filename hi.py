from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets

DATABASE_URL = "sqlite:///./event.db"
engine = create_engine(DATABASE_URL)
Sessionlocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class EventUser(Base):
    __tablename__ = "event"
    e_id = Column(Integer, primary_key=True, index=True)
    e_name = Column(String)
    e_email = Column(String, unique=True)
    e_password = Column(String)


class UserSchema(BaseModel):
    e_id: int
    e_name: Optional[str] = None
    e_password: Optional[str] = None
    e_email: Optional[str] = None


Base.metadata.create_all(bind=engine)


def get_db():
    try:
        db = Sessionlocal()
        yield db
    finally:
        db.close()


app = FastAPI()
templates = Jinja2Templates(directory="templates")

tokens = {}


def generate_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    tokens[token] = {"email": email, "expiry": datetime.utcnow() + timedelta(minutes=30)}
    return token


def verify_token(token: str) -> Optional[str]:
    token_data = tokens.get(token)
    if token_data and token_data["expiry"] > datetime.utcnow():
        return token_data["email"]
    return None


def generate_reset_token(email: str) -> str:
    reset_token = secrets.token_urlsafe(32)
    tokens[reset_token] = {"email": email, "expiry": datetime.utcnow() + timedelta(minutes=30)}
    return reset_token


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@app.get("/login")
def loginp(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(email: str = Form(...),password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(EventUser).filter(EventUser.e_email == email).first()
    if user and verify_password(password, user.e_password):
        token = generate_token(email)
        response = templates.TemplateResponse("dashboard.html", {"request": request, "user_name": user.e_name})
        response.set_cookie(key="access_token", value=token, httponly=True)
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("spage.html", {"request": request})


@app.post("/")
def signup(name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(EventUser).filter(EventUser.e_email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(password)
    new_user = EventUser(e_name=name, e_email=email, e_password=hashed_password)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred")

    return new_user
