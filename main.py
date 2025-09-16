import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from pydantic import BaseModel
from auth_module import verifygtoken
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()
app = FastAPI()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

origins = [
    "https://ohcorientation.vercel.app/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Adjust this for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

class DBResult(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    points = Column(Integer)
    time_taken = Column(Float)
    created_at = Column(DateTime, default=func.now())

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class User(BaseModel):
    email: str
    name: str
    picture: str | None = None

class Result(BaseModel):
    user_id: str
    points: int
    time_taken: float

class GoogleTokenRequest(BaseModel):
    token: str

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/auth/google")
async def google_login(request: GoogleTokenRequest):
    user_data = verifygtoken(request.token)
    email, name, picture = user_data["email"], user_data["name"], user_data.get("picture")

    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(DBUser).filter(DBUser.email == email).first()
        
        if not user:
            # Create new user
            user = DBUser(email=email, name=name, picture=picture)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return {"user_id": user.id, "email": user.email, "name": user.name, "picture": user.picture}
    
    finally:
        db.close()

@app.post("/result")
async def submit_result(result: Result):
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(DBUser).filter(DBUser.id == result.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Save result
        db_result = DBResult(user_id=result.user_id, points=result.points, time_taken=result.time_taken)
        db.add(db_result)
        db.commit()
        
        return {"msg": "Result saved!"}
    
    finally:
        db.close()

@app.get("/leaderboard")
async def leaderboard():
    db = SessionLocal()
    try:
        # Join users and results, order by points (desc) then time (asc)
        results = db.query(
            DBUser.name,
            DBResult.points,
            DBResult.time_taken
        ).join(
            DBResult, DBUser.id == DBResult.user_id
        ).order_by(
            DBResult.points.desc(),
            DBResult.time_taken.asc()
        ).all()
        
        return [
            {"name": result.name, "points": result.points, "time_taken": result.time_taken}
            for result in results
        ]
    
    finally:
        db.close()

@app.get("/user/has-taken-quiz")
async def has_taken_quiz(user_email: str):
    db = SessionLocal()
    try:
        user = db.query(DBUser).filter(DBUser.email == user_email).first()
        if not user:
            return {"has_taken": False}
        
        result = db.query(DBResult).filter(DBResult.user_id == user.id).first()
        return {"has_taken": result is not None}
    
    finally:
        db.close()