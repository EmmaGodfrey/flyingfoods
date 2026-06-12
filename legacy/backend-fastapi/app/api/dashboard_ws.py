"""WebSocket endpoint for live branch dashboard updates."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, WebSocketException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.websockets import get_dashboard_ws_manager
from app.db.models import User
from app.db.session import get_db
from app.services.security import decode_token

router = APIRouter(tags=["dashboard_ws"])


async def get_websocket_user(websocket: WebSocket, session: AsyncSession = Depends(get_db)) -> User:
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing access token")

    try:
        payload = decode_token(token, settings)
    except Exception as exc:  # noqa: BLE001
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid access token") from exc

    if payload.get("type") != "access":
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token type")

    user_id = payload.get("sub")
    if user_id is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token subject")

    user = (await session.execute(select(User).where(User.id == int(user_id)))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
    return user


@router.websocket("/ws/dashboard")
async def dashboard_websocket_endpoint(websocket: WebSocket, current_user: User = Depends(get_websocket_user)) -> None:
    manager = get_dashboard_ws_manager()
    branch_id = int(current_user.branch_id)
    await manager.connect(branch_id, websocket)
    await websocket.send_json({"type": "connection", "status": "connected", "branch_id": branch_id})

    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            if message.lower() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(branch_id, websocket)
    except Exception:  # noqa: BLE001
        await manager.disconnect(branch_id, websocket)
