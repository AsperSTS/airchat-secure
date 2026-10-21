"""Operaciones de base de datos SQLite asíncronas."""

import re
import aiosqlite
from app.config import DB_PATH


async def init_db() -> None:
    """Crea las tablas necesarias si no existen."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                creator TEXT,
                target TEXT,
                title TEXT,
                is_group BOOLEAN,
                created_at TEXT,
                last_updated TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                from_user TEXT,
                to_target TEXT,
                message TEXT,
                file_data TEXT,
                file_name TEXT,
                file_type TEXT,
                timestamp TEXT,
                is_group BOOLEAN,
                reply_to INTEGER,
                reactions TEXT DEFAULT '{}'
            )
        ''')
        # Migraciones (Añadir columnas a tablas existentes si faltan)
        try:
            await db.execute("ALTER TABLE messages ADD COLUMN session_id TEXT")
        except Exception:
            pass
            
        try:
            await db.execute("ALTER TABLE messages ADD COLUMN reactions TEXT DEFAULT '{}'")
        except Exception:
            pass  # Ya existe o error
            
        await db.commit()


async def save_message(payload: dict) -> int:
    """Guarda un mensaje y retorna su ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO messages
                (session_id, from_user, to_target, message, file_data, file_name, file_type, timestamp, is_group, reply_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payload.get("session_id"),
            payload.get("from_user"),
            payload.get("to_target"),
            payload.get("message", ""),
            payload.get("file_data", ""),
            payload.get("file_name", ""),
            payload.get("file_type", ""),
            payload.get("timestamp"),
            payload.get("is_group", False),
            payload.get("reply_to", None),
        ))
        await db.commit()
        return cursor.lastrowid


async def delete_message(msg_id: int) -> None:
    """Elimina un mensaje por ID y todos los siguientes en la misma sesión si es de la IA."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT from_user, to_target, session_id FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                is_ai = row["to_target"] == "Agente IA" or row["from_user"] == "Agente IA"
                if is_ai:
                    real_user = row["from_user"] if row["to_target"] == "Agente IA" else row["to_target"]
                    if row["session_id"]:
                        await db.execute(
                            "DELETE FROM messages WHERE id >= ? AND session_id = ?", 
                            (msg_id, row["session_id"])
                        )
                    else:
                        await db.execute(
                            "DELETE FROM messages WHERE id >= ? AND ((from_user = ? AND to_target = 'Agente IA') OR (from_user = 'Agente IA' AND to_target = ?))", 
                            (msg_id, real_user, real_user)
                        )
                else:
                    await db.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        await db.commit()

async def delete_session(session_id: str) -> None:
    """Elimina una sesión entera y sus mensajes."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.commit()

