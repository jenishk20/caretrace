"""Loopback-only health check for an OpenAI-compatible local model server."""
import os
from urllib.parse import urlparse
from urllib.request import urlopen

def status():
    url=os.environ.get("CARETRACE_LOCAL_MODEL_URL","http://127.0.0.1:8000/v1/models"); host=urlparse(url).hostname
    if host not in {"localhost","127.0.0.1","::1"}: return {"reachable":False,"url":url,"detail":"Blocked: endpoint must be loopback in local-only mode."}
    try:
        with urlopen(url,timeout=1.5) as response: return {"reachable":response.status<400,"url":url,"detail":"Local model endpoint responded."}
    except Exception as error: return {"reachable":False,"url":url,"detail":f"Local model unavailable: {type(error).__name__}"}
