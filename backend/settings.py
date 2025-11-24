from dotenv import load_dotenv
import os
load_dotenv()

def _bool(s: str, default=False):
    if s is None: return default
    return s.strip().lower() in ("1","true","yes","on")

class Settings:
    # ✅ Configuration MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "llm_tests")

    # ✅ Configuration LLM - Cohérence avec llm_service.py
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")  # ✅ Changé de 1.3b à 6.7b (plus performant)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")

    # ✅ Configuration Mistral AI
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    # ✅ Configuration Authentication & Sécurité
    AUTH_ENABLED = _bool(os.getenv("AUTH_ENABLED"), False)
    JWT_SECRET = os.getenv("JWT_SECRET")  # ✅ Retiré la valeur par défaut dangereuse
    JWT_ALG = os.getenv("JWT_ALG", "HS256")
    JWT_ACCESS_TTL_MIN = int(os.getenv("JWT_ACCESS_TTL_MIN", "30"))
    JWT_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "7"))

    # ✅ CORS - Valeur par défaut sécurisée (localhost uniquement)
    CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS","http://localhost:5173,http://localhost:3000").split(",") if o.strip()]

    MAX_REQ_BODY_KB = int(os.getenv("MAX_REQ_BODY_KB", "256"))
    GEN_TIMEOUT = int(os.getenv("GEN_TIMEOUT", "90"))
    MAX_GENERATE_PER_MIN = int(os.getenv("MAX_GENERATE_PER_MIN","60"))

settings = Settings()
