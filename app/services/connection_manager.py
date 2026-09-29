"""Gestor de conexiones WebSocket activas."""

from fastapi import WebSocket


class ConnectionManager:
    """Administra las conexiones WebSocket de usuarios y grupos."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.groups: dict[str, set[str]] = {"Chat grupal": set()}

    async def connect(self, websocket: WebSocket, username: str) -> None:
        """Acepta y registra una nueva conexión."""
        await websocket.accept()
        self.active_connections[username] = websocket
        self.groups["Chat grupal"].add(username)

    def disconnect(self, username: str) -> None:
        """Desconecta un usuario de todas las estructuras."""
        self.active_connections.pop(username, None)
        for group in self.groups.values():
            group.discard(username)

    async def broadcast_user_state(self) -> None:
        """Envía el estado actual de usuarios y grupos a todos."""
        payload = {
            "type": "state_update",
            "users": list(self.active_connections.keys()),
            "groups": {g: list(m) for g, m in self.groups.items()},
        }
        for ws in self.active_connections.values():
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def send_to_user(self, payload: dict, to_user: str) -> None:
        """Envía un payload JSON a un usuario específico."""
        ws = self.active_connections.get(to_user)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def send_to_group(
        self, payload: dict, group_name: str, exclude_user: str | None = None
    ) -> None:
        """Envía un payload a todos los miembros de un grupo."""
        members = self.groups.get(group_name, set())
        for member in members:
            if member != exclude_user:
                await self.send_to_user(payload, member)


# Instancia global (singleton)
manager = ConnectionManager()
