"""WebSocket principal del chat en tiempo real."""

import asyncio
import json
import time
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.database import save_message, delete_message, load_history
from app.services.connection_manager import manager
from app.services.ai_engine import handle_ai_message, set_prompt, clear_memory

router = APIRouter()


async def _send_history(websocket: WebSocket, username: str) -> None:
    """Envía el historial persistido al cliente que se conecta."""
    rows = await load_history(username)
    for payload in rows:
        await websocket.send_json(payload)


@router.websocket("/ws/chat/{username}")
async def websocket_chat(websocket: WebSocket, username: str):
    """Endpoint principal de chat multiplexado."""
    await manager.connect(websocket, username)
    await manager.broadcast_user_state()
    await _send_history(websocket, username)

    try:
        while True:
            raw = await websocket.receive_text()
            parsed = json.loads(raw)
            msg_type = parsed.get("type", "chat")

            # --- Mensajes de chat, archivos y voz ---
            if msg_type in ("chat", "file", "voice"):
                to_target = parsed.get("to_target")
                is_group = to_target in manager.groups

                payload = {
                    "type": msg_type,
                    "from_user": username,
                    "to_target": to_target,
                    "message": parsed.get("message", ""),
                    "file_data": parsed.get("file_data"),
                    "file_name": parsed.get("file_name"),
                    "file_type": parsed.get("file_type"),
                    "timestamp": datetime.now().strftime("%H:%M"),
                    "is_group": is_group,
                    "reply_to": parsed.get("reply_to"),
                    "ephemeral": parsed.get("ephemeral", False),
                }

                if not payload["ephemeral"]:
                    msg_id = await save_message(payload)
                    payload["id"] = msg_id
                else:
                    payload["id"] = int(time.time() * 1000)

                if is_group:
                    await manager.send_to_group(payload, to_target, exclude_user=username)
                else:
                    await manager.send_to_user(payload, to_target)

                    # Interceptar mensajes al Agente IA
                    if to_target == "Agente IA" and msg_type == "chat":
                        asyncio.create_task(
                            handle_ai_message(username, parsed.get("message", ""))
                        )

            # --- Eliminar mensaje ---
            elif msg_type == "delete_message":
                msg_id = parsed.get("id")
                await delete_message(msg_id)
                to_target = parsed.get("to_target")
                del_payload = {"type": "delete_message", "id": msg_id, "to_target": to_target}
                if to_target in manager.groups:
                    await manager.send_to_group(del_payload, to_target)
                else:
                    await manager.send_to_user(del_payload, to_target)

            # --- Crear grupo ---
            elif msg_type == "create_group":
                group_name = parsed.get("group_name")
                members = parsed.get("members", [])
                if group_name and group_name not in manager.groups:
                    members.append(username)
                    manager.groups[group_name] = set(members)
                    await manager.broadcast_user_state()

            # --- Configurar IA ---
            elif msg_type == "update_ai_prompt":
                set_prompt(username, parsed.get("system_prompt", ""), parsed.get("user_prompt", ""))

            elif msg_type == "clear_ai_memory":
                clear_memory(username)

            # --- Indicadores de estado ---
            elif msg_type in ("typing", "stop_typing", "read_receipt"):
                to_target = parsed.get("to_target")
                if to_target not in manager.groups:
                    await manager.send_to_user(
                        {"type": msg_type, "from_user": username}, to_target
                    )

            # --- WebRTC signaling ---
            elif msg_type in ("call_offer", "call_answer", "ice_candidate", "end_call"):
                to_user = parsed.get("to_user")
                await manager.send_to_user(
                    {"type": msg_type, "from_user": username, "data": parsed.get("data")},
                    to_user,
                )

    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast_user_state()
