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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
