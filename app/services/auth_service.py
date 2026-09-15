import hashlib
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.database import db_manager

logger = logging.getLogger("aichatbot.auth")

# In-memory storage for users and active sessions when MongoDB is not connected
_in_memory_users: Dict[str, Dict[str, Any]] = {}
_in_memory_sessions: Dict[str, str] = {}  # token -> user_id

class AuthService:
    """Manages user registration, login authentication, and active sessions."""

    @staticmethod
    def _hash_password(password: str, salt: str = "ai_bot_secure_salt_2026") -> str:
        """Generates a secure SHA-256 password hash."""
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

    @classmethod
    async def register_user(cls, username: str, email: str, password: str) -> Dict[str, Any]:
        """Registers a new user account."""
        clean_username = username.strip()
        clean_email = email.strip().lower()

        # Check existing user in DB
        db = db_manager.db
        if db is not None and db_manager.is_connected:
            existing = await db.users.find_one({"$or": [{"email": clean_email}, {"username": clean_username}]})
            if existing:
                if existing.get("email") == clean_email:
                    return {"status": "error", "message": "Email is already registered. Please login."}
                return {"status": "error", "message": "Username is already taken. Please choose another."}

            user_id = f"user_{uuid.uuid4().hex[:12]}"
            hashed_pw = cls._hash_password(password)
            created_at = datetime.utcnow().isoformat()
            avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={clean_username}"

            user_doc = {
                "id": user_id,
                "username": clean_username,
                "email": clean_email,
                "password": hashed_pw,
                "avatar_url": avatar_url,
                "created_at": created_at
            }
            await db.users.insert_one(user_doc)
        else:
            # In-memory registration fallback
            for u in _in_memory_users.values():
                if u["email"] == clean_email:
                    return {"status": "error", "message": "Email is already registered. Please login."}
                if u["username"].lower() == clean_username.lower():
                    return {"status": "error", "message": "Username is already taken. Please choose another."}

            user_id = f"user_{uuid.uuid4().hex[:12]}"
            hashed_pw = cls._hash_password(password)
            created_at = datetime.utcnow().isoformat()
            avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={clean_username}"

            user_doc = {
                "id": user_id,
                "username": clean_username,
                "email": clean_email,
                "password": hashed_pw,
                "avatar_url": avatar_url,
                "created_at": created_at
            }
            _in_memory_users[user_id] = user_doc

        # Generate session token
        token = f"token_{uuid.uuid4().hex}"
        _in_memory_sessions[token] = user_id

        user_data = {
            "id": user_doc["id"],
            "username": user_doc["username"],
            "email": user_doc["email"],
            "avatar_url": user_doc["avatar_url"],
            "created_at": user_doc["created_at"]
        }

        return {
            "status": "success",
            "message": "User account created successfully!",
            "token": token,
            "user": user_data
        }

    @classmethod
    async def login_user(cls, email_or_username: str, password: str) -> Dict[str, Any]:
        """Authenticates user login credentials."""
        clean_input = email_or_username.strip().lower()
        hashed_pw = cls._hash_password(password)

        user_doc = None
        db = db_manager.db
        if db is not None and db_manager.is_connected:
            user_doc = await db.users.find_one({
                "$or": [
                    {"email": clean_input},
                    {"username": clean_input}
                ]
            })
        else:
            for u in _in_memory_users.values():
                if u["email"] == clean_input or u["username"].lower() == clean_input:
                    user_doc = u
                    break

        if not user_doc:
            return {"status": "error", "message": "Account not found. Please register first."}

        if user_doc["password"] != hashed_pw:
            return {"status": "error", "message": "Incorrect password. Please try again."}

        # Generate session token
        token = f"token_{uuid.uuid4().hex}"
        _in_memory_sessions[token] = user_doc["id"]

        user_data = {
            "id": user_doc["id"],
            "username": user_doc["username"],
            "email": user_doc["email"],
            "avatar_url": user_doc.get("avatar_url", ""),
            "created_at": user_doc.get("created_at", "")
        }

        return {
            "status": "success",
            "message": "Welcome back! Login successful.",
            "token": token,
            "user": user_data
        }

    @classmethod
    async def get_user_by_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile by session token."""
        if not token or token not in _in_memory_sessions:
            return None

        user_id = _in_memory_sessions[token]
        db = db_manager.db
        if db is not None and db_manager.is_connected:
            user_doc = await db.users.find_one({"id": user_id})
            if user_doc:
                return {
                    "id": user_doc["id"],
                    "username": user_doc["username"],
                    "email": user_doc["email"],
                    "avatar_url": user_doc.get("avatar_url", ""),
                    "created_at": user_doc.get("created_at", "")
                }

        if user_id in _in_memory_users:
            u = _in_memory_users[user_id]
            return {
                "id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "avatar_url": u.get("avatar_url", ""),
                "created_at": u.get("created_at", "")
            }

        return None

    @classmethod
    async def logout_user(cls, token: str) -> Dict[str, Any]:
        """Invalidates user session token."""
        if token in _in_memory_sessions:
            del _in_memory_sessions[token]
        return {"status": "success", "message": "Logged out successfully."}
