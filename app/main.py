import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Body, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db_manager
from app.models.schemas import (
    ChatCreate, ChatUpdate, ChatResponse,
    StreamChatRequest, SettingsUpdate, HealthResponse,
    UserRegister, UserLogin, AuthResponse,
    VoiceTTSRequest, VoiceSTTRequest
)
from app.services.chat_service import ChatService
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.voice_service import VoiceService
from app.services.weather_service import WeatherService
from app.services.time_service import TimeService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("aichatbot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NEXORA AI backend...")
    try:
        await asyncio.wait_for(db_manager.connect(), timeout=2.5)
    except Exception as e:
        logger.warning(f"Database initialization warning (using in-memory fallback): {e}")
    yield
    if db_manager.client:
        try:
            logger.info("Closing MongoDB client connection...")
            db_manager.client.close()
        except Exception:
            pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack AI Chatbot API powered by Google Gemini & FastAPI",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for production & development
origins = settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://.*" if "*" in origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CWD_DIR = os.getcwd()

possible_template_dirs = [
    os.path.join(BASE_DIR, "templates"),
    os.path.join(CWD_DIR, "templates"),
    "/var/task/templates"
]
template_dirs = [d for d in possible_template_dirs if os.path.exists(d)]
if not template_dirs:
    template_dirs = [os.path.join(BASE_DIR, "templates")]

possible_static_dirs = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(CWD_DIR, "static"),
    "/var/task/static"
]
static_dir = os.path.join(BASE_DIR, "static")
for d in possible_static_dirs:
    if os.path.exists(d):
        static_dir = d
        break

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=template_dirs)

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serve the single-page application UI"""
    try:
        return templates.TemplateResponse("index.html", {"request": request, "project_name": settings.PROJECT_NAME})
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        for tdir in template_dirs:
            index_path = os.path.join(tdir, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>NEXORA AI Backend Online</h1>", status_code=200)

@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    """Check backend health and connectivity"""
    db_status = await db_manager.check_health()
    return HealthResponse(
        status="online",
        mongodb="connected" if db_status["is_connected"] else "fallback",
        mongodb_mode=db_status["mode"],
        active_model=settings.DEFAULT_MODEL,
        has_gemini_key=bool(settings.GEMINI_API_KEY)
    )

@app.get("/api/weather")
async def get_weather(lat: float = None, lon: float = None, city: str = None):
    """Real-time weather endpoint via lat/lon or city name"""
    if lat is not None and lon is not None:
        return await WeatherService.get_weather_by_coords(lat, lon)
    elif city:
        return await WeatherService.get_weather_by_city(city)
    else:
        return await WeatherService.get_weather_by_city("Mumbai")

@app.get("/api/time")
async def get_time(city: str = None, tz: str = None):
    """Real-time timezone and current time endpoint"""
    if city:
        return await TimeService.get_time_for_city(city)
    elif tz:
        return TimeService.get_time_for_tz(tz)
    else:
        return TimeService.get_time_for_tz("Asia/Kolkata", location_label="Local Time")

@app.get("/api/chats")
async def list_chats():
    """Retrieve list of conversation threads"""
    chats = await ChatService.list_chats()
    return {"status": "success", "chats": chats}

@app.post("/api/chats")
async def create_chat(payload: ChatCreate):
    """Create a new chat thread"""
    chat = await ChatService.create_chat(
        title=payload.title,
        system_prompt=payload.system_prompt,
        model=payload.model
    )
    return {"status": "success", "chat": chat}

@app.get("/api/chats/{chat_id}")
async def get_chat_details(chat_id: str):
    """Get chat details and message history"""
    chat = await ChatService.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation thread not found")
    messages = await ChatService.get_messages(chat_id)
    return {"status": "success", "chat": chat, "messages": messages}

@app.patch("/api/chats/{chat_id}")
async def update_chat(chat_id: str, payload: ChatUpdate):
    """Update title, system prompt, or model for a chat"""
    updated = await ChatService.update_chat(chat_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation thread not found")
    return {"status": "success", "chat": updated}

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat thread and its messages"""
    await ChatService.delete_chat(chat_id)
    return {"status": "success", "message": "Chat deleted"}

