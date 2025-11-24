# backend/artifacts.py
import os, uuid
from pathlib import Path
from typing import List

# Repertoire de base pour stocker les artifacts
_BASE = Path(__file__).resolve().parent / "artifacts"
_BASE.mkdir(parents=True, exist_ok=True)

def save_bytes(data: bytes, suffix: str = "") -> str:
    """
    Sauvegarde des donnees binaires en tant qu'artifact

    Args:
        data: Donnees binaires a sauvegarder
        suffix: Suffixe du fichier (par ex. ".png", ".html", ".jar")

    Returns:
        ID de l'artifact (nom du fichier)

    Example:
        artifact_id = save_bytes(screenshot_data, ".png")
        # Retourne quelque chose comme "a1b2c3d4e5f6.png"
    """
    name = f"{uuid.uuid4().hex}{suffix}"
    (_BASE / name).write_bytes(data)
    return name

def save_text(text: str, suffix: str = ".txt") -> str:
    """
    Sauvegarde un texte en tant qu'artifact

    Args:
        text: Texte a sauvegarder
        suffix: Suffixe du fichier (par ex. ".txt", ".log", ".xml")

    Returns:
        ID de l'artifact
    """
    return save_bytes(text.encode("utf-8"), suffix)

def open_path(artifact_id: str) -> Path:
    """
    Recupere le chemin d'un artifact par son ID

    Args:
        artifact_id: ID de l'artifact (nom du fichier)

    Returns:
        Path vers l'artifact

    Raises:
        FileNotFoundError: Si l'artifact n'existe pas
    """
    p = _BASE / artifact_id
    if not p.exists():
        raise FileNotFoundError(f"Artifact introuvable: {artifact_id}")
    return p

def list_artifacts() -> List[str]:
    """
    Liste tous les artifacts disponibles

    Returns:
        Liste des IDs d'artifacts
    """
    return [f.name for f in _BASE.iterdir() if f.is_file()]

def delete_artifact(artifact_id: str) -> bool:
    """
    Supprime un artifact

    Args:
        artifact_id: ID de l'artifact a supprimer

    Returns:
        True si supprime, False si n'existait pas
    """
    try:
        p = _BASE / artifact_id
        p.unlink()
        return True
    except FileNotFoundError:
        return False

def get_artifact_size(artifact_id: str) -> int:
    """
    Recupere la taille d'un artifact en octets

    Args:
        artifact_id: ID de l'artifact

    Returns:
        Taille en octets

    Raises:
        FileNotFoundError: Si l'artifact n'existe pas
    """
    p = open_path(artifact_id)
    return p.stat().st_size
