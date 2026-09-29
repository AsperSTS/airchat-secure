"""Operaciones de base de datos SQLite asíncronas."""

import re
import aiosqlite
from app.config import DB_PATH


async def init_db() -> None:
    """Crea las tablas necesarias si no existen."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT,
                to_target TEXT,
                message TEXT,
                file_data TEXT,
                file_name TEXT,
                file_type TEXT,
                timestamp TEXT,
                is_group BOOLEAN,
                reply_to INTEGER
            )
        ''')
        await db.commit()


async def save_message(payload: dict) -> int:
    """Guarda un mensaje y retorna su ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO messages
                (from_user, to_target, message, file_data, file_name, file_type, timestamp, is_group, reply_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
    """Elimina un mensaje por ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        await db.commit()


async def load_history(username: str) -> list[dict]:
    """Carga el historial de mensajes relevante para un usuario."""
    rows: list[dict] = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT * FROM messages
            WHERE to_target = ? OR from_user = ? OR is_group = 1
            ORDER BY id ASC
        ''', (username, username)) as cursor:
            async for row in cursor:
                rows.append({
                    "type": "file" if row["file_data"] else "chat",
                    "id": row["id"],
                    "from_user": row["from_user"],
                    "to_target": row["to_target"],
                    "message": row["message"],
                    "file_data": row["file_data"],
                    "file_name": row["file_name"],
                    "file_type": row["file_type"],
                    "timestamp": row["timestamp"],
                    "is_group": bool(row["is_group"]),
                    "reply_to": row["reply_to"],
                    "is_history": True,
                })
    return rows


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
