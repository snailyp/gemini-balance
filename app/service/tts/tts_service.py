import datetime
import io
import re
import time
import wave
from typing import Optional

from google import genai

from app.config.config import settings
from app.core.constants import TTS_VOICE_NAMES
from app.database.services import add_error_log, add_request_log
from app.domain.openai_models import TTSRequest
from app.log.logger import get_openai_logger

logger = get_openai_logger()


def _create_wav_file(audio_data: bytes) -> bytes:
    """Creates a WAV file in memory from raw audio data."""
    with io.BytesIO() as wav_file:
        with wave.open(wav_file, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(24000)  # 24kHz sample rate
            wf.writeframes(audio_data)
        return wav_file.getvalue()


class TTSService:
    async def create_tts(self, request: TTSRequest, api_key: str) -> Optional[bytes]:
        """
        使用 Google Gemini SDK 创建音频。
        """
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None
        response = None
        error_log_msg = ""
        try:
            client = genai.Client(api_key=api_key)
            response =await client.aio.models.generate_content(
                model=settings.TTS_MODEL,
                contents=f"Speak in a {settings.TTS_SPEED} speed voice: {request.input}",
                config={
                    "response_modalities": ["Audio"],
                    "speech_config": {
                        "voice_config": {
                            "prebuilt_voice_config": {
                                "voice_name": request.voice if request.voice in TTS_VOICE_NAMES else settings.TTS_VOICE_NAME
                            }
                        }
                    },
                },
            )
            if (
                response.candidates
                and response.candidates[0].content.parts
                and response.candidates[0].content.parts[0].inline_data
            ):
                raw_audio_data = response.candidates[0].content.parts[0].inline_data.data
                is_success = True
                status_code = 200
                return _create_wav_file(raw_audio_data)
        except Exception as e:
            is_success = False
            error_log_msg = f"Generic error: {e}"
            logger.error(f"An error occurred in TTSService: {error_log_msg}")
            match = re.search(r"status code (\d+)", str(e))
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500
            raise
        finally:
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)
            if not is_success:
                await add_error_log(
                    gemini_key=api_key,
                    model_name=settings.TTS_MODEL,
                    error_type="google-tts",
                    error_log=error_log_msg,
                    error_code=status_code,
                    request_msg=request.input
                 )
            await add_request_log(
                model_name=settings.TTS_MODEL,
                api_key=api_key,
                is_success=is_success,
                status_code=status_code,
                latency_ms=latency_ms,
                request_time=request_datetime
            )