import asyncio
import os
from app.models.database import (
    init_db, save_message, get_message_by_id, update_reaction, load_history, delete_message
)
from app.config import DB_PATH

async def run_tests():
    print("Iniciando pruebas del Core...")
    await init_db()
    
    # 1. Test save_message
    msg_id = await save_message({
        "from_user": "UserA",
        "to_target": "UserB",
        "message": "Hola test",
        "session_id": "ses-123"
    })
    print(f"✅ save_message exitoso. ID: {msg_id}")
    
    # 2. Test get_message_by_id
    msg = await get_message_by_id(msg_id)
    assert msg["message"] == "Hola test"
    print("✅ get_message_by_id exitoso.")
    
    # 3. Test reactions
    await update_reaction(msg_id, "UserC", "heart")
    history = await load_history("UserA", "ses-123")
    assert history[-1]["reactions"].get("UserC") == "heart"
    print("✅ update_reaction exitoso.")
    
    print("Todas las pruebas de la BD pasaron.")

if __name__ == "__main__":
    asyncio.run(run_tests())
