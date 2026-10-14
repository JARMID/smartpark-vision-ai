import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import Request
from src.server import app

# Register route aliases so both /api/xxx and /xxx resolve seamlessly
for route in list(app.routes):
    if hasattr(route, "path") and route.path.startswith("/api/"):
        stripped = route.path[4:]  # e.g., '/status', '/cameras', '/simulate'
        if not any(getattr(r, "path", None) == stripped for r in app.routes):
            app.add_api_route(
                stripped,
                route.endpoint,
                methods=route.methods,
                response_model=getattr(route, "response_model", None),
            )

@app.middleware("http")
async def vercel_path_rewrite_middleware(request: Request, call_next):
    matched_path = request.headers.get("x-matched-path")
    if matched_path and request.scope["path"] in ("/api/index.py", "/api/index", "/api"):
        request.scope["path"] = matched_path
    elif request.scope["path"].startswith("/api/index/"):
        request.scope["path"] = request.scope["path"].replace("/api/index", "/api", 1)
    elif request.scope["path"].startswith("/api/index.py/"):
        request.scope["path"] = request.scope["path"].replace("/api/index.py", "/api", 1)
    
    return await call_next(request)

@app.get("/")
def vercel_root():
    return {"status": "ONLINE", "service": "SmartPark Vision AI Serverless"}

from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Custom 404",
            "scope_path": request.scope.get("path"),
            "url_path": request.url.path,
            "raw_path": request.scope.get("raw_path", b"").decode(),
            "matched_path": request.headers.get("x-matched-path"),
            "headers": dict(request.headers),
        }
    )

