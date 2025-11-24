# backend/rate_limit.py
import time
from fastapi import HTTPException, Request

# Stockage en memoire des requetes par IP (sliding window)
_BUCKET = {}

def rate_limit(max_per_min: int):
    """
    Decorator pour limiter le nombre de requetes par minute

    Utilise un algorithme de sliding window :
    - Conserve les timestamps des requetes dans une fenetre de 60s
    - Bloque si le nombre de requetes depasse max_per_min
    - Identifie les clients par IP + chemin

    Args:
        max_per_min: Nombre maximum de requetes autorisees par minute

    Returns:
        Dependency FastAPI a utiliser avec Depends()

    Example:
        @app.post("/generate")
        def generate(data: GenerateRequest, _=Depends(rate_limit(10))):
            ...
    """
    window = 60.0  # Fenetre de 60 secondes

    def dep(request: Request):
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path}"
        now = time.time()

        # Garder seulement les timestamps dans la fenetre
        ts = [t for t in _BUCKET.get(key, []) if now - t < window]

        # Verifier si la limite est atteinte
        if len(ts) >= max_per_min:
            raise HTTPException(
                status_code=429,
                detail=f"Trop de requetes. Limite: {max_per_min}/minute. Reessayez dans {int(window - (now - ts[0]))}s."
            )

        # Ajouter le timestamp actuel
        ts.append(now)
        _BUCKET[key] = ts

    return dep

def cleanup_rate_limit_cache():
    """
    Nettoie les anciennes entrees du cache de rate limiting
    A appeler periodiquement (par ex. toutes les 5 minutes)
    """
    now = time.time()
    window = 60.0

    # Supprimer les cles expirees
    keys_to_delete = []
    for key, timestamps in _BUCKET.items():
        # Garder seulement les timestamps recents
        recent = [t for t in timestamps if now - t < window]
        if not recent:
            keys_to_delete.append(key)
        else:
            _BUCKET[key] = recent

    for key in keys_to_delete:
        del _BUCKET[key]
