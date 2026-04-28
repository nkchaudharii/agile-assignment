from fastapi import APIRouter, WebSocket, status

from app.core.responses import not_implemented_error
from app.schemas.common import ApiError
from app.schemas.voice import VoiceSessionRequest

router = APIRouter(tags=["voice"])


@router.post(
    "/voice",
    response_model=ApiError,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def create_voice_session(_: VoiceSessionRequest) -> ApiError:
    return not_implemented_error("Voice session creation")


@router.websocket("/voice")
async def voice_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json(not_implemented_error("Realtime voice transport").model_dump())
    await websocket.close(code=1011, reason="Not implemented")
