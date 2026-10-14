import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.server import app

@app.get("/status")
def test_status():
    return {"status": "ONLINE", "matched": "/status"}

@app.get("/api/status")
def test_api_status():
    return {"status": "ONLINE", "matched": "/api/status"}
