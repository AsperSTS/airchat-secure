# AirChat Secure

Chat privado en tiempo real con cifrado de extremo a extremo (E2EE), agente de inteligencia artificial local y sistema RAG. Proyecto de redes del 5º semestre (BUAP), evolucionado desde la versión original basada en sockets TCP/UDP (`backup_v1/`) a una app web moderna en tiempo real.

## Arquitectura

- **Backend:** Python + FastAPI (app factory, async).
- **Tiempo real:** WebSockets — `/ws/chat/{usuario}` para el chat y `/ws/metrics` para métricas del sistema (psutil).
- **Base de datos:** SQLite vía `aiosqlite` (`chat.db`; sesiones y mensajes).
- **Frontend:** HTML5 + Tailwind CSS + Vanilla JS, con PWA (manifest + service worker) instalable en móvil.
- **Cifrado:** AES-256-GCM en el cliente (WebCrypto API) con derivación de claves PBKDF2. *Nota: se trata de un proyecto educativo; el servidor conserva copia del flujo entrante y no hay autenticación, por lo que no debe considerarse producción.*
- **IA local:** LLM de HuggingFace Transformers corriendo en CPU (`Qwen/Qwen2.5-0.5B-Instruct`), sin censura, con ventana de memoria conversacional, seudollamadas a herramientas (`<tool:calc>`, `<tool:time>`) y RAG por palabras clave sobre el historial en SQLite.

## Requisitos

- Python 3.12+
- pip o Conda (`environment.yml`, entorno `chat_tcp_udp_modern`)

## Instalación y ejecución

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Abre `http://localhost:8000`, o `http://<IP_LOCAL>:8000` desde otro dispositivo en la misma red. En Windows también funciona `start.bat`.

## Funcionalidades

- Chat en tiempo real 1:1 y grupal
- Cifrado E2EE en el cliente (AES-256-GCM)
- Videollamadas y pantalla compartida (WebRTC signaling)
- IA local con memoria, roles/personalidades y RAG (`/rag`)
- Mensajes efímeros (autodestrucción en 10 s), edición y borrado remoto
- Reacciones, respuestas, indicador de escritura y confirmación de lectura
- Notas de voz y archivos adjuntos con compresión de imágenes
- Sesiones de chat (crear, renombrar, cargar, eliminar) y contactos offline
- Métricas en vivo (CPU, RAM, red, uptime) vía WebSocket
- Modo oscuro y PWA instalable

## Comandos de IA

| Comando | Descripción |
|---|---|
| `/rag [pregunta]` | Busca en el historial y responde con contexto |
| `/rolear [escenario]` | Inicia un roleplay |
| `/historia [tema]` | Genera una historia creativa |
| `/codigo [tarea]` | Genera código |

## Estructura

```
.
├── main.py                  # Punto de entrada (app factory)
├── app/
│   ├── config.py            # Configuración centralizada
│   ├── models/database.py   # Capa de datos (SQLite async)
│   ├── routers/             # Rutas HTTP y WebSockets
│   └── services/            # Gestor de conexiones y motor LLM
├── templates/index.html     # Frontend (HTML/Tailwind/JS)
├── static/                  # PWA (manifest + service worker)
└── backup_v1/               # Versión legacy TCP/UDP (referencia)
```

## English Version

AirChat Secure is a private real-time chat with end-to-end encryption (E2EE), a local AI agent, and RAG over chat history. Originally a 5th-semester BUAP networking project built with TCP/UDP sockets, it evolved (`backup_v1/` keeps the legacy version) into a modern real-time web app.

- **Stack:** FastAPI + WebSockets backend, SQLite (aiosqlite) persistence, HTML5 + Tailwind + vanilla JS frontend, installable PWA.
- **Encryption:** client-side AES-256-GCM via WebCrypto with PBKDF2 key derivation. *Educational project: no authentication; not production-grade.*
- **Local AI:** uncensored HuggingFace LLM (`Qwen/Qwen2.5-0.5B-Instruct`) on CPU, with conversation memory, pseudo tool-calling, and keyword-based RAG over stored history.
- **Features:** 1:1 and group chat, WebRTC video/screen calls, ephemeral messages, remote edit/delete, reactions and read receipts, voice notes and attachments, chat sessions, live system metrics (CPU/RAM/network) over WebSocket, dark mode.

### Run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000` (or `http://<LOCAL_IP>:8000` from other devices on the LAN). AI commands: `/rag`, `/rolear`, `/historia`, `/codigo`.
