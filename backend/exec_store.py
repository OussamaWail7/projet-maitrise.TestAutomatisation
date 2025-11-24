# backend/exec_store.py
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# Store mémoire simple
_EXEC: Dict[str, Dict[str, Any]] = {}

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def create_execution(kind: str, params: dict | None = None, test_case_id: str | None = None) -> str:
    exec_id = str(uuid.uuid4())
    _EXEC[exec_id] = {
        "id": exec_id,
        "kind": kind,
        "status": "queued",
        "created_at": _now_iso(),
        "started_at": None,
        "finished_at": None,
        "params": params or {},
        "test_case_id": test_case_id,
        "notes": None,
        "logs": "",          # IMPORTANT: champ toujours présent (string)
        "logs_url": f"/executions/{exec_id}/logs",
        "artifacts": [],     # liste de dicts {name,url,size}
        "language": (params or {}).get("language"),
        "jacoco_metrics": None,  # ✅ Métriques de couverture JaCoCo
        "quality_analysis": None,  # ✅ Analyse de qualité du test
    }
    return exec_id

def mark_running(exec_id: str, notes: Optional[str] = None) -> None:
    ex = _EXEC.get(exec_id)
    if not ex:
        return
    ex["status"] = "running"
    ex["started_at"] = _now_iso()
    if notes:
        ex["notes"] = notes

def mark_result(exec_id: str, ok: bool, logs: str, artifacts: List[dict] | None = None, jacoco_metrics: dict | None = None, quality_analysis: dict | None = None) -> None:
    ex = _EXEC.get(exec_id)
    if not ex:
        return
    ex["status"] = "success" if ok else "failed"
    ex["finished_at"] = _now_iso()
    # Toujours poser un string, jamais None
    ex["logs"] = str(logs or "")
    ex["artifacts"] = artifacts or []
    # ✅ Stocker les métriques JaCoCo si disponibles
    if jacoco_metrics:
        ex["jacoco_metrics"] = jacoco_metrics
    # ✅ Stocker l'analyse de qualité si disponible
    if quality_analysis:
        ex["quality_analysis"] = quality_analysis

def get_execution(exec_id: str) -> Optional[Dict[str, Any]]:
    return _EXEC.get(exec_id)

def list_executions(limit: int = 50) -> List[Dict[str, Any]]:
    # tri inverse par date de création
    items = sorted(_EXEC.values(), key=lambda x: x.get("created_at") or "", reverse=True)
    return items[:limit]

def get_execution_logs_text(exec_id: str) -> Optional[str]:
    ex = _EXEC.get(exec_id)
    if not ex:
        return None
    return ex.get("logs", "")
