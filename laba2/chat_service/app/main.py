from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List, Dict, Optional
from jose import JWTError, jwt
import os
import httpx
from datetime import datetime

USER_SERVICE_URL = "http://user_service:8000"

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{USER_SERVICE_URL}/token")

# Временное хранилище чатов
chats_db: Dict[int, Dict] = {
    1: {
        "name": "General Chat",
        "creator_id": 1,
        "participant_ids": [1],
        "messages": []
    }
}

class AddParticipantsRequest(BaseModel):
    participant_ids: List[int]

class ChatMessage(BaseModel):
    text: str

class ChatCreateRequest(BaseModel):
    name: str
    initial_participant_ids: List[int] = []

async def get_user_info(user_id: int, token: str) -> Dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{USER_SERVICE_URL}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        response.raise_for_status()
        return response.json()

@app.post("/chats", status_code=status.HTTP_201_CREATED)
async def create_chat(
    request: ChatCreateRequest,
    token: str = Depends(oauth2_scheme)
):
    current_user_info = await get_user_info(user_id=None, token=token)
    current_user_id = current_user_info["id"]

    for participant_id in request.initial_participant_ids:
        await get_user_info(participant_id, token)

    new_id = max(chats_db.keys(), default=0) + 1
    chats_db[new_id] = {
        "name": request.name,
        "creator_id": current_user_id,
        "participant_ids": [current_user_id] + request.initial_participant_ids,
        "messages": []
    }
    return {"chat_id": new_id}

@app.post("/chats/{chat_id}/participants")
async def add_participants(
    chat_id: int,
    request: AddParticipantsRequest,
    token: str = Depends(oauth2_scheme)
):
    current_user_info = await get_user_info(user_id=None, token=token)
    current_user_id = current_user_info["id"]

    if chat_id not in chats_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if chats_db[chat_id]["creator_id"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only chat creator can add participants"
        )
    
    for participant_id in request.participant_ids:
        await get_user_info(participant_id, token)

    existing = set(chats_db[chat_id]["participant_ids"])
    new_participants = [p for p in request.participant_ids if p not in existing]
    chats_db[chat_id]["participant_ids"].extend(new_participants)
    
    return {
        "status": "participants added",
        "count": len(new_participants),
        "total": len(chats_db[chat_id]["participant_ids"])
    }

@app.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: int,
    message: ChatMessage,
    token: str = Depends(oauth2_scheme)
):
    current_user_info = await get_user_info(user_id=None, token=token)
    current_user_id = current_user_info["id"]

    if chat_id not in chats_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if current_user_id not in chats_db[chat_id]["participant_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You're not a participant of this chat"
        )
    
    user_info = await get_user_info(current_user_id, token)
    
    chats_db[chat_id]["messages"].append({
        "sender_id": current_user_id,
        "sender_login": user_info.get("login"),
        "text": message.text,
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "message sent"}

@app.get("/chats/{chat_id}")
async def get_chat(
    chat_id: int,
    token: str = Depends(oauth2_scheme)
):
    current_user_info = await get_user_info(user_id=None, token=token)
    current_user_id = current_user_info["id"]

    if chat_id not in chats_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if current_user_id not in chats_db[chat_id]["participant_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    participants_info = []
    for user_id in chats_db[chat_id]["participant_ids"]:
        try:
            user_info = await get_user_info(user_id, token)
            participants_info.append({
                "id": user_id,
                "login": user_info.get("login"),
                "name": user_info.get("name", "")
            })
        except HTTPException:
            continue
    
    return {
        "chat_id": chat_id,
        "name": chats_db[chat_id]["name"],
        "creator_id": chats_db[chat_id]["creator_id"],
        "participants": participants_info,
        "messages": chats_db[chat_id]["messages"]
    }