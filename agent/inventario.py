#!/usr/bin/env python3
"""
GerenciadorTI — Agente de Inventário v1.0.0
============================================
Coleta dados técnicos do computador (CPU, RAM, Disco, Rede, OS)
e envia para o servidor GerenciadorTI via HTTP POST.

Uso:
    1. Instale as dependências:
           pip install psutil requests

    2. Na primeira execução, o arquivo config.json é criado automaticamente.
       Preencha o campo "user_id" com o seu ID do Supabase.

    3. Execute:
           python inventario.py

Requisitos: Python 3.9+ | Windows 10/11
"""

import json
import socket
import platform
import subprocess
import datetime
import sys
import os
import time
import threading

# ── Dependências externas ────────────────────────────────
try:
    import psutil
except ImportError:
    print("[ERRO] psutil não instalado.")
    print("       Execute: pip install psutil requests")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERRO] requests não instalado.")
    print("       Execute: pip install psutil requests")
    sys.exit(1)

# ── Constantes ───────────────────────────────────────────
AGENT_VERSION = "1.0.0"
CONFIG_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {
    "server_url": "http://localhost:8000",
    "agent_key": "",
    "user_id": "COLE_SEU_USER_ID_AQUI",
    "client_id": None,
    "heartbeat_interval_minutes": 5,
}

# ── Config ───────────────────────────────────────────────
def load_config() -> dict:
    """Lê config.json; cria o template se não existir."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[INFO] config.json criado em:\n       {CONFIG_FILE}")
        print()
        print("[AÇÃO] Abra o arquivo, preencha 'user_id' e rode novamente.")
        input("\nPressione Enter para fechar...")
        sys.exit(0)

    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)

    merged = {**DEFAULT_CONFIG, **cfg}

    if not merged.get("user_id") or merged["user_id"] == DEFAULT_CONFIG["user_id"]:
        print("[ERRO] user_id não configurado em config.json")
        print(f"       Arquivo: {CONFIG_FILE}")
        input("\nPressione Enter para fechar...")
        sys.exit(1)

    return merged


# ── Coleta de hardware / sistema ─────────────────────────
def get_mac_address() -> str:
    """Retorna o MAC da interface de rede principal (não-loopback)."""
    # Windows: usa wmic para maior confiabilidade
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                ["wmic", "nic", "where", "NetEnabled=True", "get", "MACAddress", "/value"],
                text=True, timeout=5, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if line.startswith("MACAddress="):
                    mac = line.split("=", 1)[1].strip()
                    if mac:
                        return mac.replace("-", ":").lower()
        except Exception:
            pass

    # Fallback: psutil (multiplataforma)
    skip = {"loopback", "lo", "vmware", "vbox", "virtual", "docker", "vethernet"}
    for iface, addrs in psutil.net_if_addrs().items():
        if any(k in iface.lower() for k in skip):
            continue
        for addr in addrs:
            if addr.family == psutil.AF_LINK:
                mac = addr.address.replace("-", ":").lower()
                if mac and mac != "00:00:00:00:00:00":
                    return mac

    # Último recurso: derivado do UUID do sistema
    n = __import__("uuid").getnode()
    return ":".join(f"{(n >> i) & 0xff:02x}" for i in range(40, -1, -8))


def get_ip_local() -> str:
    """Retorna o IP local preferencial (não-loopback)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def get_cpu_model() -> str:
    """Retorna o nome completo do processador."""
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "Name", "/value"],
                text=True, timeout=5, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if line.startswith("Name="):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
    return platform.processor() or "Desconhecido"


def get_os_version() -> str:
    """Retorna string legível da versão do sistema operacional."""
    if platform.system() == "Windows":
        try:
            out = subprocess.check_output(
                ["wmic", "os", "get", "Caption,BuildNumber,Version", "/value"],
                text=True, timeout=5, stderr=subprocess.DEVNULL,
            )
            caption = build = ""
            for line in out.splitlines():
                if line.startswith("Caption="):
                    caption = line.split("=", 1)[1].strip()
                if line.startswith("BuildNumber="):
                    build = line.split("=", 1)[1].strip()
            if caption:
                return f"{caption} (Build {build})" if build else caption
        except Exception:
            pass
    return f"{platform.system()} {platform.release()} {platform.version()}"


