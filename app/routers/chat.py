"""WebSocket principal del chat en tiempo real."""

import asyncio
import json
import time
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.database import (
    save_message, delete_message, load_history, update_message, 
    get_chat_sessions, create_chat_session, update_session_title, delete_session,
    update_reaction, get_message_by_id
)
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
    
    from app.models.database import get_offline_contacts
    offline = await get_offline_contacts(username)
    await websocket.send_json({"type": "offline_contacts", "contacts": list(offline)})
    
    sessions = await get_chat_sessions(username)
    await websocket.send_json({"type": "chat_sessions", "sessions": sessions})
    
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
                session_id = parsed.get("session_id")

                payload = {
                    "type": msg_type,
                    "session_id": session_id,
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
                    if session_id:
                        from app.models.database import update_session_timestamp
                        await update_session_timestamp(session_id)
                else:
                    payload["id"] = int(time.time() * 1000)
                    
                if payload.get("reply_to"):
                    reply_msg = await get_message_by_id(payload["reply_to"])
                    if reply_msg:
                        payload["reply_to_user"] = reply_msg["from_user"]
                        payload["reply_to_text"] = reply_msg["message"]
                        payload["reply_to_file"] = reply_msg["file_name"]
                        

                if is_group:
                    await manager.send_to_group(payload, to_target, exclude_user=username)
                else:
                    await manager.send_to_user(payload, to_target)

                    # Interceptar mensajes al Agente IA
                    if to_target == "Agente IA" and msg_type in ("chat", "file"):
                        msg_text = parsed.get("message", "")
                        if msg_type == "file":
                            file_data = parsed.get("file_data", "")
                            file_name = parsed.get("file_name", "")
                            file_type = parsed.get("file_type", "")
                            file_text = ""
                            
                            if "text" in file_type or "json" in file_type or file_name.endswith(('.py', '.js', '.md', '.txt', '.csv')):
                                if ";base64," in file_data:
                                    import base64
                                    try:
                                        b64 = file_data.split(";base64,")[1]
                                        file_text = base64.b64decode(b64).decode('utf-8', errors='ignore')
                                    except Exception:
                                        pass
                                msg_text = f"[Contenido del archivo {file_name}]:\n{file_text}"
                            else:
                                msg_text = f"[Archivo/Imagen subido: {file_name}] (El contenido binario ha sido omitido)"
                            
                        asyncio.create_task(
                            handle_ai_message(username, msg_text, session_id=session_id)
                        )

            # --- Eliminar mensaje ---
            elif msg_type == "delete_message":
                msg_id = parsed.get("id")
                await delete_message(msg_id)
                to_target = parsed.get("to_target")
                del_payload = {"type": "delete_message", "id": msg_id, "to_target": to_target, "from_user": username}
                if to_target in manager.groups:
                    await manager.send_to_group(del_payload, to_target)
                else:
                    await manager.send_to_user(del_payload, to_target)

            # --- Editar mensaje ---
            elif msg_type == "edit_message":
                msg_id = parsed.get("id")
                new_text = parsed.get("new_text")
                to_target = parsed.get("to_target")
                session_id = parsed.get("session_id")
                await update_message(msg_id, new_text)
                
                edit_payload = {"type": "edit_message", "id": msg_id, "new_text": new_text, "to_target": to_target, "from_user": username}
                if to_target in manager.groups:
                    await manager.send_to_group(edit_payload, to_target)
                else:
                    await manager.send_to_user(edit_payload, to_target)
                
                # If editing a message sent TO the AI, trigger generation again!
                if to_target == "Agente IA":
                    asyncio.create_task(handle_ai_message(username, new_text, session_id=session_id))

            # --- Reactions ---
            elif msg_type == "react_message":
                msg_id = parsed.get("id")
                reaction = parsed.get("reaction")  # string name like 'like', 'heart' or None to remove
                to_target = parsed.get("to_target")
                session_id = parsed.get("session_id")
                
                updated_reactions = await update_reaction(msg_id, username, reaction)
                
                react_payload = {
                    "type": "reaction_updated",
                    "id": msg_id,
                    "session_id": session_id,
                    "reactions": updated_reactions,
                    "to_target": to_target
                }
                if to_target in manager.groups:
                    await manager.send_to_group(react_payload, to_target)
                else:
                    await manager.send_to_user(react_payload, to_target)
                    # if I react to my own message in a 1-to-1 chat, the other person needs it. Wait, the to_target is the currentChat! So we send to the currentChat. But we also want the sender to receive it if they need confirmation, but they already updated locally. 
                    # Actually, we should send it to both or just to_target since the sender has it.
                    # Send to myself too to ensure sync if I am on multiple devices.
                    await manager.send_to_user(react_payload, username)

            # --- Chat Sessions ---
            elif msg_type == "create_session":
                import uuid
                session_id = str(uuid.uuid4())
                target = parsed.get("target", "Agente IA")
                title = parsed.get("title", "Nuevo Chat")
                is_group = target in manager.groups
                
                await create_chat_session(session_id, username, target, title, is_group)
                
                sessions = await get_chat_sessions(username)
                await websocket.send_json({"type": "chat_sessions", "sessions": sessions})
                # Auto-select on UI
                await websocket.send_json({"type": "session_created", "session_id": session_id})
                
            elif msg_type == "delete_session":
                session_id = parsed.get("session_id")
                await delete_session(session_id)
                sessions = await get_chat_sessions(username)
                await websocket.send_json({"type": "chat_sessions", "sessions": sessions})
                
            elif msg_type == "rename_session":
                session_id = parsed.get("session_id")
                new_title = parsed.get("title")
                await update_session_title(session_id, new_title)
                sessions = await get_chat_sessions(username)
                await websocket.send_json({"type": "chat_sessions", "sessions": sessions})
                
            elif msg_type == "load_session":
                session_id = parsed.get("session_id")
                # Enviar historial solo para esta sesión
                rows = await load_history(username, session_id)
                await websocket.send_json({"type": "session_history", "session_id": session_id, "messages": rows})

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
                asyncio.create_task(
                    handle_ai_message(username, "¡El rol ha sido actualizado! Haz tu primera acción o saludo presentándote in-character ahora.")
                )
                
            elif msg_type == "update_ai_settings":
                from app.services.ai_engine import update_ai_settings
                update_ai_settings(username, parsed.get("config", {}))

            elif msg_type == "clear_ai_memory":
                clear_memory(username)
                
            elif msg_type == "get_cached_models":
                import os
                hf_cache = os.path.expanduser('~/.cache/huggingface/hub')
                models = []
                if os.path.exists(hf_cache):
                    for folder in os.listdir(hf_cache):
                        if folder.startswith("models--"):
                            model_name = folder.replace("models--", "").replace("--", "/")
                            size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(os.path.join(hf_cache, folder)) for filename in filenames)
                            models.append({"name": model_name, "size": f"{size / (1024**3):.2f} GB"})
                await manager.send_to_user({"type": "cached_models", "models": models}, username)
                
            elif msg_type == "delete_cached_model":
                import os
                import shutil
                model_name = parsed.get("model_name", "").replace("/", "--")
                if model_name:
                    target_folder = os.path.expanduser(f'~/.cache/huggingface/hub/models--{model_name}')
                    if os.path.exists(target_folder):
                        try:
                            shutil.rmtree(target_folder)
                            await manager.send_to_user({"type": "system_message", "message": f"Modelo {model_name} eliminado del disco."}, username)
                        except Exception as e:
                            await manager.send_to_user({"type": "system_message", "message": f"Error eliminando modelo: {e}"}, username)

            # --- Indicadores de estado ---
            elif msg_type in ("typing", "stop_typing", "read_receipt"):
                to_target = parsed.get("to_target")
                if to_target not in manager.groups:
                    await manager.send_to_user(
                        {"type": msg_type, "from_user": username}, to_target
                    )

            # --- WebRTC signaling ---
            elif msg_type in ("call_offer", "call_answer", "ice_candidate", "end_call", "p2p_file_offer", "p2p_file_answer", "p2p_file_ice"):
                to_user = parsed.get("to_user")
                payload_to_send = {"type": msg_type, "from_user": username, "data": parsed.get("data")}
                if msg_type == "p2p_file_offer":
                    payload_to_send["file_metadata"] = parsed.get("file_metadata")
                await manager.send_to_user(payload_to_send, to_user)

    except WebSocketDisconnect:
        manager.disconnect(username)
        await manager.broadcast_user_state()
