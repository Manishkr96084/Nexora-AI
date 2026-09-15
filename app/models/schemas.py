from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class MessageBase(BaseModel):
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Text content of the message")
    model: Optional[str] = "smart-fallback"

class MessageCreate(MessageBase):
    chat_id: str

class MessageResponse(MessageBase):
    id: str
    chat_id: str
    timestamp: str

class ChatCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    system_prompt: Optional[str] = None
    model: Optional[str] = "smart-fallback"

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None

class ChatResponse(BaseModel):
    id: str
    title: str
    system_prompt: str
    model: str
    created_at: str
    updated_at: str
    message_count: int = 0
    last_message: Optional[str] = None

class ImageAttachment(BaseModel):
    mime_type: str
    data: str

class FileAttachment(BaseModel):
    filename: str
    content_type: Optional[str] = None
    data: str
    is_pdf: bool = False

class StreamChatRequest(BaseModel):
    chat_id: Optional[str] = None
    prompt: str
    history: Optional[List[dict]] = None
    images: Optional[List[ImageAttachment]] = None
    files: Optional[List[FileAttachment]] = None
    model: Optional[str] = "gemini-2.5-flash"
    system_prompt: Optional[str] = None

class SettingsUpdate(BaseModel):
    mongodb_uri: Optional[str] = None
    gemini_api_key: Optional[str] = None
    default_model: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    mongodb: str
    mongodb_mode: str
    active_model: str
    has_gemini_key: bool

# --- Authentication Schemas ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(...)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email_or_username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    avatar_url: Optional[str] = None
    created_at: str

class AuthResponse(BaseModel):
    status: str
    message: str
    token: Optional[str] = None
    user: Optional[UserResponse] = None

# --- Voice Assistant Schemas ---
class VoiceTTSRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech")
    language: Optional[str] = "en"
    slow: Optional[bool] = False

class VoiceSTTRequest(BaseModel):
    audio_data: str = Field(..., description="Base64-encoded audio data (WebM/WAV/OGG)")
    language: Optional[str] = "en-US"
    model: Optional[str] = "google-gemini"
