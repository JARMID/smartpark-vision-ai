import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import Request
from src.server import app

@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    orig = request.query_params.get("__orig_path")
    if orig:
        clean = orig if orig.startswith("/") else f"/{orig}"
        target = f"/api{clean}" if not clean.startswith("/api") else clean
        request.scope["path"] = target
    elif request.scope.get("path") in ("/api/index.py", "/api/index"):
        request.scope["path"] = "/api"
    
    return await call_next(request)

@app.get("/api")
def vercel_api_root():
    return {"status": "ONLINE", "service": "SmartPark Vision AI Sovereign Server"}
