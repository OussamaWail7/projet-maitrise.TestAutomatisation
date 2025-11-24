# backend/audit.py
import re, time
from fastapi import Request
from database import db

# Regex pour detecter et masquer les donnees sensibles (PII)
PII_RE = re.compile(r"(?i)(password|secret|token|api_key|bearer\s+[a-z0-9\-_.=]+)")

def mask_pii(s: str) -> str:
    """Masque les donnees sensibles dans une chaine"""
    if not s:
        return s
    return PII_RE.sub("[REDACTED]", s)

async def audit_middleware(request: Request, call_next):
    """
    Middleware d'audit pour logger toutes les requetes HTTP

    Enregistre dans MongoDB :
    - Timestamp
    - IP du client
    - Methode HTTP
    - Chemin de la requete
    - Code de statut de la reponse
    - User-Agent (avec masquage des donnees sensibles)
    - Duree de la requete en ms
    """
    start = time.time()
    resp = await call_next(request)
    duration = time.time() - start

    try:
        db["audit_logs"].insert_one({
            "ts": time.time(),
            "ip": request.client.host if request.client else None,
            "method": request.method,
            "path": request.url.path,
            "status": resp.status_code,
            "ua": mask_pii(request.headers.get("user-agent", "")),
            "dur_ms": int(duration * 1000),
        })
    except Exception as e:
        # Ne pas faire echouer la requete si l'audit echoue
        print(f"[AUDIT ERROR] {e}")

    return resp
