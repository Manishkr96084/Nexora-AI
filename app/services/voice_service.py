"""
Voice Service - Backend TTS & STT for NEXORA AI
Handles:
  - Text-to-Speech (TTS) using gTTS (Google TTS) → returns MP3 audio
  - Speech-to-Text (STT) using SpeechRecognition library with Google Web Speech API
  - Fallback for when Gemini TTS/STT is not available
"""

import io
import base64
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("aichatbot.voice_service")


class VoiceService:

    # ─── Text-to-Speech ─────────────────────────────────────────────────────
    @staticmethod
    async def text_to_speech(text: str, language: str = "en", slow: bool = False) -> bytes:
        """
        Convert text to MP3 audio bytes using gTTS.
        Returns raw MP3 bytes.
        """
        try:
            from gtts import gTTS
        except ImportError:
            raise RuntimeError("gTTS is not installed. Run: pip install gtts")

        # Clean text: remove markdown before speaking
        clean = VoiceService._strip_markdown(text)
        if not clean.strip():
            raise ValueError("Empty text after cleaning")

        # gTTS is synchronous – run in thread to avoid blocking event loop
        def _synth():
            tts = gTTS(text=clean, lang=language, slow=slow)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()

        loop = asyncio.get_event_loop()
        mp3_bytes = await loop.run_in_executor(None, _synth)
        return mp3_bytes

    # ─── Speech-to-Text ──────────────────────────────────────────────────────
    @staticmethod
    async def speech_to_text(audio_data_b64: str, language: str = "en-US") -> str:
        """
        Transcribe base64-encoded audio (WebM/WAV/OGG) to text.
        Uses SpeechRecognition with Google Web Speech API (free tier).
        Returns transcribed text string.
        """
        if not audio_data_b64 or not audio_data_b64.strip():
            raise ValueError("audio_data cannot be empty")
        try:
            import speech_recognition as sr
        except ImportError:
            raise RuntimeError("SpeechRecognition is not installed. Run: pip install SpeechRecognition")

        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 audio data: {e}")

        def _transcribe():
            recognizer = sr.Recognizer()
            audio_file = io.BytesIO(audio_bytes)

            # Try to load as AudioFile (supports WAV, AIFF, FLAC)
            try:
                with sr.AudioFile(audio_file) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.record(source)
            except Exception:
                # If AudioFile fails (e.g. WebM), try raw AudioData
                # Convert WebM to WAV using pydub if available
                try:
                    from pydub import AudioSegment
                    audio_file.seek(0)
                    segment = AudioSegment.from_file(audio_file)
                    wav_buf = io.BytesIO()
                    segment.export(wav_buf, format="wav")
                    wav_buf.seek(0)
                    with sr.AudioFile(wav_buf) as source:
                        audio = recognizer.record(source)
                except ImportError:
                    raise RuntimeError(
                        "Cannot decode WebM audio without pydub. Run: pip install pydub"
                    )
                except Exception as conv_err:
                    raise RuntimeError(f"Audio conversion failed: {conv_err}")

            # Transcribe with Google Web Speech API
            try:
                text = recognizer.recognize_google(audio, language=language)
                return text
            except sr.UnknownValueError:
                return ""  # Silence / unclear speech
            except sr.RequestError as e:
                raise RuntimeError(f"Google Speech API request failed: {e}")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _transcribe)
        return result

    # ─── Helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove markdown formatting and convert structured text into fluid spoken sentences for TTS."""
        import re
        if not text:
            return ""

        # Remove HTML elements
        text = re.sub(r'<[^>]*>', ' ', text)
        # Convert numbered lists into natural spoken transitions
        text = re.sub(r'^\s*1\.\s+(.+)$', r'First, \1.', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*2\.\s+(.+)$', r'Second, \1.', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*3\.\s+(.+)$', r'Third, \1.', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+(.+)$', r'Also, \1.', text, flags=re.MULTILINE)
        # Convert bullet points into natural spoken transitions
        text = re.sub(r'^\s*[-*+]\s+(.+)$', r'Also, \1.', text, flags=re.MULTILINE)
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', ' I have provided the code in your chat window. ', text)
        # Remove inline code
        text = re.sub(r'`[^`]+`', ' ', text)
        # Remove images
        text = re.sub(r'!\[.*?\]\(.*?\)', ' ', text)
        # Remove links (keep text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove headings
        text = re.sub(r'#{1,6}\s+', '', text)
        # Remove bold/italic/strikethrough
        text = re.sub(r'[*_~]{1,3}([^*_~\n]+)[*_~]{1,3}', r'\1', text)
        # Remove blockquotes
        text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
        # Clean math and LaTeX notation
        text = re.sub(r'\\mathbf\{[^}]*\}', '', text)
        text = re.sub(r'\$\$', '', text)
        # Collapse multiple newlines and spaces
        text = re.sub(r'\n{2,}', '. ', text)
        text = text.replace('\n', ' ')
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

