"""
main.py — Servidor de desenvolvimento local
════════════════════════════════════════════
Serve o frontend estático para desenvolvimento local.
Gera config.js automaticamente a partir do .env local,
eliminando a necessidade de editar o arquivo manualmente.

⚠️  APENAS PARA USO LOCAL — este arquivo NÃO é usado na Vercel.
    O deploy na Vercel é 100% estático via outputDirectory: frontend.

Uso:
    # Instale as deps mínimas (uma vez):
    pip install fastapi uvicorn[standard] python-dotenv

    # Rode o servidor:
    python main.py
    # ou com reload automático:
    uvicorn main:app --reload --port 8000
"""

import os
import re
import asyncio
import socket
import platform
import subprocess
import ipaddress
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()  # lê .env se existir

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

app = FastAPI(
    title="GerenciadorTI — Dev Server",
    description="Servidor local de desenvolvimento. Use a Vercel para produção.",
    version="local",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/config.js", include_in_schema=False)
async def serve_config():
    """
    Gera config.js em tempo real com as credenciais do .env local.
    Assim você nunca precisa editar frontend/config.js manualmente.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("[⚠️  config.js] SUPABASE_URL ou SUPABASE_ANON_KEY não definidos no .env")
    content = (
        "// Gerado pelo servidor local (main.py) — não edite manualmente.\n"
        f"window.SUPABASE_URL = '{url}';\n"
        f"window.SUPABASE_KEY = '{key}';\n"
    )
    return Response(content=content, media_type="application/javascript")


_SUBNET_RE = re.compile(r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$')


@app.get("/api/scan-network")
async def scan_network(
    subnet: str = Query(default="192.168.1.0/24", description="CIDR da rede a escanear"),
):
    """
    Scan ARP da rede local via scapy.
    ⚠️  Apenas para uso local — requer scapy + Npcap (Windows) ou libpcap (Linux/macOS).
    """
    subnet = subnet.strip()
    if not _SUBNET_RE.match(subnet):
        return JSONResponse(
            {"error": "Formato inválido. Use ex: 192.168.1.0/24"},
            status_code=400,
        )

    try:
        from scapy.all import ARP, Ether, srp  # importação diferida: scapy é pesado
    except ImportError:
        return JSONResponse(
            {
                "error": "scapy não instalado.",
                "hint": "Execute: pip install scapy  (e Npcap no Windows)",
            },
            status_code=503,
        )

    def _do_scan() -> list[dict]:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=subnet)
        answered, _ = srp(pkt, timeout=2, verbose=0, retry=0)
        results = []
        for _, rcv in answered:
            hostname = None
            try:
                hostname = socket.gethostbyaddr(rcv.psrc)[0]
            except Exception:
                pass
            results.append({
                "ip":       rcv.psrc,
                "mac":      rcv.hwsrc.lower(),
                "hostname": hostname,
            })
        results.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])
        return results

    try:
        devices = await asyncio.get_event_loop().run_in_executor(None, _do_scan)
        return {"subnet": subnet, "count": len(devices), "devices": devices}
    except PermissionError:
        return JSONResponse(
            {
                "error": "Permissão negada para enviar pacotes ARP raw.",
                "hint": "Windows: execute o terminal como Administrador. Linux/macOS: use sudo.",
            },
            status_code=403,
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/ping")
async def ping_host(
    ip: str = Query(..., description="IP ou hostname a verificar via ICMP"),
):
    """
    Verifica se um host responde a ping ICMP via subprocess.
    Não requer privilégios de administrador — use para monitoramento local.
    """
    target = ip.strip()

    # Validação básica: aceita IP ou hostname simples
    is_valid_ip = False
    try:
        ipaddress.ip_address(target)
        is_valid_ip = True
    except ValueError:
        pass

    if not is_valid_ip and not re.match(r'^[a-zA-Z0-9._-]{1,253}$', target):
        return JSONResponse({"error": "IP ou hostname inválido."}, status_code=400)

    def _do_ping(host: str) -> bool:
        try:
            if platform.system() == "Windows":
                cmd = ["ping", "-n", "1", "-w", "1500", host]
            else:
                cmd = ["ping", "-c", "1", "-W", "2", host]
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    try:
        online = await asyncio.get_event_loop().run_in_executor(None, _do_ping, target)
        return {"ip": target, "online": online}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Serve arquivos estáticos; fallback para index.html (SPA)."""
    target = os.path.normpath(os.path.join(FRONTEND_DIR, full_path))
    # Proteção contra path traversal
    if not target.startswith(os.path.abspath(FRONTEND_DIR)):
        return Response(status_code=403)
    if os.path.isfile(target):
        return FileResponse(target)
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"\n  GerenciadorTI — Dev Server")
    print(f"  http://localhost:{port}")
    print(f"  SUPABASE_URL definida: {'✅' if os.getenv('SUPABASE_URL') else '❌  (configure no .env)'}\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
