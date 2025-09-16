from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    email: str
    name: str
    picture: Optional[str]

class Result(BaseModel):
    user_id: str   # Mongo ObjectId stored as string
    points: int
    time_taken: float