@app.post("/chat")
@app.post("/api/chat")
async def chat_endpoint(req: StreamChatRequest):
    """
    Standard non-streaming JSON endpoint for AI chat response.
    Frontend sends: { "prompt": "Who is the president of India?" }
    Backend returns: { "success": true, "reply": "...", "response": "..." }
    """
    logger.info(f"[CHAT] User message: {req.prompt[:80]}")

    chat_id = req.chat_id
    if not chat_id:
        new_chat = await ChatService.create_chat(
            title=req.prompt[:30] + ("..." if len(req.prompt) > 30 else ""),
            system_prompt=req.system_prompt,
            model=req.model or settings.DEFAULT_MODEL
        )
        chat_id = new_chat["id"]

    logger.info(f"[CHAT] Conversation ID: {chat_id}")

    # Save user message to database
    await ChatService.add_message(chat_id=chat_id, role="user", content=req.prompt, model=req.model or settings.DEFAULT_MODEL)

    # Fetch existing conversation history for context
    raw_history = await ChatService.get_messages(chat_id=chat_id)
    clean_history = [
        {"role": str(m.get("role", "")), "content": str(m.get("content", ""))}
        for m in raw_history[:-1]
    ]
    if not clean_history and req.history:
        clean_history = [
            {"role": str(m.get("role", "")), "content": str(m.get("content", ""))}
            for m in req.history
        ]

    img_payload = [img.model_dump() for img in req.images] if req.images else None
    files_payload = [f.model_dump() for f in req.files] if req.files else None

    logger.info("[AI] Calling Gemini API")
    response_chunks = []
    try:
        async for chunk in AIService.generate_stream(
            prompt=req.prompt,
            history=clean_history,
            model=req.model or settings.DEFAULT_MODEL,
            images=img_payload,
            files=files_payload,
            system_prompt=req.system_prompt
        ):
            if chunk:
                response_chunks.append(chunk)
        logger.info("[AI] Gemini response received")
    except Exception as e:
        logger.error(f"[AI] Error generating response: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "reply": "Sorry, I couldn't process your request right now. Please try again.",
                "error": str(e)
            }
        )

    plain_text_response = "".join(response_chunks).strip()

    # Save complete AI response
    await ChatService.add_message(
        chat_id=chat_id,
        role="assistant",
        content=plain_text_response,
        model=req.model or settings.DEFAULT_MODEL
    )

    return {
        "success": True,
        "reply": plain_text_response,
        "response": plain_text_response,
        "conversation_id": chat_id
    }


