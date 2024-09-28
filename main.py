from fastapi import FastAPI, Request, Form, HTTPException, Depends, Cookie
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets

# Database configuration
DATABASE_URL = "sqlite:///./event.db"
engine = create_engine(DATABASE_URL)
Sessionlocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
Base = declarative_base()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class EventUser(Base):
    __tablename__ = "event"
    e_id = Column(Integer, primary_key=True, index=True)
    e_name = Column(String)
    e_email = Column(String, unique=True)
    e_password = Column(String)

# Pydantic models
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

# FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME="bodavamshikrishna30@gmail.com",
    MAIL_PASSWORD="idxl ankf mkqt zidu",
    MAIL_FROM="bodavamshikrishna30@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL=False,
)

# Token storage (in-memory for simplicity)
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
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(EventUser).filter(EventUser.e_email == email).first()
    if user and verify_password(password, user.e_password):
        token = generate_token(email)
        response = templates.TemplateResponse("dashboard.html", {"request": Request(), "user_name": user.e_name})
        response.set_cookie(key="access_token", value=token, httponly=True)
        return response
    return {"detail": "Invalid credentials"}

@app.get("/")
def add(request: Request):
    return templates.TemplateResponse("spage.html", {"request": request})

@app.post("/")
def signup(name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(EventUser).filter(EventUser.e_email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(password)
    user = EventUser(e_name=name, e_email=email, e_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/fetch/signupenrolls")
def readsignups(id: int, db: Session = Depends(get_db)):
    db_user = db.query(EventUser).filter(EventUser.e_id == id).first()
    if db_user:
        return db_user
    return f"User with ID {id} doesn't exist"

@app.get("/signupdetails")
def read():
    return {"message": "Endpoint not implemented or unnecessary"}

@app.post("/request_reset_password")
async def request_reset_password(email: EmailStr, db: Session = Depends(get_db)):
    user = db.query(EventUser).filter(EventUser.e_email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = generate_reset_token(email)
    reset_link = f"http://localhost:8000/reset_password?token={reset_token}"

    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"Click the following link to reset your password: {reset_link}",
        subtype="text",
    )
    fm = FastMail(conf)
    await fm.send_message(message)

    return {"message": "Password reset link sent"}

@app.get("/reset_password")
def reset_password_form(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@app.post("/reset_password")
def reset_password(token: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=404, detail="Invalid or expired token")

    user = db.query(EventUser).filter(EventUser.e_email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.e_password = hash_password(password)
    db.commit()
    db.refresh(user)
    return {"message": "Password successfully reset"}

@app.get("/logout")
def logout(request: Request, access_token: str = Cookie(None)):
    if access_token in tokens:
        tokens.pop(access_token)
    response = templates.TemplateResponse("login.html", {"request": request, "message": "Logged out successfully"})
    response.set_cookie(key="access_token", value="", expires=0)  # Clear the cookie
    return response
