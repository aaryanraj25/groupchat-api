# main.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
import os
from uuid import uuid4

app = FastAPI(title="Group Chat API")

# Data Models
class User(BaseModel):
    id: str
    username: str
    email: str
    org_ids: List[str] = []

class Organization(BaseModel):
    id: str
    name: str
    description: str

class Message(BaseModel):
    id: str
    content: str
    user_id: str
    timestamp: str
    likes: List[str] = []  # List of user IDs who liked
    dislikes: List[str] = []  # List of user IDs who disliked

class Group(BaseModel):
    id: str
    name: str
    description: str
    org_id: str
    members: List[str] = []  # List of user IDs
    messages: List[Message] = []

# Database functions
def load_data(filename: str, default_data: dict = None):
    if default_data is None:
        default_data = {}
    try:
        if os.path.exists(f"data/{filename}"):
            with open(f"data/{filename}", "r") as f:
                return json.load(f)
        os.makedirs("data", exist_ok=True)
        save_data(filename, default_data)
        return default_data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return default_data

def save_data(filename: str, data: dict):
    try:
        with open(f"data/{filename}", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# Initialize data stores
users_db = load_data("users.json", {})
orgs_db = load_data("organizations.json", {})
groups_db = load_data("groups.json", {})

# User endpoints
@app.post("/users/", response_model=User)
async def create_user(user: User):
    if user.id in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    users_db[user.id] = user.dict()
    save_data("users.json", users_db)
    return user

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

# Organization endpoints
@app.post("/organizations/", response_model=Organization)
async def create_organization(org: Organization):
    if org.id in orgs_db:
        raise HTTPException(status_code=400, detail="Organization already exists")
    orgs_db[org.id] = org.dict()
    save_data("organizations.json", orgs_db)
    return org

# Group endpoints
@app.post("/groups/", response_model=Group)
async def create_group(group: Group):
    if group.id in groups_db:
        raise HTTPException(status_code=400, detail="Group already exists")
    groups_db[group.id] = group.dict()
    save_data("groups.json", groups_db)
    return group

@app.post("/groups/{group_id}/members/{user_id}")
async def add_member_to_group(group_id: str, user_id: str):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id not in groups_db[group_id]["members"]:
        groups_db[group_id]["members"].append(user_id)
        save_data("groups.json", groups_db)
    return {"message": "Member added successfully"}

@app.post("/groups/{group_id}/messages")
async def create_message(group_id: str, content: str, user_id: str):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    message = Message(
        id=str(uuid4()),
        content=content,
        user_id=user_id,
        timestamp=datetime.now().isoformat()
    ).dict()
    
    groups_db[group_id]["messages"].append(message)
    save_data("groups.json", groups_db)
    return message

@app.post("/groups/{group_id}/messages/{message_id}/react")
async def react_to_message(group_id: str, message_id: str, user_id: str, reaction: str):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group = groups_db[group_id]
    message = None
    for msg in group["messages"]:
        if msg["id"] == message_id:
            message = msg
            break
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Remove existing reaction if any
    if user_id in message["likes"]:
        message["likes"].remove(user_id)
    if user_id in message["dislikes"]:
        message["dislikes"].remove(user_id)
    
    # Add new reaction
    if reaction == "like":
        message["likes"].append(user_id)
    elif reaction == "dislike":
        message["dislikes"].append(user_id)
    
    save_data("groups.json", groups_db)
    return message

@app.get("/groups/{group_id}/messages")
async def get_messages(group_id: str):
    if group_id not in groups_db:
        raise HTTPException(status_code=404, detail="Group not found")
    
    messages = groups_db[group_id]["messages"]
    for message in messages:
        # Calculate reaction color
        total_reactions = len(message["likes"]) + len(message["dislikes"])
        if total_reactions > 0:
            like_ratio = len(message["likes"]) / total_reactions
            if like_ratio == 1:
                message["color"] = "green"
            elif like_ratio == 0:
                message["color"] = "red"
            else:
                message["color"] = "yellow"
        else:
            message["color"] = "gray"
    
    return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)