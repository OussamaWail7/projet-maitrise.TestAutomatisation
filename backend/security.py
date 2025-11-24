import time, uuid
from typing import List, Dict, Optional
import jwt
from fastapi import HTTPException, Header
from settings import settings

# ✅ Validation JWT_SECRET si l'authentification est activée
if settings.AUTH_ENABLED and not settings.JWT_SECRET:
    raise ValueError(
        "JWT_SECRET manquant dans .env alors que AUTH_ENABLED=True. "
        "Générez un secret sécurisé avec: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    )

ROLES = {
    "viewer":  ["history:read"],
    "tester":  ["generate:preview", "tests:confirm", "history:read"],
    "manager": ["generate:preview", "tests:confirm", "tests:export", "history:read"],
    "admin":   ["*"],
}

def role_scopes(role: str) -> List[str]:
    return ROLES.get(role, [])

def _now() -> int: return int(time.time())

def issue_tokens(user_id: str, role: str) -> Dict[str, str]:
    """
    ✅ Génère les tokens JWT avec validation du secret
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET non configuré")

    kid = "dev-kid-1"
    iat = _now()
    access = jwt.encode(
        {"sub": user_id, "role": role, "scopes": role_scopes(role), "iat": iat, "exp": iat + 60*settings.JWT_ACCESS_TTL_MIN, "kid": kid},
        settings.JWT_SECRET, algorithm=settings.JWT_ALG
    )
    refresh = jwt.encode(
        {"sub": user_id, "typ": "refresh", "iat": iat, "exp": iat + 60*60*24*settings.JWT_REFRESH_TTL_DAYS, "kid": kid, "jti": str(uuid.uuid4())},
        settings.JWT_SECRET, algorithm=settings.JWT_ALG
    )
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

def verify_access(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

def require_scopes(required: List[str]):
    """
    Si AUTH_ENABLED=false, bypass (aucune auth nécessaire).
    Sinon, vérifie un Bearer token et la présence des scopes.
    """
    def dep(authorization: Optional[str] = Header(None)):
        if not settings.AUTH_ENABLED:
            return {"sub": "dev", "scopes": ["*"]}
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Auth manquante")
        payload = verify_access(authorization.split(" ",1)[1])
        scopes = payload.get("scopes", [])
        if "*" in scopes:
            return payload
        for r in required:
            if r not in scopes:
                raise HTTPException(status_code=403, detail=f"Scope manquant: {r}")
        return payload
    return dep

def jwks() -> dict:
    return {"keys":[{"kid":"dev-kid-1","kty":"oct","use":"sig","alg":settings.JWT_ALG}]}