async def update_message(msg_id: int, new_text: str) -> None:
    """Actualiza el texto de un mensaje y elimina los subsecuentes si es IA."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE messages SET message = ? WHERE id = ?", (new_text, msg_id))
        
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT from_user, to_target, session_id FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                is_ai = row["to_target"] == "Agente IA" or row["from_user"] == "Agente IA"
                if is_ai:
                    real_user = row["from_user"] if row["to_target"] == "Agente IA" else row["to_target"]
                    if row["session_id"]:
                        await db.execute(
                            "DELETE FROM messages WHERE id > ? AND session_id = ?", 
                            (msg_id, row["session_id"])
                        )
                    else:
                        await db.execute(
                            "DELETE FROM messages WHERE id > ? AND ((from_user = ? AND to_target = 'Agente IA') OR (from_user = 'Agente IA' AND to_target = ?))", 
                            (msg_id, real_user, real_user)
                        )
        await db.commit()

async def update_reaction(msg_id: int, user: str, reaction: str | None) -> dict:
    """Añade o remueve una reacción de un usuario en un mensaje."""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT reactions FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {}
            
            try:
                reactions = json.loads(row["reactions"]) if row["reactions"] else {}
            except Exception:
                reactions = {}
                
            if reaction:
                reactions[user] = reaction
            else:
                reactions.pop(user, None)
                
            await db.execute("UPDATE messages SET reactions = ? WHERE id = ?", (json.dumps(reactions), msg_id))
            await db.commit()
            return reactions



async def load_history(username: str, session_id: str | None = None) -> list[dict]:
    """Carga el historial de mensajes relevante para un usuario y opcionalmente por sesión."""
    rows: list[dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if session_id:
            sql = '''
                SELECT m.*, p.message AS reply_to_text, p.from_user AS reply_to_user, p.file_name AS reply_to_file
                FROM messages m
                LEFT JOIN messages p ON m.reply_to = p.id
                WHERE m.session_id = ?
                ORDER BY m.id ASC
            '''
            params = (session_id,)
        else:
            sql = '''
                SELECT m.*, p.message AS reply_to_text, p.from_user AS reply_to_user, p.file_name AS reply_to_file
                FROM messages m
                LEFT JOIN messages p ON m.reply_to = p.id
                WHERE m.to_target = ? OR m.from_user = ? OR m.is_group = 1
                ORDER BY m.id ASC
            '''
            params = (username, username)
            
        async with db.execute(sql, params) as cursor:
            import json
            async for row in cursor:
                try:
                    reactions = json.loads(row["reactions"]) if row["reactions"] else {}
                except Exception:
                    reactions = {}
                    
                rows.append({
                    "type": "file" if row["file_data"] else "chat",
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "from_user": row["from_user"],
                    "to_target": row["to_target"],
                    "message": row["message"],
                    "file_data": row["file_data"],
                    "file_name": row["file_name"],
                    "file_type": row["file_type"],
                    "timestamp": row["timestamp"],
                    "is_group": bool(row["is_group"]),
                    "reply_to": row["reply_to"],
                    "reply_to_text": row["reply_to_text"],
                    "reply_to_user": row["reply_to_user"],
                    "reply_to_file": row["reply_to_file"],
                    "reactions": reactions,
                    "is_history": True,
                })
    return rows

async def get_message_by_id(msg_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT from_user, message, file_name FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def rag_search(query: str, limit: int = 8) -> list[dict]:
    """
    RAG: Busca mensajes relevantes en la DB usando keywords.
    Retorna los `limit` resultados más recientes que coincidan.
    """
    stopwords = {
        "que", "como", "los", "las", "una", "uno", "del", "con", "por",
        "para", "sobre", "mas", "hay", "son", "fue", "era", "esto",
        "esta", "ese", "esa", "quien", "donde", "cuando", "cual",
        "todo", "todos", "muy", "bien", "mal", "algo", "nada",
        "tiene", "hacer",
    }
    words = [
        w.lower()
        for w in re.findall(r'\w+', query)
        if len(w) > 2 and w.lower() not in stopwords
    ]
    if not words:
        return []

    conditions = " OR ".join(["message LIKE ?" for _ in words])
    params: list = [f"%{w}%" for w in words]

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = f'''
            SELECT from_user, to_target, message, timestamp
            FROM messages
            WHERE ({conditions})
              AND from_user != 'Agente IA'
              AND message != ''
            ORDER BY id DESC
            LIMIT ?
        '''
        params.append(limit)
        results: list[dict] = []
        async with db.execute(sql, params) as cursor:
            async for row in cursor:
                results.append({
                    "from": row["from_user"],
                    "to": row["to_target"],
                    "msg": row["message"],
                    "time": row["timestamp"],
                })
    return results

async def create_chat_session(session_id: str, creator: str, target: str, title: str, is_group: bool = False) -> None:
    from datetime import datetime
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO chat_sessions (id, creator, target, title, is_group, created_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, creator, target, title, is_group, now, now))
        await db.commit()

async def get_chat_sessions(username: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM chat_sessions 
            WHERE creator = ? OR target = ? OR (is_group = 1 AND target = ?)
            ORDER BY last_updated DESC
        ''', (username, username, username)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_session_title(session_id: str, title: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))
        await db.commit()

async def update_session_timestamp(session_id: str) -> None:
    from datetime import datetime
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE chat_sessions SET last_updated = ? WHERE id = ?", (now, session_id))
        await db.commit()

async def get_offline_contacts(username: str) -> set[str]:
    """Obtiene todos los usuarios y grupos con los que este usuario ha interactuado."""
    contacts = set()
    async with aiosqlite.connect(DB_PATH) as db:
        # Todos a los que les envió mensaje (excepto grupos)
        async with db.execute("SELECT DISTINCT to_target FROM messages WHERE from_user = ? AND is_group = 0", (username,)) as cursor:
            async for row in cursor:
                contacts.add(row[0])
        # Todos los que le enviaron mensaje
        async with db.execute("SELECT DISTINCT from_user FROM messages WHERE to_target = ? AND is_group = 0", (username,)) as cursor:
            async for row in cursor:
                contacts.add(row[0])
        # Grupos en los que participó
        async with db.execute("SELECT DISTINCT to_target FROM messages WHERE (from_user = ? OR to_target = ?) AND is_group = 1", (username, username)) as cursor:
            async for row in cursor:
                contacts.add(row[0])
                
    contacts.discard(username)
    return contacts
