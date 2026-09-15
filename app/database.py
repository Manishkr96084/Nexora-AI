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
        self._db = None
        self.is_connected = False
        self.mode = "disconnected"

    async def connect(self):
        try:
            import os
            # If running on Vercel and no cloud MongoDB URI is supplied, fallback immediately without cold start delay
            if os.getenv("VERCEL") and ("localhost" in settings.MONGODB_URI or "127.0.0.1" in settings.MONGODB_URI):
                logger.info("Running on Vercel without cloud MongoDB URI. Using In-Memory Fallback.")
                self.client = None
                self._db = None
                self.is_connected = False
                self.mode = "in-memory-fallback"
                return

            from motor.motor_asyncio import AsyncIOMotorClient
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=1500
            )
            # Verify connection with a quick ping command
            await self.client.admin.command('ping')
            self._db = self.client[settings.DATABASE_NAME]
            self.is_connected = True
            self.mode = "connected"
            logger.info(f"Successfully connected to MongoDB database: '{settings.DATABASE_NAME}'")
            
            # Ensure indexes
            await self._db.chats.create_index("id", unique=True)
            await self._db.messages.create_index("chat_id")
            await self._db.messages.create_index("id", unique=True)
            
        except Exception as e:
            logger.warning(f"MongoDB connection attempt failed: {e}. Active mode: In-Memory Fallback.")
            self.client = None
            self._db = None
            self.is_connected = False
            self.mode = "in-memory-fallback"

    @property
    def db(self):
        if not self.is_connected or self.client is None:
            return None
        try:
            # Check if event loop is running
            asyncio.get_running_loop()
            return self.client[settings.DATABASE_NAME]
        except Exception:
            return None

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
