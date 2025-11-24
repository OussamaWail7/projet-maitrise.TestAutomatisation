# backend/main.py
from datetime import datetime
import os
import traceback
import re
from typing import Optional, List, Dict, Tuple

from fastapi import FastAPI, HTTPException, Query, Depends, Body, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from settings import settings
from database import save_test_case, list_test_cases, db, collection as TESTS_COL
from security import issue_tokens, require_scopes, jwks
from rate_limit import rate_limit
from audit import audit_middleware
from artifacts import open_path, save_bytes
from jobs import submit_job
from exec_store_mongo import (
    create_execution,
    mark_running,
    mark_result,
    get_execution,
    list_executions,
    get_execution_logs_text,
)
from selenium_runner import run_selenium
from gatling_jmeter_runner import run_gatling, run_jmeter
from test_runner import run_java_maven
from quality_analyzer import analyze_test_quality
from bson import ObjectId
from fastapi.responses import PlainTextResponse

app = FastAPI(
    title="IA Test Automatisation API",
    description="""
## API de Génération Automatique de Tests avec IA

Cette API permet de générer automatiquement des cas de test en utilisant différents modèles de langage (LLM).

### Fonctionnalités

* **Génération de tests** : Créez des tests unitaires, d'API (RestAssured) ou UI (Selenium)
* **Support multi-providers** : Gemini, Ollama, Mistral AI
* **Exécution avec JaCoCo** : Mesurez la couverture de code
* **Analyse qualitative** : Obtenez un score et des recommandations
* **Gestion d'historique** : Sauvegardez et réexécutez vos tests

### Providers LLM

* **Google Gemini** : Service cloud avec quotas gratuits
* **Ollama** : Modèles locaux (DeepSeek Coder)
* **Mistral AI** : Service cloud premium

### Authentification

L'authentification JWT est optionnelle (configurablevia AUTH_ENABLED dans .env).
    """,
    version="1.0.0",
    contact={
        "name": "Support ProjetIA",
        "url": "https://github.com/votre-repo",
    },
    license_info={
        "name": "MIT",
    },
)

# ------------------------ CORS ------------------------
# ✅ Configuration CORS sécurisée - Pas de wildcard "*" par défaut
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,  # ✅ Retiré le fallback ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ------------------------ Audit global ------------------------
app.middleware("http")(audit_middleware)

# ------------------------ Gestion globale des erreurs ------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global d'erreurs pour capturer toutes les exceptions non gérées"""
    import traceback

    error_id = str(ObjectId())  # ID unique pour tracer l'erreur
    error_trace = traceback.format_exc()

    # Logger l'erreur complète côté serveur
    print(f"[ERROR {error_id}] {type(exc).__name__}: {str(exc)}")
    print(error_trace)

    # Retourner une réponse propre au client
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Erreur interne du serveur. ID de l'erreur : {error_id}",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "error_id": error_id
        }
    )

# ------------------------ Limite de taille de corps ------------------------
@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl and int(cl) > settings.MAX_REQ_BODY_KB * 1024:
        return JSONResponse(status_code=413, content={"detail": "Corps de requête trop volumineux"})
    return await call_next(request)

# ------------------------ Helpers provider / modèle ------------------------
def _select_generator(provider_name: Optional[str]):
    """
    Retourne (fonction_de_generation, provider_actif) à partir du provider demandé
    ou de la config par défaut.
    """
    name = (provider_name or settings.LLM_PROVIDER or "").lower()
    if name == "ollama":
        from llm_service import generate_test_case_ollama as _gen
        return _gen, "ollama"
    elif name == "mistral":
        from mistral_service import generate_test_case_with_mistral as _gen
        return _gen, "mistral"
    # défaut: gemini
    from gemini_service import generate_test_case_with_gemini as _gen
    return _gen, "gemini"

def _normalize_model(provider: str, model: Optional[str]) -> Optional[str]:
    """
    Aligne le nom du modèle sur le provider choisi.
    - gemini  : si model absent ou ne commence pas par 'gemini-', utiliser settings.GOOGLE_MODEL
    - ollama  : si model absent, utiliser settings.OLLAMA_MODEL
    - mistral : si model absent, utiliser settings.MISTRAL_MODEL
    """
    p = (provider or "").lower()
    m = (model or "").strip() if model else None
    if p == "gemini":
        return m if (m and m.startswith("gemini-")) else settings.GOOGLE_MODEL
    elif p == "mistral":
        return m or settings.MISTRAL_MODEL
    return m or settings.OLLAMA_MODEL