@app.post("/api/chat/stream")
async def stream_chat(req: StreamChatRequest):
    """
    Stream AI response using Server-Sent Events (SSE).
    Automatically saves conversation history to MongoDB.
    """
    logger.info(f"[CHAT-STREAM] User message: {req.prompt[:80]}")

    chat_id = req.chat_id
    if not chat_id:
        new_chat = await ChatService.create_chat(
            title=req.prompt[:30] + ("..." if len(req.prompt) > 30 else ""),
            system_prompt=req.system_prompt,
            model=req.model or settings.DEFAULT_MODEL
        )
        chat_id = new_chat["id"]

    logger.info(f"[CHAT-STREAM] Conversation ID: {chat_id}")

    # Save user message to database
    await ChatService.add_message(chat_id=chat_id, role="user", content=req.prompt, model=req.model or settings.DEFAULT_MODEL)

    # Fetch existing conversation history for context
    raw_history = await ChatService.get_messages(chat_id=chat_id)
    clean_history = [
        {"role": str(m.get("role", "")), "content": str(m.get("content", ""))}
        for m in raw_history[:-1]
    ]
    if not clean_history and req.history:
        clean_history = [
            {"role": str(m.get("role", "")), "content": str(m.get("content", ""))}
            for m in req.history
        ]

    async def event_generator():
        meta_event = {"type": "meta", "chat_id": chat_id}
        yield f"data: {json.dumps(meta_event)}\n\n"

        img_payload = [img.model_dump() for img in req.images] if req.images else None
        files_payload = [f.model_dump() for f in req.files] if req.files else None
        full_ai_response = []

        logger.info("[AI] Calling Gemini API (stream)")
        try:
            async for chunk in AIService.generate_stream(
                prompt=req.prompt,
                history=clean_history,
                model=req.model or settings.DEFAULT_MODEL,
                images=img_payload,
                files=files_payload,
                system_prompt=req.system_prompt
            ):
                if chunk:
                    full_ai_response.append(chunk)
                    chunk_event = {"type": "content", "content": chunk}
                    yield f"data: {json.dumps(chunk_event)}\n\n"
            logger.info("[AI] Gemini stream complete")
        except Exception as e:
            logger.error(f"[AI] Stream error: {e}")
            err_msg = "Sorry, I couldn't process your request right now. Please try again."
            full_ai_response.append(err_msg)
            yield f"data: {json.dumps({'type': 'content', 'content': err_msg})}\n\n"

        # Save complete AI message to MongoDB
        complete_response_text = "".join(full_ai_response)
        await ChatService.add_message(
            chat_id=chat_id,
            role="assistant",
            content=complete_response_text,
            model=req.model or settings.DEFAULT_MODEL
        )

        done_event = {"type": "done", "chat_id": chat_id}
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/settings")
async def update_settings(payload: SettingsUpdate):
    """Update runtime settings (MongoDB URI, Gemini API Key, Model)"""
    if payload.mongodb_uri is not None:
        settings.MONGODB_URI = payload.mongodb_uri
        await db_manager.connect()

    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key

    if payload.default_model is not None:
        settings.DEFAULT_MODEL = payload.default_model

    db_status = await db_manager.check_health()
    return {
        "status": "success",
        "message": "Settings updated successfully",
        "db_mode": db_status["mode"],
        "has_gemini_key": bool(settings.GEMINI_API_KEY)
    }

# --- Voice Assistant Endpoints ---

@app.post("/api/voice/tts")
async def voice_text_to_speech(payload: VoiceTTSRequest):
    """
    Convert text to speech using gTTS (Google TTS).
    Returns base64-encoded MP3 audio data.
    """
    try:
        if not payload.text or not payload.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        mp3_bytes = await VoiceService.text_to_speech(
            text=payload.text,
            language=payload.language or "en",
            slow=payload.slow or False
        )

        audio_b64 = __import__('base64').b64encode(mp3_bytes).decode('utf-8')
        return {
            "status": "success",
            "audio": audio_b64,
            "format": "mp3",
            "language": payload.language or "en"
        }
    except RuntimeError as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Text-to-speech generation failed")


@app.post("/api/voice/stt")
async def voice_speech_to_text(payload: VoiceSTTRequest):
    """
    Transcribe audio to text using Google Web Speech API.
    Accepts base64-encoded audio (WebM/WAV/OGG).
    """
    try:
        if not payload.audio_data:
            raise HTTPException(status_code=400, detail="Audio data cannot be empty")

        transcribed = await VoiceService.speech_to_text(
            audio_data_b64=payload.audio_data,
            language=payload.language or "en-US"
        )

        return {
            "status": "success",
            "text": transcribed,
            "language": payload.language or "en-US"
        }
    except RuntimeError as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"STT unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Speech transcription failed")


# --- Authentication Endpoints ---

@app.post("/api/auth/register")
async def register(payload: UserRegister):
    """Register a new user account"""
    res = await AuthService.register_user(
        username=payload.username,
        email=payload.email,
        password=payload.password
    )
    if res["status"] == "error":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@app.post("/api/auth/login")
async def login(payload: UserLogin):
    """Login existing user account"""
    res = await AuthService.login_user(
        email_or_username=payload.email_or_username,
        password=payload.password
    )
    if res["status"] == "error":
        raise HTTPException(status_code=401, detail=res["message"])
    return res

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout current user session"""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    return await AuthService.logout_user(token)

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get active user profile details"""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    user = await AuthService.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"status": "success", "user": user}