# Softwares considerados de risco — chave em minúsculo, parcial
RISK_SOFTWARE = {
    # P2P / Torrent
    "utorrent":       ("torrent",    "⚠️ P2P/Torrent"),
    "bittorrent":     ("torrent",    "⚠️ P2P/Torrent"),
    "qbittorrent":    ("torrent",    "⚠️ P2P/Torrent"),
    "vuze":           ("torrent",    "⚠️ P2P/Torrent"),
    "frostwire":      ("torrent",    "⚠️ P2P/Torrent"),
    # Acesso remoto não autorizado
    "anydesk":        ("remote",     "🔴 Acesso Remoto"),
    "ultraviewer":    ("remote",     "🔴 Acesso Remoto"),
    "rustdesk":       ("remote",     "🔴 Acesso Remoto"),
    "ammyy":          ("remote",     "🔴 Acesso Remoto"),
    "supremo":        ("remote",     "🔴 Acesso Remoto"),
    # Ferramentas de hacking / pentest
    "cheat engine":   ("hack",       "🔴 Cheat/Hack"),
    "wireshark":      ("sniffer",    "⚠️ Sniffer de Rede"),
    "nmap":           ("scanner",    "⚠️ Scanner de Rede"),
    # Adware / PUP conhecidos
    "opencandy":      ("adware",     "⚠️ Adware"),
    "conduit":        ("adware",     "⚠️ Adware"),
    "babylon":        ("adware",     "⚠️ Adware"),
    "ask toolbar":    ("adware",     "⚠️ Adware"),
    "mywebsearch":    ("adware",     "⚠️ Adware"),
}


def _classify_risk(name: str) -> str | None:
    """Retorna string de risco se o software for reconhecido, senão None."""
    n = name.lower()
    for key, (_, label) in RISK_SOFTWARE.items():
        if key in n:
            return label
    return None


def get_installed_software() -> list[dict]:
    """
    Lê o registro do Windows e retorna lista de softwares instalados.
    Varre HKLM (64-bit e 32-bit) e HKCU para pegar instalações por usuário.
    Não requer dependências externas — usa winreg (stdlib).
    """
    if platform.system() != "Windows":
        return []

    import winreg

    HIVES = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    def _read_str(key, field: str) -> str | None:
        try:
            val, _ = winreg.QueryValueEx(key, field)
            return str(val).strip() or None
        except Exception:
            return None

    seen   = set()
    result = []

    for hive, path in HIVES:
        try:
            root = winreg.OpenKey(hive, path)
        except Exception:
            continue

        i = 0
        while True:
            try:
                sub_name = winreg.EnumKey(root, i)
                i += 1
            except OSError:
                break

            try:
                sub = winreg.OpenKey(root, sub_name)
                name = _read_str(sub, "DisplayName")
                if not name or name in seen:
                    winreg.CloseKey(sub)
                    continue
                seen.add(name)

                version   = _read_str(sub, "DisplayVersion")
                publisher = _read_str(sub, "Publisher")
                raw_date  = _read_str(sub, "InstallDate") or ""
                size_kb   = None
                try:
                    sz, _ = winreg.QueryValueEx(sub, "EstimatedSize")
                    size_kb = int(sz)
                except Exception:
                    pass

                # Formata data: "20240115" → "15/01/2024"
                install_date = None
                if len(raw_date) == 8 and raw_date.isdigit():
                    install_date = f"{raw_date[6:]}/{raw_date[4:6]}/{raw_date[:4]}"

                entry = {
                    "name":         name,
                    "version":      version,
                    "publisher":    publisher,
                    "install_date": install_date,
                    "size_kb":      size_kb,
                    "risk":         _classify_risk(name),
                }
                result.append(entry)
                winreg.CloseKey(sub)
            except Exception:
                pass

        winreg.CloseKey(root)

    result.sort(key=lambda s: s["name"].lower())
    print(f"[DEBUG] Softwares instalados: {len(result)} encontrados"
          f" | {sum(1 for s in result if s['risk'])} com risco detectado")
    return result


