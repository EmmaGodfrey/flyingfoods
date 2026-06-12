"""Branch-scoped WebSocket connection manager for live dashboard events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class DashboardWebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, branch_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[branch_id].add(websocket)

    async def disconnect(self, branch_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(branch_id)
            if sockets is None:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(branch_id, None)

    async def broadcast_to_branch(self, branch_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(branch_id, set()))

        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:  # noqa: BLE001
                stale.append(socket)

        if stale:
            async with self._lock:
                current = self._connections.get(branch_id, set())
                for socket in stale:
                    current.discard(socket)
                if not current:
                    self._connections.pop(branch_id, None)


_dashboard_ws_manager: DashboardWebSocketManager | None = None


def get_dashboard_ws_manager() -> DashboardWebSocketManager:
    global _dashboard_ws_manager
    if _dashboard_ws_manager is None:
        _dashboard_ws_manager = DashboardWebSocketManager()
    return _dashboard_ws_manager