DEFAULT_PROVIDER = (settings.LLM_PROVIDER or "gemini").lower()
if DEFAULT_PROVIDER == "ollama":
    DEFAULT_MODEL = settings.OLLAMA_MODEL
elif DEFAULT_PROVIDER == "mistral":
    DEFAULT_MODEL = settings.MISTRAL_MODEL
else:
    DEFAULT_MODEL = settings.GOOGLE_MODEL

# ------------------------ Schemas ------------------------
class AuthRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TestRequest(BaseModel):
    code: str = Field(min_length=1)
    # Pydantic v2: utiliser 'pattern=' au lieu de 'regex='
    test_type: str = Field(pattern="^(unit|rest-assured|selenium)$", default="rest-assured")
    language: str = Field(pattern="^(java|python|javascript|typescript|csharp|ruby|go)$", default="java")
    provider: Optional[str] = None
    model: Optional[str] = None

class ConfirmRequest(BaseModel):
    code: str
    generated_test: str
    test_type: str
    language: str
    status: str = "confirmed"
    provider: Optional[str] = None
    model: Optional[str] = None

class RunRequest(BaseModel):
    code: str
    test_type: str
    language: str
    model: Optional[str] = None
    provider: Optional[str] = None  # utile pour les jobs

# ------------------------ Auth ------------------------
@app.post("/auth/token", response_model=TokenResponse)
def login(data: AuthRequest):
    role = "admin" if data.username == "admin" else "tester"
    return issue_tokens(user_id=data.username, role=role)

@app.get("/.well-known/jwks.json")
def jwks_endpoint():
    return jwks()

# ------------------------ Health & Monitoring ------------------------
@app.get("/health")
def health():
    """
    Endpoint de health check basique.
    Retourne toujours UP (utilisé par les load balancers).
    """
    return {
        "status": "UP",
        "provider_default": DEFAULT_PROVIDER,
        "model_default": DEFAULT_MODEL,
        "version": "1.0.0"
    }


@app.get("/ready")
def readiness():
    """
    Endpoint de readiness check.
    Vérifie que toutes les dépendances critiques sont disponibles.
    """
    checks = {
        "mongodb": False,
        "collections": False,
    }

    errors = []

    # Vérifier MongoDB
    try:
        db.command("ping")
        checks["mongodb"] = True
    except Exception as e:
        errors.append(f"MongoDB: {str(e)}")

    # Vérifier les collections critiques
    try:
        collection_names = db.list_collection_names()
        required_collections = ["test_cases", "executions", "audit_logs"]
        missing = [c for c in required_collections if c not in collection_names]

        if not missing:
            checks["collections"] = True
        else:
            errors.append(f"Collections manquantes: {', '.join(missing)}")
    except Exception as e:
        errors.append(f"Collections: {str(e)}")

    # Déterminer le statut global
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    response = {
        "status": "READY" if all_ready else "NOT_READY",
        "checks": checks,
        "errors": errors if errors else None
    }

    return JSONResponse(content=response, status_code=status_code)


@app.get("/models")
def get_available_models():
    """
    Liste tous les modèles LLM disponibles (selon les providers configurés).
    Détecte automatiquement quels providers sont actifs et leurs modèles.
    """
    all_models = []

    # Gemini
    try:
        from gemini_service import list_available_models as gemini_models
        models = gemini_models()
        all_models.extend(models)
    except Exception as e:
        print(f"Erreur Gemini models: {e}")

    # Ollama
    try:
        from llm_service import list_available_models as ollama_models
        models = ollama_models()
        all_models.extend(models)
    except Exception as e:
        print(f"Erreur Ollama models: {e}")

    # Mistral
    try:
        from mistral_service import list_available_models as mistral_models
        models = mistral_models()
        all_models.extend(models)
    except Exception as e:
        print(f"Erreur Mistral models: {e}")

    # Grouper par provider
    by_provider = {}
    for model in all_models:
        provider = model.get("provider", "unknown")
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)

    return {
        "total": len(all_models),
        "models": all_models,
        "by_provider": by_provider,
        "default_provider": settings.LLM_PROVIDER,
        "default_model": DEFAULT_MODEL
    }