def _get_wmi():
    """Retorna instância WMI ou None se não disponível."""
    try:
        import wmi
        return wmi.WMI()
    except Exception:
        return None


def get_gpu_info() -> dict:
    """
    Coleta GPU via wmi.Win32_VideoController().
    - Se houver múltiplas GPUs, usa a de maior VRAM (dedicada).
    - Temperatura via nvidia-smi para NVIDIA; N/D para AMD/Intel.
    """
    info = {"gpu_model": None, "gpu_vram_gb": None, "gpu_temp_c": None}

    if platform.system() != "Windows":
        return info

    w = _get_wmi()
    if w:
        try:
            controllers = w.Win32_VideoController()
            # Ordena por VRAM decrescente — GPU dedicada geralmente tem mais VRAM
            controllers = sorted(
                controllers,
                key=lambda c: int(c.AdapterRAM or 0),
                reverse=True,
            )
            if controllers:
                gpu = controllers[0]
                name = (gpu.Name or "").strip() or "Integrada"
                info["gpu_model"] = name

                ram_bytes = int(gpu.AdapterRAM or 0)
                if ram_bytes > 0:
                    info["gpu_vram_gb"] = round(ram_bytes / (1024 ** 3), 2)

                print(f"[DEBUG] GPU detectada: {name}"
                      + (f" | {info['gpu_vram_gb']} GB VRAM" if info["gpu_vram_gb"] else " | VRAM N/D"))
        except Exception as e:
            print(f"[DEBUG] GPU via WMI falhou: {e}")

    # Temperatura via nvidia-smi (somente NVIDIA)
    try:
        temp_out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        ).strip()
        info["gpu_temp_c"] = float(temp_out.splitlines()[0].strip())
        print(f"[DEBUG] GPU temperatura: {info['gpu_temp_c']}°C")
    except Exception:
        pass  # AMD / Intel / nvidia-smi ausente

    return info


def get_motherboard_info() -> dict:
    """Coleta placa-mãe via wmi.Win32_BaseBoard() e BIOS via Win32_BIOS()."""
    info = {
        "mb_manufacturer": None,
        "mb_model":        None,
        "mb_version":      None,
        "bios_version":    None,
        "bios_date":       None,
    }

    if platform.system() != "Windows":
        return info

    w = _get_wmi()
    if w:
        # Placa-mãe
        try:
            boards = w.Win32_BaseBoard()
            if boards:
                b = boards[0]
                info["mb_manufacturer"] = (b.Manufacturer or "").strip() or None
                info["mb_model"]        = (b.Product      or "").strip() or None
                info["mb_version"]      = (b.Version      or "").strip() or None
                print(f"[DEBUG] Placa-mãe: {info['mb_manufacturer']} {info['mb_model']} {info['mb_version']}")
        except Exception as e:
            print(f"[DEBUG] Placa-mãe via WMI falhou: {e}")

        # BIOS
        try:
            bioses = w.Win32_BIOS()
            if bioses:
                bios = bioses[0]
                info["bios_version"] = (bios.SMBIOSBIOSVersion or "").strip() or None

                # ReleaseDate: "20231205000000.000000+000" → "05/12/2023"
                raw = bios.ReleaseDate or ""
                if len(raw) >= 8:
                    try:
                        info["bios_date"] = f"{raw[6:8]}/{raw[4:6]}/{raw[:4]}"
                    except Exception:
                        info["bios_date"] = raw[:8]

                print(f"[DEBUG] BIOS: {info['bios_version']} ({info['bios_date']})")
        except Exception as e:
            print(f"[DEBUG] BIOS via WMI falhou: {e}")

    return info


def get_disk_info() -> tuple:
    """Retorna (total_gb, free_gb) da unidade do sistema."""
    drive = "C:\\" if platform.system() == "Windows" else "/"
    try:
        usage = psutil.disk_usage(drive)
        return (
            round(usage.total / (1024 ** 3), 2),
            round(usage.free  / (1024 ** 3), 2),
        )
    except Exception:
        return (0.0, 0.0)


