import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import Request
from src.server import app

@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    # Vercel sends the original requested path in 'x-matched-path' or 'x-invoke-path'
    matched_path = request.headers.get("x-matched-path")
    if matched_path and request.scope["path"] in ("/api/index.py", "/api/index"):
        request.scope["path"] = matched_path
    elif request.scope["path"].startswith("/api/index.py/"):
        request.scope["path"] = request.scope["path"].replace("/api/index.py", "/api", 1)
    
    response = await call_next(request)
    return response

@app.get("/api/index.py")
def debug_vercel(request: Request):
    return {
        "path": request.url.path,
        "matched_path": request.headers.get("x-matched-path"),
        "headers": {k: v for k, v in request.headers.items() if not k.startswith("sec-")}
    }

