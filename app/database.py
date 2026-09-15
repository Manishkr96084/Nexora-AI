import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.config import settings

logger = logging.getLogger("aichatbot.database")

# In-memory fallback database structure
_in_memory_chats: Dict[str, Dict[str, Any]] = {}
_in_memory_messages: List[Dict[str, Any]] = []

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_connected = False
        self.mode = "disconnected"

    async def connect(self):
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2000
            )
            # Verify connection with a quick ping command
            await self.client.admin.command('ping')
            self.db = self.client[settings.DATABASE_NAME]
            self.is_connected = True
            self.mode = "connected"
            logger.info(f"Successfully connected to MongoDB database: '{settings.DATABASE_NAME}'")
            
            # Ensure indexes
            await self.db.chats.create_index("id", unique=True)
            await self.db.messages.create_index("chat_id")
            await self.db.messages.create_index("id", unique=True)
            
        except Exception as e:
            logger.warning(f"MongoDB connection attempt failed: {e}. Active mode: In-Memory Fallback.")
            self.client = None
            self.db = None
            self.is_connected = False
            self.mode = "in-memory-fallback"

    async def check_health(self) -> Dict[str, Any]:
        """Check current database status and auto-reconnect if needed."""
        if self.client:
            try:
                await self.client.admin.command('ping')
                self.is_connected = True
                self.mode = "connected"
            except Exception:
                logger.warning("MongoDB ping failed during health check. Re-attempting connection...")
                self.is_connected = False
                await self.connect()
        else:
            # Re-attempt connection in case MongoDB was started after app launch
            await self.connect()
            
        return {
            "is_connected": self.is_connected,
            "mode": self.mode,
            "uri": settings.MONGODB_URI,
            "database_name": settings.DATABASE_NAME
        }

db_manager = DatabaseManager()
