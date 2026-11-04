import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from backend.app.schemas.live import (
    LiveFrameRequest,
    LivePoseState,
    LiveAttemptFeedback,
    LiveAttemptPayload,
    LiveSessionSummary,
)
from backend.app.services.live_coach_service import live_coach_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["Live Batting Coach"])

@router.post("/process-frame", response_model=LivePoseState)
def process_live_frame(payload: LiveFrameRequest):
    img = live_coach_service.decode_base64_image(payload.image_base64)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    session_id = payload.session_id or "default_live_session"
    res = live_coach_service.process_live_frame(
        session_id=session_id,
        image_bgr=img,
        timestamp_ms=payload.timestamp_ms,
        handedness=payload.handedness,
        shot_hint=payload.shot_hint or "Cover Drive",
        manual_trigger=payload.manual_trigger
    )
    return res

@router.post("/analyze-attempt", response_model=LiveAttemptFeedback)
def analyze_attempt(payload: LiveAttemptPayload):
    frames_dict = [f.model_dump() for f in payload.frames]
    feedback = live_coach_service.analyze_completed_attempt(
        session_id=payload.session_id,
        shot_type=payload.shot_type,
        handedness=payload.handedness,
        camera_angle=payload.camera_angle,
        provided_frames=frames_dict,
        video_base64=payload.video_base64
    )
    return feedback

@router.get("/session/{session_id}/attempts", response_model=List[LiveAttemptFeedback])
def get_session_attempts(session_id: str):
    sess = live_coach_service.get_or_create_session(session_id)
    return sess.completed_attempts

@router.websocket("/ws/{session_id}")
async def live_stream_websocket(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket stream for ultra-low latency live camera tracking.
    Client sends JSON packets: { image_base64, timestamp_ms, handedness, shot_hint, manual_trigger }
    Server replies with LivePoseState or LiveAttemptFeedback.
    """
    await websocket.accept()
    sess = live_coach_service.get_or_create_session(session_id)
    logger.info(f"WebSocket client connected for live session {session_id}")

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            action = data.get("action", "frame")

            if action == "frame":
                b64 = data.get("image_base64", "")
                ts = data.get("timestamp_ms", 0.0)
                handedness = data.get("handedness", "Right")
                shot_hint = data.get("shot_hint", "Cover Drive")
                manual = data.get("manual_trigger")

                img = live_coach_service.decode_base64_image(b64)
                if img is not None:
                    pose_state = live_coach_service.process_live_frame(
                        session_id=session_id,
                        image_bgr=img,
                        timestamp_ms=ts,
                        handedness=handedness,
                        shot_hint=shot_hint,
                        manual_trigger=manual
                    )
                    
                    # If shot just completed automatically, generate feedback immediately!
                    if pose_state.state == "shot_completed":
                        feedback = live_coach_service.analyze_completed_attempt(
                            session_id=session_id,
                            shot_type=shot_hint,
                            handedness=handedness
                        )
                        await websocket.send_text(json.dumps({
                            "type": "attempt_feedback",
                            "data": feedback.model_dump()
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "pose_state",
                            "data": pose_state.model_dump()
                        }))

            elif action == "analyze_now":
                shot_hint = data.get("shot_hint", "Cover Drive")
                handedness = data.get("handedness", "Right")
                feedback = live_coach_service.analyze_completed_attempt(
                    session_id=session_id,
                    shot_type=shot_hint,
                    handedness=handedness
                )
                await websocket.send_text(json.dumps({
                    "type": "attempt_feedback",
                    "data": feedback.model_dump()
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
