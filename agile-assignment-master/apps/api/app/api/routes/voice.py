"""Voice routes — TTS synthesis endpoints.

POST /tts        Synthesise a complete answer and return base-64 audio.
POST /tts/stream Synthesise and return each audio chunk as a newline-delimited
                 JSON stream (one TTSChunk object per line).
WS   /voice      Reserved for future real-time voice transport.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.responses import StreamingResponse

from app.core.responses import not_implemented_error
from app.schemas.common import ApiError
from app.schemas.voice import (
    TTSChunk,
    TTSRequest,
    TTSResponse,
    VoiceSessionRequest,
)
from app.services.interfaces import TextToSpeechProvider
from app.services.tts import TTSError, stream_answer_chunks, synthesize_answer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


# ---------------------------------------------------------------------------
# Dependency — swap this out for a real provider in your DI layer
# ---------------------------------------------------------------------------

def get_tts_provider() -> TextToSpeechProvider:
    """Return the configured TTS provider.

    Replace the body of this function (or override via FastAPI dependency
    injection) to plug in a real provider such as OpenAI, ElevenLabs, gTTS…
    """
    raise NotImplementedError(
        "No TTS provider has been configured. "
        "Implement get_tts_provider() in the voice route or your DI setup."
    )


# ---------------------------------------------------------------------------
# POST /tts — single audio response
# ---------------------------------------------------------------------------

@router.post(
    "/tts",
    response_model=TTSResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesise answer text to audio (single response)",
)
def synthesize_tts(
    body: TTSRequest,
    provider: TextToSpeechProvider = Depends(get_tts_provider),
) -> TTSResponse:
    """Convert *body.text* to audio and return the result as base-64.

    The answer is cleaned (markdown stripped), split into TTS-safe segments,
    synthesised with automatic retry on length errors, and the audio bytes
    are concatenated into one response.
    """
    try:
        result = synthesize_answer(provider, body.text)
    except TTSError as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"TTS provider error: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected TTS error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during speech synthesis.",
        ) from exc

    return TTSResponse(
        mime_type=result.mime_type,
        audio_b64=base64.b64encode(result.audio_bytes).decode(),
        chunk_count=1,
    )


# ---------------------------------------------------------------------------
# POST /tts/stream — newline-delimited JSON stream of audio chunks
# ---------------------------------------------------------------------------

@router.post(
    "/tts/stream",
    summary="Synthesise answer text to audio (streamed chunks)",
    response_class=StreamingResponse,
)
def synthesize_tts_stream(
    body: TTSRequest,
    provider: TextToSpeechProvider = Depends(get_tts_provider),
) -> StreamingResponse:
    """Stream audio chunks as newline-delimited JSON (one TTSChunk per line).

    Each line is a JSON-serialised TTSChunk containing a base-64-encoded
    audio segment. Clients can start playing back audio before all chunks
    arrive.
    """
    def _generate():
        try:
            for index, chunk in enumerate(stream_answer_chunks(provider, body.text)):
                tts_chunk = TTSChunk(
                    index=index,
                    mime_type=chunk.mime_type,
                    audio_b64=base64.b64encode(chunk.audio_bytes).decode(),
                )
                yield tts_chunk.model_dump_json() + "\n"
        except TTSError as exc:
            logger.error("TTS stream error: %s", exc)
            yield f'{{"error": "{exc}"}}\n'
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected TTS stream error")
            yield '{"error": "Unexpected error during speech synthesis."}\n'

    return StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
    )


# ---------------------------------------------------------------------------
# Legacy session endpoint (kept for backward compatibility)
# ---------------------------------------------------------------------------

@router.post(
    "/voice",
    response_model=ApiError,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def create_voice_session(_: VoiceSessionRequest) -> ApiError:
    return not_implemented_error("Voice session creation")


# ---------------------------------------------------------------------------
# WebSocket — reserved for future real-time voice transport
# ---------------------------------------------------------------------------

@router.websocket("/voice/ws")
async def voice_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(not_implemented_error("Realtime voice transport").model_dump())
    await websocket.close(code=1011, reason="Not implemented")