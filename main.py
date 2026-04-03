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
import datetime
from fastapi import FastAPI, Query, Request
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


# ── Agente de Inventário ─────────────────────────────────

def _normalize_mac(mac: str) -> str:
    """Normaliza MAC para xx:xx:xx:xx:xx:xx lowercase, independente do separador de entrada."""
    digits = re.sub(r'[^0-9a-fA-F]', '', mac).lower()
    if len(digits) == 12:
        return ':'.join(digits[i:i+2] for i in range(0, 12, 2))
    return mac.lower()  # fallback: devolve como veio


def _sb_headers() -> dict | None:
    """Retorna headers para chamadas REST diretas ao Supabase (service role)."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None
    return {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }

def _sb_url(path: str) -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/") + "/rest/v1/" + path.lstrip("/")


@app.post("/agente/coleta")
async def agent_collect(request: Request):
    """
    Recebe dados coletados pelo agente de inventário.
    Faz upsert na tabela equipamentos usando (user_id, mac_address) como chave.
    ⚠️  Apenas para uso local — usa service role key para bypassar RLS.
    """
    # Verificação de chave de agente (opcional)
    agent_key_env = os.getenv("AGENT_SECRET", "")
    if agent_key_env:
        received_key = request.headers.get("X-Agent-Key", "")
        if received_key != agent_key_env:
            return JSONResponse({"error": "Chave de agente inválida."}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON inválido."}, status_code=400)

    user_id  = body.get("user_id", "").strip()
    mac      = _normalize_mac((body.get("mac_address") or "").strip())

    print(f"[DEBUG] Coleta recebida — user: {user_id[:8]}... | MAC normalizado: '{mac}'")

    if not user_id:
        return JSONResponse(
            {"error": "user_id obrigatório.", "hint": "Configure user_id no config.json do agente."},
            status_code=422,
        )
    if not mac:
        return JSONResponse({"error": "mac_address obrigatório."}, status_code=422)

    headers = _sb_headers()
    if headers is None:
        return JSONResponse(
            {
                "error": "Supabase não configurado no servidor.",
                "hint": "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env",
            },
            status_code=503,
        )

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    upsert_data = {
        "user_id":          user_id,
        "mac_address":      mac,
        "last_seen_at":     now_iso,   # coleta também conta como sinal de vida
        "ip_local":         body.get("ip_local"),
        "hostname_real":    body.get("hostname"),
        "os_version":       body.get("os_version"),
        "cpu_model":        body.get("cpu_model"),
        "cpu_cores":        body.get("cpu_cores"),
        "cpu_freq_mhz":     body.get("cpu_freq_mhz"),
        "ram_total_gb":     body.get("ram_total_gb"),
        "ram_used_gb":      body.get("ram_used_gb"),
        "storage_total_gb": body.get("storage_total_gb"),
        "storage_free_gb":  body.get("storage_free_gb"),
        "agent_version":    body.get("agent_version"),
        "last_inventory_at": now_iso,
        # GPU
        "gpu_model":        body.get("gpu_model"),
        "gpu_vram_gb":      body.get("gpu_vram_gb"),
        "gpu_temp_c":       body.get("gpu_temp_c"),
        # Placa-mãe / BIOS
        "mb_manufacturer":  body.get("mb_manufacturer"),
        "mb_model":         body.get("mb_model"),
        "mb_version":       body.get("mb_version"),
        "bios_version":     body.get("bios_version"),
        "bios_date":        body.get("bios_date"),
        "softwares_json":   body.get("softwares_json") or [],
    }
    if body.get("client_id") is not None:
        upsert_data["client_id"] = body["client_id"]

    sw_list = body.get("softwares_json")
    if isinstance(sw_list, list) and len(sw_list) > 0:
        upsert_data["softwares_json"] = sw_list
        print(f"[DEBUG] softwares_json recebidos: {len(sw_list)} itens")
    else:
        upsert_data["softwares_json"] = []
        print(f"[ERRO] Lista de softwares recebida vazia ou inválida (tipo: {type(sw_list).__name__}, valor: {str(sw_list)[:80]})")

    try:
        import httpx
        # Timeout maior: payload com softwares pode ter 30-50 KB
        # Prefer: return=minimal no PATCH — não devolve a linha inteira, evita timeout
        patch_headers = {**headers, "Prefer": "return=minimal"}

        async with httpx.AsyncClient(timeout=60) as client:
            # Busca equipamento existente pelo MAC
            search = await client.get(
                _sb_url("equipamentos"),
                headers=headers,
                params={
                    "user_id":     f"eq.{user_id}",
                    "mac_address": f"eq.{mac}",
                    "select":      "id,name",
                    "limit":       "1",
                },
            )
            search.raise_for_status()
            rows = search.json()

            if rows:
                equip_id   = rows[0]["id"]
                equip_name = rows[0]["name"]
                patch_r = await client.patch(
                    _sb_url(f"equipamentos?id=eq.{equip_id}"),
                    headers=patch_headers,
                    json=upsert_data,
                )
                if patch_r.status_code not in (200, 204):
                    print(f"[ERRO] PATCH falhou: {patch_r.status_code} — {patch_r.text[:300]}")
                    return JSONResponse({"error": f"Supabase PATCH falhou: {patch_r.text[:200]}"}, status_code=500)
                print(f"[DEBUG] PATCH OK ({patch_r.status_code}) — '{equip_name}' atualizado com {len(upsert_data.get('softwares_json', []))} softwares")
                return JSONResponse({
                    "action":  "updated",
                    "id":      equip_id,
                    "message": f"Equipamento '{equip_name}' atualizado.",
                })
            else:
                upsert_data["name"]   = body.get("hostname") or mac
                upsert_data["type"]   = "computador"
                upsert_data["status"] = "ativo"
                ins = await client.post(
                    _sb_url("equipamentos"),
                    headers={**headers, "Prefer": "return=representation"},
                    json=upsert_data,
                )
                ins.raise_for_status()
                result = ins.json()
                new_id = result[0]["id"] if result else None
                print(f"[DEBUG] INSERT OK — novo equipamento ID {new_id}")
                return JSONResponse({
                    "action":  "created",
                    "id":      new_id,
                    "message": "Equipamento cadastrado via agente.",
                }, status_code=201)

    except Exception as exc:
        print(f"[ERRO] Exceção em /agente/coleta: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/agente/heartbeat")
async def agent_heartbeat(request: Request):
    """
    Sinal de vida do agente — chamado a cada N minutos.
    Atualiza apenas last_seen_at; payload mínimo: {user_id, mac_address}.
    """
    agent_key_env = os.getenv("AGENT_SECRET", "")
    if agent_key_env:
        if request.headers.get("X-Agent-Key", "") != agent_key_env:
            return JSONResponse({"error": "Chave inválida."}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON inválido."}, status_code=400)

    user_id  = (body.get("user_id") or "").strip()
    mac_raw  = (body.get("mac_address") or "").strip()
    mac      = _normalize_mac(mac_raw)

    print(f"[DEBUG] Heartbeat recebido — user: {user_id[:8]}... | MAC bruto: '{mac_raw}' | MAC normalizado: '{mac}'")

    if not user_id or not mac:
        return JSONResponse({"error": "user_id e mac_address obrigatórios."}, status_code=422)

    headers = _sb_headers()
    if headers is None:
        return JSONResponse({"error": "Supabase não configurado."}, status_code=503)

    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        import httpx
        # Cabeçalho extra: conta as linhas afetadas
        patch_headers = {**headers, "Prefer": "return=representation,count=exact"}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.patch(
                _sb_url(f"equipamentos?user_id=eq.{user_id}&mac_address=eq.{mac}"),
                headers=patch_headers,
                json={"last_seen_at": now_iso},
            )
            r.raise_for_status()
            rows = r.json()
            affected = len(rows) if isinstance(rows, list) else 0

            if affected == 0:
                # Nenhuma linha encontrada — MAC pode não estar no banco ainda
                # Tenta buscar com MAC sem normalização para diagnóstico
                search = await client.get(
                    _sb_url("equipamentos"),
                    headers=headers,
                    params={"user_id": f"eq.{user_id}", "select": "id,mac_address", "limit": "20"},
                )
                macs_no_banco = [row.get("mac_address") for row in (search.json() or [])]
                print(f"[DEBUG] Nenhuma linha afetada! MACs no banco para este user: {macs_no_banco}")
                return JSONResponse({
                    "ok": False,
                    "warn": "Nenhum equipamento encontrado com esse MAC. Execute inventario.py primeiro.",
                    "mac_buscado": mac,
                    "macs_no_banco": macs_no_banco,
                })

            print(f"[DEBUG] last_seen_at atualizado com sucesso — {affected} linha(s) | ts: {now_iso}")
            return JSONResponse({"ok": True, "ts": now_iso, "rows_updated": affected})

    except Exception as exc:
        print(f"[DEBUG] Heartbeat ERRO: {exc}")
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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
