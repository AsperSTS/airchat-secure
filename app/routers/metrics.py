"""WebSocket de métricas del sistema en tiempo real."""

import os
import asyncio
import time
import socket

import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import START_TIME, PROCESS
from app.services.ai_engine import is_ready as ai_is_ready

router = APIRouter()

_last_net_io = psutil.net_io_counters()
_last_net_time = time.time()


def _format_bytes(size: float) -> str:
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB/s"
    return f"{size / (1024 * 1024):.1f} MB/s"


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """Envía métricas del proceso cada segundo."""
    await websocket.accept()
    global _last_net_io, _last_net_time
    try:
        while True:
            now = time.time()
            app_cpu = PROCESS.cpu_percent()
            app_ram = PROCESS.memory_info().rss / (1024 * 1024)

            try:
                load1, load5, load15 = os.getloadavg()
            except AttributeError:
                load1 = load5 = load15 = 0.0

            net = psutil.net_io_counters()
            dt = now - _last_net_time
            up = (net.bytes_sent - _last_net_io.bytes_sent) / dt if dt > 0 else 0
            down = (net.bytes_recv - _last_net_io.bytes_recv) / dt if dt > 0 else 0
            _last_net_io = net
            _last_net_time = now

            uptime = int(now - START_TIME)
            uptime_str = f"{uptime // 3600:02d}:{(uptime % 3600) // 60:02d}:{uptime % 60:02d}"

            await websocket.send_json({
                "app_cpu": f"{app_cpu:.1f}%",
                "app_ram": f"{app_ram:.1f} MB",
                "server_load": f"{load1:.2f}, {load5:.2f}, {load15:.2f}",
                "uptime": uptime_str,
                "ip": _get_local_ip(),
                "upload": _format_bytes(up),
                "download": _format_bytes(down),
                "ai_ready": ai_is_ready(),
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


from pydantic import BaseModel
from app.services.ai_engine import change_model

class ModelChangeRequest(BaseModel):
    model_name: str

@router.get("/api/hardware")
async def get_hardware_info():
    """Detecta el hardware y valida dinámicamente modelos con métricas reales."""
    import platform
    import psutil
    import torch
    import os

    os_name = platform.system()
    arch = platform.machine()
    ram_gb = psutil.virtual_memory().total / (1024**3)
    
    gpu_name = "CPU Only (Sin GPU Dedicada)"
    vram_gb = 0
    has_mps = False
    has_cuda = False
    
    if torch.cuda.is_available():
        has_cuda = True
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    elif torch.backends.mps.is_available():
        has_mps = True
        gpu_name = "Apple Silicon GPU (MPS)"
        vram_gb = ram_gb  # Unified memory
    
    def is_cached(model_name: str) -> bool:
        folder_name = "models--" + model_name.replace("/", "--")
        cache_path = os.path.expanduser(f"~/.cache/huggingface/hub/{folder_name}")
        if os.path.exists(cache_path):
            snaps = os.path.join(cache_path, "snapshots")
            if os.path.exists(snaps) and os.listdir(snaps):
                return True
        return False

    base_models = [
        {"name": "HuggingFaceTB/SmolLM-135M-Instruct", "size_b": 0.135, "desc": "Básico y veloz, pero poco coherente en español."},
        {"name": "Qwen/Qwen2.5-0.5B-Instruct", "size_b": 0.5, "desc": "Súper rápido. Ideal para pruebas y roleplay básico."},
        {"name": "meta-llama/Llama-3.2-1B-Instruct", "size_b": 1.0, "desc": "Equilibrio ideal entre velocidad y coherencia."},
        {"name": "Qwen/Qwen2.5-3B-Instruct", "size_b": 3.0, "desc": "Excelente para razonamiento lógico y programación."},
        {"name": "meta-llama/Meta-Llama-3.1-8B-Instruct", "size_b": 8.0, "desc": "Modelo muy inteligente, requiere bastante memoria libre."},
        {"name": "Qwen/Qwen2.5-7B-Instruct", "size_b": 7.0, "desc": "Nivel profesional, excelente multilingüe y de rol profundo."},
        {"name": "Qwen/Qwen2.5-14B-Instruct", "size_b": 14.0, "desc": "Gama alta, requiere hardware potente."}
    ]

    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.exists(cache_dir):
        for d in os.listdir(cache_dir):
            if d.startswith("models--"):
                parts = d.split("--")
                if len(parts) >= 3:
                    repo_id = "/".join(parts[1:])
                    if not any(m["name"] == repo_id for m in base_models):
                        # Inferir tamaño aproximado por el nombre
                        guessed = 7.0
                        if "0.5B" in repo_id: guessed = 0.5
                        elif "1B" in repo_id: guessed = 1.0
                        elif "1.5B" in repo_id: guessed = 1.5
                        elif "3B" in repo_id: guessed = 3.0
                        elif "8B" in repo_id: guessed = 8.0
                        elif "14B" in repo_id: guessed = 14.0
                        elif "32B" in repo_id: guessed = 32.0
                        elif "70B" in repo_id: guessed = 70.0
                        
                        base_models.append({
                            "name": repo_id,
                            "size_b": guessed,
                            "desc": "Detectado localmente en tu sistema.",
                        })

    for m in base_models:
        m["is_downloaded"] = is_cached(m["name"])
        
        # Memoria FP16 estimada (aprox 2 bytes por parámetro) + 1.5GB overhead de KV Cache base
        est_mem = (m["size_b"] * 2) + 1.5
        m["est_mem_gb"] = round(est_mem, 1)

        # Validación Avanzada de Hardware
        if has_mps: # Apple Silicon
            if ram_gb >= est_mem + 3:
                m["compat"] = {"level": "optimo", "label": "🟢 Óptimo (MPS)", "msg": "Fluidez total en Neural Engine."}
            elif ram_gb >= est_mem:
                m["compat"] = {"level": "aceptable", "label": "🟡 Justo (Unificado)", "msg": "Correrá, pero consumirás casi toda tu RAM."}
            else:
                m["compat"] = {"level": "critico", "label": "🔴 Peligro (Swap)", "msg": "Paging a disco duro. Sistema se congelará."}
        elif has_cuda: # NVIDIA GPU
            if vram_gb >= est_mem:
                m["compat"] = {"level": "optimo", "label": "🟢 Óptimo (VRAM)", "msg": "Cabe perfectamente en tu GPU."}
            elif ram_gb >= est_mem + 2:
                m["compat"] = {"level": "aceptable", "label": "🟡 Offload a RAM", "msg": "Lento. Solo parte del modelo irá en la GPU."}
            else:
                m["compat"] = {"level": "critico", "label": "🔴 Imposible", "msg": "Ni tu RAM ni VRAM soportan este modelo."}
        else: # CPU ONLY
            if ram_gb >= est_mem + 2:
                m["compat"] = {"level": "aceptable", "label": "🟡 CPU Only", "msg": "Correrá usando CPU, será bastante lento."}
            else:
                m["compat"] = {"level": "critico", "label": "🔴 Insuficiente", "msg": "Provocará Crash o Swap masivo."}

    return {
        "hardware": {
            "os": os_name,
            "arch": arch,
            "ram_gb": round(ram_gb, 1),
            "gpu": gpu_name,
            "vram_gb": round(vram_gb, 1) if vram_gb else 0,
        },
        "recommended_models": sorted(base_models, key=lambda x: x["size_b"])
    }

@router.post("/api/model")
async def api_change_model(req: ModelChangeRequest):
    """Trigger the hot-swap of the LLM model."""
    change_model(req.model_name)
    return {"status": "loading", "message": f"Cambiando a {req.model_name}..."}

