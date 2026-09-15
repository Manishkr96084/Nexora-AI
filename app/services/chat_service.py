import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.database import db_manager, _in_memory_chats, _in_memory_messages
from app.config import settings

logger = logging.getLogger("aichatbot.chat_service")

class ChatService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    async def create_chat(cls, title: str = "New Conversation", system_prompt: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        chat_id = f"chat_{uuid.uuid4().hex[:12]}"
        now = cls._now_iso()
        
        chat_doc = {
            "id": chat_id,
            "title": title or "New Conversation",
            "system_prompt": system_prompt or settings.DEFAULT_SYSTEM_PROMPT,
            "model": model or settings.DEFAULT_MODEL,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "last_message": None
        }

        if db_manager.is_connected and db_manager.db is not None:
            await db_manager.db.chats.insert_one(chat_doc.copy())
        else:
            _in_memory_chats[chat_id] = chat_doc.copy()

        return chat_doc

    @classmethod
    async def get_chat(cls, chat_id: str) -> Optional[Dict[str, Any]]:
        if db_manager.is_connected and db_manager.db is not None:
            chat = await db_manager.db.chats.find_one({"id": chat_id}, {"_id": 0})
            return chat
        else:
            return _in_memory_chats.get(chat_id)

    @classmethod
    async def list_chats(cls) -> List[Dict[str, Any]]:
        if db_manager.is_connected and db_manager.db is not None:
            cursor = db_manager.db.chats.find({}, {"_id": 0}).sort("updated_at", -1)
            chats = await cursor.to_list(length=100)
            return chats
        else:
            chats = list(_in_memory_chats.values())
            chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return chats

    @classmethod
    async def update_chat(cls, chat_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = cls._now_iso()
        clean_updates = {k: v for k, v in updates.items() if v is not None}

        if db_manager.is_connected and db_manager.db is not None:
            result = await db_manager.db.chats.find_one_and_update(
                {"id": chat_id},
                {"$set": clean_updates},
                return_document=True,
                projection={"_id": 0}
            )
            return result
        else:
            if chat_id in _in_memory_chats:
                _in_memory_chats[chat_id].update(clean_updates)
                return _in_memory_chats[chat_id]
            return None

    @classmethod
    async def delete_chat(cls, chat_id: str) -> bool:
        # Delete from MongoDB if connected
        if db_manager.is_connected and db_manager.db is not None:
            try:
                await db_manager.db.chats.delete_many({"$or": [{"id": chat_id}, {"_id": chat_id}]})
                await db_manager.db.messages.delete_many({"chat_id": chat_id})
            except Exception as e:
                logger.error(f"Error deleting chat from MongoDB: {e}")

        # Always delete from in-memory store as well
        global _in_memory_messages
        if chat_id in _in_memory_chats:
            del _in_memory_chats[chat_id]
        _in_memory_messages = [m for m in _in_memory_messages if m.get("chat_id") != chat_id]

        return True

    @classmethod
    async def add_message(cls, chat_id: str, role: str, content: str, model: Optional[str] = None) -> Dict[str, Any]:
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = cls._now_iso()

        msg_doc = {
            "id": msg_id,
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "model": model or settings.DEFAULT_MODEL,
            "timestamp": now
        }

        if db_manager.is_connected and db_manager.db is not None:
            await db_manager.db.messages.insert_one(msg_doc.copy())
            # Update chat metadata
            message_count = await db_manager.db.messages.count_documents({"chat_id": chat_id})
            await db_manager.db.chats.update_one(
                {"id": chat_id},
                {
                    "$set": {
                        "updated_at": now,
                        "message_count": message_count,
                        "last_message": content[:80] + ("..." if len(content) > 80 else "")
                    }
                }
            )
        else:
            _in_memory_messages.append(msg_doc.copy())
            if chat_id in _in_memory_chats:
                chat_msgs = [m for m in _in_memory_messages if m.get("chat_id") == chat_id]
                _in_memory_chats[chat_id]["message_count"] = len(chat_msgs)
                _in_memory_chats[chat_id]["last_message"] = content[:80] + ("..." if len(content) > 80 else "")
                _in_memory_chats[chat_id]["updated_at"] = now

        return msg_doc

    @classmethod
    async def get_messages(cls, chat_id: str) -> List[Dict[str, Any]]:
        if db_manager.is_connected and db_manager.db is not None:
            cursor = db_manager.db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("timestamp", 1)
            messages = await cursor.to_list(length=500)
            return messages
        else:
            messages = [m for m in _in_memory_messages if m.get("chat_id") == chat_id]
            messages.sort(key=lambda x: x.get("timestamp", ""))
            return messages
