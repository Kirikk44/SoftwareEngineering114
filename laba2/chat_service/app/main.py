from fastapi import FastAPI, HTTPException, Depends, Request, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
import httpx

USER_SERVICE_URL = "http://user_service:8000"

app = FastAPI()

client = MongoClient("mongodb://root:example@mongodb:27017/")
db = client.chatdb

class ChatCreate(BaseModel):
    name: str

class MessageCreate(BaseModel):
    text: str

class AddParticipantRequest(BaseModel):
    user_ids: List[int]

async def get_user_info(user_id: int, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{USER_SERVICE_URL}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        response.raise_for_status()
        return response.json()
    
async def check_user_exists(user_id: int) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        response.raise_for_status()

async def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = auth.split(" ")[1]

    async with httpx.AsyncClient() as client:
        users = await client.get(f"{USER_SERVICE_URL}/users", headers={"Authorization": f"Bearer {token}"})
        if users.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid token")
        users.raise_for_status()
        return users.json()[0]

@app.post("/chats")
async def create_chat(chat: ChatCreate, request: Request):
    user = await get_current_user(request)
    chat_id = db.chats.count_documents({}) + 1
    chat_data = {
        "chat_id": chat_id,
        "name": chat.name,
        "creator_id": user["id"],
        "participants": [user["id"]],
        "created_at": datetime.now(datetime.timezone.utc)
    }
    db.chats.insert_one(chat_data)
    return {"chat_id": chat_id}

@app.post("/chats/{chat_id}/participants")
async def add_participants(chat_id: int, data: AddParticipantRequest, request: Request):
    user = await get_current_user(request)
    chat = db.chats.find_one({"chat_id": chat_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only creator can add participants")

    for uid in data.user_ids:
        await check_user_exists(uid)
    
    db.chats.update_one({"chat_id": chat_id}, {"$addToSet": {"participants": {"$each": data.user_ids}}})
    return {"status": "Participants added"}

@app.post("/chats/{chat_id}/messages")
async def send_message(chat_id: int, message: MessageCreate, request: Request):
    user = await get_current_user(request)
    chat = db.chats.find_one({"chat_id": chat_id})
    if not chat or user["id"] not in chat["participants"]:
        raise HTTPException(status_code=403, detail="Not a chat participant")
    
    msg = {
        "chat_id": chat_id,
        "sender_id": user["id"],
        "text": message.text,
        "timestamp": datetime.utcnow()
    }
    db.messages.insert_one(msg)
    return {"status": "Message sent"}

@app.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: int, limit: int = 100):
    messages = db.messages.find({"chat_id": chat_id}).sort("timestamp", DESCENDING).limit(limit)
    return list(messages)

@app.get("/users/me/chats")
async def get_user_chats(request: Request):
    user = await get_current_user(request)
    chats = db.chats.find({"participants": user["id"]})
    return list(chats)
