from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Initialize the FastAPI application
app = FastAPI()

# Define the database connection
SQLALCHEMY_DATABASE_URL = "sqlite:///software_courses.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the base class for models
Base = declarative_base()

# Define the SoftwareCourse model
class SoftwareCourse(Base):
    __tablename__ = "software_courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)
    duration = Column(String)

# Create the database tables
Base.metadata.create_all(engine)

# Define the Pydantic model for SoftwareCourse
class SoftwareCourseSchema(BaseModel):
    id: int
    name: str
    description: str
    duration: str

# Define the Pydantic model for creating a SoftwareCourse
class CreateSoftwareCourseSchema(BaseModel):
    name: str
    description: str
    duration: str

# API 1: Create a new software course
@app.post("/software-course/", response_model=SoftwareCourseSchema)
async def create_software_course(course: CreateSoftwareCourseSchema):
    db = SessionLocal()
    existing_course = db.query(SoftwareCourse).filter(SoftwareCourse.name == course.name).first()
    if existing_course:
        raise HTTPException(status_code=400, detail="Course with same name already exists")
    new_course = SoftwareCourse(name=course.name, description=course.description, duration=course.duration)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

# API 2: Retrieve the list of software courses
@app.get("/software-courses/", response_model=List[SoftwareCourseSchema])
async def get_software_courses():
    db = SessionLocal()
    courses = db.query(SoftwareCourse).all()
    return courses