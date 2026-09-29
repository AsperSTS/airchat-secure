"""Configuración centralizada de la aplicación."""

import os
import time
import psutil

# --- Rutas ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(BASE_DIR, "chat.db")

# --- Métricas del proceso ---
START_TIME = time.time()
PROCESS = psutil.Process(os.getpid())

# --- Modelo de IA ---
AI_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
AI_MAX_TOKENS = 300
AI_TEMPERATURE = 0.7
AI_MEMORY_LIMIT = 20  # Max exchanges kept in memory per user
AI_MEMORY_TRIM = 12   # Trim to this when limit is reached
