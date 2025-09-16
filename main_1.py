import os
from fastapi import FastAPI, HTTPException, Body, Query
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from bson import ObjectId
from pydantic import BaseModel
from auth_module import verifygtoken
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()

MONGODB_URI = os.getenv("MONGODB_URI")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.quizapp

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class User(BaseModel):
    email: str
    name: str
    picture: str | None = None


class Result(BaseModel):
    user_id: str  # MongoDB ObjectId as string
    points: int
    time_taken: float


# Add this new model for the Google token request
class GoogleTokenRequest(BaseModel):
    token: str


@app.post("/auth/google")
async def google_login(request: GoogleTokenRequest):
    user_data = verifygtoken(request.token)
    email, name, picture = user_data["email"], user_data["name"], user_data.get("picture")

    user = await db.users.find_one({"email": email})
    if not user:
        result = await db.users.insert_one({"email": email, "name": name, "picture": picture})
        user_id = str(result.inserted_id)
    else:
        user_id = str(user["_id"])

    return {"user_id": user_id, "email": email, "name": name, "picture": picture}


@app.post("/result")
async def submit_result(result: Result):
    user = await db.users.find_one({"_id": ObjectId(result.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.results.insert_one({
        "user_id": ObjectId(result.user_id),
        "points": result.points,
        "time_taken": result.time_taken
    })
    return {"msg": "Result saved!"}


@app.get("/leaderboard")
async def leaderboard():
    pipeline = [
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        {"$unwind": "$user_info"},
        {"$sort": {"points": -1, "time_taken": 1}}
    ]
    cursor = db.results.aggregate(pipeline)
    results = []
    async for doc in cursor:
        results.append({
            "name": doc["user_info"]["name"],
            "points": doc["points"],
            "time_taken": doc["time_taken"]
        })
    return results


@app.get("/user/has-taken-quiz")
async def has_taken_quiz(user_email: str):
    user = await db.users.find_one({"email": user_email})
    if not user:
        return {"has_taken": False}
    result = await db.results.find_one({"user_id": user["_id"]})
    return {"has_taken": result is not None}