def collect() -> dict:
    """Coleta e exibe todos os dados do sistema."""
    print("[*] Coletando informações do sistema...\n")

    hostname    = socket.gethostname()
    mac         = get_mac_address()
    ip          = get_ip_local()
    os_ver      = get_os_version()
    cpu_model   = get_cpu_model()
    cpu_cores   = psutil.cpu_count(logical=True) or 0
    cpu_freq    = None
    try:
        freq = psutil.cpu_freq()
        if freq:
            cpu_freq = round(freq.current, 1)
    except Exception:
        pass

    mem         = psutil.virtual_memory()
    ram_total   = round(mem.total / (1024 ** 3), 2)
    ram_used    = round(mem.used  / (1024 ** 3), 2)
    disk_total, disk_free = get_disk_info()
    gpu         = get_gpu_info()
    mb          = get_motherboard_info()
    softwares   = get_installed_software()

    # ── Print para o console ─────────────────────────────
    print(f"  Hostname     : {hostname}")
    print(f"  MAC          : {mac}")
    print(f"  IP Local     : {ip}")
    print(f"  OS           : {os_ver}")
    print(f"  CPU          : {cpu_model}")
    print(f"               : {cpu_cores} cores"
          + (f" @ {cpu_freq} MHz" if cpu_freq else ""))
    print(f"  RAM          : {ram_used} GB usados / {ram_total} GB total")
    print(f"  Disco (C:)   : "
          f"{round(disk_total - disk_free, 1)} GB usados / "
          f"{disk_total} GB total "
          f"({disk_free} GB livres)")
    if gpu.get("gpu_model"):
        temp_str = f" | {gpu['gpu_temp_c']}°C" if gpu.get("gpu_temp_c") is not None else ""
        vram_str = f" | {gpu['gpu_vram_gb']} GB VRAM" if gpu.get("gpu_vram_gb") else ""
        print(f"  GPU          : {gpu['gpu_model']}{vram_str}{temp_str}")
    if mb.get("mb_model"):
        print(f"  Placa-mãe    : {mb.get('mb_manufacturer','')} {mb['mb_model']} {mb.get('mb_version','')}")
        print(f"  BIOS         : {mb.get('bios_version','—')} ({mb.get('bios_date','—')})")
    print()

    return {
        "agent_version":    AGENT_VERSION,
        "hostname":         hostname,
        "mac_address":      mac,
        "ip_local":         ip,
        "os_version":       os_ver,
        "cpu_model":        cpu_model,
        "cpu_cores":        cpu_cores,
        "cpu_freq_mhz":     cpu_freq,
        "ram_total_gb":     ram_total,
        "ram_used_gb":      ram_used,
        "storage_total_gb": disk_total,
        "storage_free_gb":  disk_free,
        # GPU
        "gpu_model":        gpu.get("gpu_model"),
        "gpu_vram_gb":      gpu.get("gpu_vram_gb"),
        "gpu_temp_c":       gpu.get("gpu_temp_c"),
        # Placa-mãe / BIOS
        "mb_manufacturer":  mb.get("mb_manufacturer"),
        "mb_model":         mb.get("mb_model"),
        "mb_version":       mb.get("mb_version"),
        "bios_version":     mb.get("bios_version"),
        "bios_date":        mb.get("bios_date"),
        # Inventário de software
        "softwares_json":   softwares,
        "collected_at":     datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ── Envio para o servidor ────────────────────────────────
def send(cfg: dict, payload: dict) -> None:
    """Envia o payload via POST para /agente/coleta."""
    url = cfg["server_url"].rstrip("/") + "/agente/coleta"

    headers = {"Content-Type": "application/json"}
    if cfg.get("agent_key"):
        headers["X-Agent-Key"] = cfg["agent_key"]

    # Injeta user_id e client_id no payload
    payload["user_id"]   = cfg["user_id"]
    payload["client_id"] = cfg.get("client_id")

    # ── Debug: verifica softwares_json antes de enviar
    sw = payload.get("softwares_json", [])
    print(f"[DEBUG] Payload — softwares_json: {len(sw)} itens | payload total: ~{len(json.dumps(payload, default=str))//1024} KB")
    if sw:
        print(f"[DEBUG] Primeiros 3 softwares: {[s['name'] for s in sw[:3]]}")

    print(f"[*] Enviando dados para: {url}")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        resp = r.json()
        action = resp.get("action", "")
        msg    = resp.get("message", "OK")
        eid    = resp.get("id", "")

        if action == "created":
            print(f"[OK] Novo equipamento cadastrado (ID: {eid})")
        elif action == "updated":
            print(f"[OK] Equipamento atualizado (ID: {eid})")
        else:
            print(f"[OK] {msg}")

    except requests.exceptions.ConnectionError:
        print(f"[ERRO] Não foi possível conectar em {url}")
        print("       Verifique se o servidor GerenciadorTI está rodando.")
    except requests.exceptions.Timeout:
        print("[ERRO] Servidor não respondeu (timeout 15s).")
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json()
            print(f"[ERRO] HTTP {e.response.status_code}: {detail.get('error', e.response.text)}")
            if detail.get("hint"):
                print(f"       Dica: {detail['hint']}")
        except Exception:
            print(f"[ERRO] HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"[ERRO] {type(e).__name__}: {e}")

# ── Heartbeat ────────────────────────────────────────────
def heartbeat(cfg: dict, mac: str) -> bool:
    """Envia sinal de vida mínimo para /agente/heartbeat."""
    url = cfg["server_url"].rstrip("/") + "/agente/heartbeat"
    headers = {"Content-Type": "application/json"}
    if cfg.get("agent_key"):
        headers["X-Agent-Key"] = cfg["agent_key"]
    payload = {"user_id": cfg["user_id"], "mac_address": mac}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def run_heartbeat_loop(cfg: dict, mac: str, interval_minutes: int) -> None:
    """Loop bloqueante: envia heartbeat a cada N minutos."""
    SEP = "═" * 52
    interval_sec = interval_minutes * 60
    print(SEP)
    print(f"  Heartbeat ativo — intervalo: {interval_minutes} min")
    print(f"  Pressione Ctrl+C para encerrar.")
    print(SEP)
    print()

    # Heartbeat imediato ao iniciar
    ok = heartbeat(cfg, mac)
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {'✔ Online' if ok else '✘ Falhou (servidor offline?)'}")

    while True:
        try:
            # Contagem regressiva visível
            for remaining in range(interval_sec, 0, -1):
                m, s = divmod(remaining, 60)
                print(f"\r  Próximo heartbeat em {m:02d}:{s:02d}  ", end="", flush=True)
                time.sleep(1)
            print()
            ok = heartbeat(cfg, mac)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}] {'✔ Online' if ok else '✘ Falhou (servidor offline?)'}")
        except KeyboardInterrupt:
            print("\n\n  Heartbeat encerrado.")
            break


# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    SEP = "═" * 52

    # Modo: python inventario.py --heartbeat
    heartbeat_mode = "--heartbeat" in sys.argv

    print(SEP)
    print(f"  GerenciadorTI — Agente de Inventário v{AGENT_VERSION}")
    if heartbeat_mode:
        print("  Modo: Heartbeat contínuo")
    print(SEP)
    print()

    cfg = load_config()
    mac = get_mac_address()

    if heartbeat_mode:
        interval = int(cfg.get("heartbeat_interval_minutes") or 5)
        run_heartbeat_loop(cfg, mac, interval)
    else:
        payload = collect()
        send(cfg, payload)
        print()

        # Pergunta se quer continuar em modo heartbeat
        print("─" * 52)
        print("  Deseja manter o agente ativo em modo heartbeat?")
        resp = input("  [S/n]: ").strip().lower()
        if resp in ("", "s", "sim", "y", "yes"):
            interval = int(cfg.get("heartbeat_interval_minutes") or 5)
            run_heartbeat_loop(cfg, mac, interval)
        else:
            input("\n[FIM] Pressione Enter para fechar.")
