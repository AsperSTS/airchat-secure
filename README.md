# AirChat Secure

Chat privado en tiempo real con cifrado de extremo a extremo (E2EE), inteligencia artificial local y sistema RAG.

## Estructura del proyecto

```
.
├── main.py                     # Punto de entrada (app factory)
├── app/
│   ├── __init__.py
│   ├── config.py               # Configuración centralizada
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py         # Capa de datos (SQLite async)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── pages.py            # Rutas HTTP
│   │   ├── metrics.py          # WebSocket de métricas
│   │   └── chat.py             # WebSocket principal del chat
│   └── services/
│       ├── __init__.py
│       ├── connection_manager.py  # Gestor de conexiones WS
│       └── ai_engine.py        # Motor LLM local + RAG
├── templates/
│   └── index.html              # Frontend (HTML/JS/Tailwind)
├── static/
│   ├── manifest.json           # PWA manifest
│   └── sw.js                   # Service Worker
├── backup_v1/                  # Código legacy (referencia)
├── requirements.txt
├── environment.yml
└── .gitignore
```

## Arquitectura

- **Backend:** FastAPI + WebSockets (async).
- **Frontend:** HTML5 + Tailwind CSS + Vanilla JS.
- **Base de datos:** SQLite via aiosqlite.
- **Cifrado:** AES-256-GCM client-side (WebCrypto API). El servidor solo almacena texto cifrado.
- **IA Local:** HuggingFace Transformers (SmolLM-135M-Instruct) corriendo en CPU.
- **RAG:** Búsqueda por keywords en SQLite, inyección de contexto en el prompt del LLM.
- **Llamadas:** WebRTC peer-to-peer con signaling via WebSockets.

## Requisitos

- Python 3.12+
- Conda (entorno `python314_Demos`) o pip

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Acceder desde el navegador en `http://localhost:8000` o `http://<IP_LOCAL>:8000` desde otro dispositivo en la misma red.

## Funcionalidades

- Chat en tiempo real (1:1 y grupos)
- Cifrado E2EE (AES-256-GCM, derivación PBKDF2)
- Videollamadas y compartir pantalla (WebRTC)
- Notas de voz
- Archivos adjuntos con compresión de imágenes
- Mensajes efímeros (auto-destrucción a los 10 segundos)
- Eliminación remota de mensajes
- IA local sin censura con memoria conversacional
- RAG (búsqueda en historial con comando `/rag`)
- Roles/presets de personalidad para la IA
- Indicadores de escritura y confirmación de lectura
- Métricas en vivo (CPU, RAM, red, uptime)
- Modo oscuro
- PWA (instalable en móvil)

## Comandos de IA

| Comando | Descripción |
|---|---|
| `/rag [pregunta]` | Busca en el historial y responde con contexto |
| `/rolear [escenario]` | Inicia un roleplay |
| `/historia [tema]` | Genera una historia creativa |
| `/codigo [lenguaje] [tarea]` | Genera código |