@app.get("/stats")
def get_stats(_auth=Depends(require_scopes(["history:read"]))):
    """
    Endpoint de statistiques globales.
    Retourne des métriques agrégées sur l'utilisation de l'application.
    """
    try:
        stats = {
            "test_cases": {},
            "executions": {},
            "audit": {}
        }

        # Statistiques des test cases
        total_tests = db["test_cases"].count_documents({})
        stats["test_cases"]["total"] = total_tests

        # Répartition par langage
        lang_pipeline = [
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        lang_stats = list(db["test_cases"].aggregate(lang_pipeline))
        stats["test_cases"]["by_language"] = {
            item["_id"] or "unknown": item["count"] for item in lang_stats
        }

        # Répartition par type de test
        type_pipeline = [
            {"$group": {"_id": "$test_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        type_stats = list(db["test_cases"].aggregate(type_pipeline))
        stats["test_cases"]["by_type"] = {
            item["_id"] or "unknown": item["count"] for item in type_stats
        }

        # Répartition par provider
        provider_pipeline = [
            {"$group": {"_id": "$provider", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        provider_stats = list(db["test_cases"].aggregate(provider_pipeline))
        stats["test_cases"]["by_provider"] = {
            item["_id"] or "unknown": item["count"] for item in provider_stats
        }

        # Statistiques des exécutions
        total_execs = db["executions"].count_documents({})
        stats["executions"]["total"] = total_execs

        # Répartition par statut
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        status_stats = list(db["executions"].aggregate(status_pipeline))
        stats["executions"]["by_status"] = {
            item["_id"] or "unknown": item["count"] for item in status_stats
        }

        # Taux de succès
        success_count = db["executions"].count_documents({"status": "success"})
        failed_count = db["executions"].count_documents({"status": "failed"})
        total_completed = success_count + failed_count

        if total_completed > 0:
            success_rate = (success_count / total_completed) * 100
            stats["executions"]["success_rate"] = round(success_rate, 2)
        else:
            stats["executions"]["success_rate"] = 0

        # Répartition par kind
        kind_pipeline = [
            {"$group": {"_id": "$kind", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        kind_stats = list(db["executions"].aggregate(kind_pipeline))
        stats["executions"]["by_kind"] = {
            item["_id"] or "unknown": item["count"] for item in kind_stats
        }

        # Statistiques d'audit (dernières 24h)
        import time
        yesterday = time.time() - (24 * 60 * 60)
        recent_requests = db["audit_logs"].count_documents({"ts": {"$gte": yesterday}})
        stats["audit"]["requests_24h"] = recent_requests

        # Endpoints les plus utilisés (dernières 24h)
        path_pipeline = [
            {"$match": {"ts": {"$gte": yesterday}}},
            {"$group": {"_id": "$path", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        path_stats = list(db["audit_logs"].aggregate(path_pipeline))
        stats["audit"]["top_endpoints"] = {
            item["_id"]: item["count"] for item in path_stats
        }

        return JSONResponse(content=stats)

    except Exception as e:
        print(f"ERROR /stats: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des stats: {str(e)}")

# ------------------------ Génération (preview) ------------------------
class TestPreviewReq(BaseModel):
    code: str = Field(min_length=1)
    test_type: str = Field(pattern="^(unit|rest-assured|selenium)$", default="rest-assured")
    language: str = Field(pattern="^(java|python|javascript|typescript|csharp|ruby|go)$", default="java")
    provider: Optional[str] = None
    model: Optional[str] = None

class TestPreviewResp(BaseModel):
    result: str

@app.post("/generate-test-preview", response_model=TestPreviewResp)
def generate_preview(
    data: TestPreviewReq,
    _auth=Depends(require_scopes(["generate:preview"])),
    _rate_limit=Depends(rate_limit(settings.MAX_GENERATE_PER_MIN))
):
    """
    ✅ Endpoint de génération de tests avec rate limiting

    Rate limit: {MAX_GENERATE_PER_MIN} requêtes/minute par IP
    """
    try:
        gen_func, active_provider = _select_generator(data.provider)
        active_model = _normalize_model(active_provider, data.model)
        # On suppose la signature (code, test_type, language, model)
        result = gen_func(data.code, data.test_type, data.language, active_model)
        cleaned = (result or "").replace("```", "").strip()
        if not cleaned:
            raise HTTPException(status_code=502, detail="Réponse du modèle vide.")
        return {"result": cleaned}
    except HTTPException:
        raise
    except Exception as e:
        print("ERROR /generate-test-preview:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------ Enregistrement confirmé ------------------------
class TestCreateReq(BaseModel):
    code: str
    generated_test: str
    test_type: str
    language: str
    status: Optional[str] = "confirmed"
    provider: Optional[str] = None
    model: Optional[str] = None

@app.post("/test-cases")
def create_test_case(data: TestCreateReq, _auth=Depends(require_scopes(["history:write"]))):
    doc = {
        "code": data.code,
        "generated_test": data.generated_test,
        "test_type": data.test_type,
        "language": data.language,
        "status": data.status or "confirmed",
        "provider": data.provider,
        "model": data.model,
        "created_at": datetime.utcnow(),
    }
    ins = TESTS_COL.insert_one(doc)
    doc["_id"] = str(ins.inserted_id)
    return doc

# ------------------------ Historique ------------------------
@app.get("/test-cases")
def get_test_cases(limit: int = Query(50, ge=1, le=200), _auth=Depends(require_scopes(["history:read"]))):
    items = list_test_cases(limit=limit)
    return JSONResponse(content=jsonable_encoder(items))

# ------------------------ Jobs async (LLM -> artefact) ------------------------
def _execute_test_job(code: str, test_type: str, language: str, model: Optional[str] = None, provider: Optional[str] = None):
    gen_func, active_provider = _select_generator(provider)
    active_model = _normalize_model(active_provider, model)
    result = gen_func(code, test_type, language, active_model)
    cleaned = (result or "").replace("```", "").strip()
    art_id = save_bytes(cleaned.encode("utf-8"), suffix=".txt")
    return {"generated_len": len(cleaned), "artifact_id": art_id}

@app.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_async(data: RunRequest, _auth=Depends(require_scopes(["generate:preview"]))):
    job_id = submit_job("execute_test", _execute_test_job, data.dict())
    return {"jobId": job_id}

# ------------------------ Jobs & artefacts ------------------------
@app.get("/status/{job_id}")
def job_status(job_id: str, _auth=Depends(require_scopes(["history:read"]))):
    rec = db["jobs"].find_one({"_id": ObjectId(job_id)})
    if not rec:
        raise HTTPException(status_code=404, detail="Job inconnu")
    rec["_id"] = str(rec["_id"])
    return rec

@app.get("/artifact/{artifact_id}")
def get_artifact(artifact_id: str):
    try:
        p = open_path(artifact_id)
        return FileResponse(path=str(p), filename=artifact_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Artefact introuvable")

# ------------------------ Exécutions (Selenium/Gatling/JMeter) ------------------------
class SeleniumRunRequest(BaseModel):
    url: str

@app.post("/exec/selenium", status_code=status.HTTP_202_ACCEPTED)
def exec_selenium(data: SeleniumRunRequest, _auth=Depends(require_scopes(["generate:preview"]))):
    exec_id = create_execution("selenium", data.dict())
    def _job(exec_id: str, params: dict):
        mark_running(exec_id)
        ok, logs, arts, pytest_metrics = run_selenium(params)
        # Analyse qualité si test_code fourni
        quality_analysis = None
        if params.get("test_code"):
            quality_analysis = analyze_test_quality(params["test_code"], pytest_metrics=pytest_metrics)
        mark_result(exec_id, ok, logs, arts, jacoco_metrics=None, quality_analysis=quality_analysis)
        return {"ok": ok, "artifacts": arts}
    submit_job("exec_selenium", _job, {"exec_id": exec_id, "params": data.dict()})
    return {"execId": exec_id}

@app.post("/exec/gatling", status_code=status.HTTP_202_ACCEPTED)
def exec_gatling(_auth=Depends(require_scopes(["generate:preview"]))):
    exec_id = create_execution("gatling", {})
    def _job(exec_id: str):
        mark_running(exec_id)
        ok, logs, arts = run_gatling({})
        mark_result(exec_id, ok, logs, arts)
        return {"ok": ok, "artifacts": arts}
    submit_job("exec_gatling", _job, {"exec_id": exec_id})
    return {"execId": exec_id}

@app.post("/exec/jmeter", status_code=status.HTTP_202_ACCEPTED)
def exec_jmeter(_auth=Depends(require_scopes(["generate:preview"]))):
    exec_id = create_execution("jmeter", {})
    def _job(exec_id: str):
        mark_running(exec_id)
        ok, logs, arts = run_jmeter({})
        mark_result(exec_id, ok, logs, arts)
        return {"ok": ok, "artifacts": arts}
    submit_job("exec_jmeter", _job, {"exec_id": exec_id})
    return {"execId": exec_id}

@app.get("/executions")
def list_execs(limit: int = Query(50, ge=1, le=200), _auth=Depends(require_scopes(["history:read"]))):
    return list_executions(limit)

@app.get("/executions/{exec_id}")
def exec_detail(exec_id: str, _auth=Depends(require_scopes(["history:read"]))):
    rec = get_execution(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Exécution introuvable")
    return rec

@app.post("/executions/{exec_id}/rerun", status_code=status.HTTP_202_ACCEPTED)
def rerun_execution(exec_id: str, _auth=Depends(require_scopes(["generate:preview"]))):
    rec = get_execution(exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Exécution inconnue")
    kind = rec.get("kind")
    params = rec.get("params") or {}
    new_id = create_execution(kind, params)

    def _dispatch(exec_id: str, kind: str, params: dict):
        mark_running(exec_id)
        quality_analysis = None
        if kind == "selenium":
            ok, logs, arts, pytest_metrics = run_selenium(params)
            # Analyse qualité si test_code fourni
            if params.get("test_code"):
                quality_analysis = analyze_test_quality(params["test_code"], pytest_metrics=pytest_metrics)
        elif kind == "gatling":
            ok, logs, arts = run_gatling(params)
        elif kind == "jmeter":
            ok, logs, arts = run_jmeter(params)
        else:
            ok, logs, arts = False, f"Kind inconnu: {kind}", []
        mark_result(exec_id, ok, logs, arts, jacoco_metrics=None if kind == "selenium" else None, quality_analysis=quality_analysis)
        return {"ok": ok, "artifacts": arts}

    submit_job("rerun_execution", _dispatch, {"exec_id": new_id, "kind": kind, "params": params})
    return {"execId": new_id}

# ------------------------ Lancement d'un test enregistré (Java/Maven) ------------------------
_FENCE_RE = re.compile(r"```(?:\w+)?")   # ``` ou ```java/```xml etc.

def _strip_fences(txt: str) -> str:
    """Enlève les balises de code Markdown et un éventuel BOM."""
    if not txt:
        return ""
    s = txt.replace("\r\n", "\n")
    s = s.lstrip("\ufeff")           # BOM éventuel
    s = _FENCE_RE.sub("", s)         # supprime ``` et ```xxx
    s = s.replace("```", "")
    return s.strip()


class RunTestRequest(BaseModel):
    language: Optional[str] = None
    notes: Optional[str] = None

@app.post("/test-cases/{test_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_saved_test(test_id: str, data: Optional[RunTestRequest] = None, _auth=Depends(require_scopes(["generate:preview"]))):
    doc = TESTS_COL.find_one({"_id": ObjectId(test_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Test case introuvable")

    language = (data.language if data and data.language else (doc.get("language") or "java")).lower()

    # NETTOYAGE ICI
    code_src = _strip_fences(doc.get("code") or "")
    test_src = _strip_fences(doc.get("generated_test") or "")

    params = {"language": language, "notes": (data.notes if data else None)}
    exec_id = create_execution(kind=f"{language}-maven", params=params, test_case_id=test_id)

    def _job():
        mark_running(exec_id)
        if language != "java":
            ok, logs, arts, jacoco_metrics = False, f"Langage non supporté pour l'instant: {language}", [], {}
            quality_analysis = None
        else:
            ok, logs, arts, jacoco_metrics = run_java_maven(code_src, test_src)
            # ✅ Analyse de qualité du test
            quality_analysis = analyze_test_quality(test_src, jacoco_metrics)
        mark_result(exec_id, ok, logs, arts, jacoco_metrics, quality_analysis)

    submit_job("run_saved_test", _job, {})
    return {"execId": exec_id}


@app.get("/executions/{exec_id}/logs", response_class=PlainTextResponse)
def exec_logs(exec_id: str, _auth=Depends(require_scopes(["history:read"]))):
    txt = get_execution_logs_text(exec_id)
    if txt is None:
        raise HTTPException(status_code=404, detail="Exécution introuvable")
    return txt