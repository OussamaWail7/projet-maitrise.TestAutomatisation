# backend/mistral_service.py
import os
import requests
from typing import Optional
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration Mistral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "https://api.mistral.ai/v1/chat/completions")
DEFAULT_MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

def _build_system_prompt(test_type: str, language: str) -> str:
    """Construit le prompt système selon le type de test."""
    if test_type == "rest-assured":
        return f"""Tu es un expert en tests d'API REST avec RestAssured pour {language}.
Génère un test RestAssured complet et fonctionnel qui :
- Utilise les annotations JUnit 5 (@Test, @BeforeEach, etc.)
- Teste tous les endpoints de l'API
- Vérifie les codes HTTP, les corps de réponse, et les headers
- Couvre les cas nominaux et d'erreur
- Suit les bonnes pratiques RestAssured

Retourne UNIQUEMENT le code du test, sans explication ni markdown."""

    elif test_type == "unit":
        return f"""Tu es un expert en tests unitaires pour {language}.
Génère des tests unitaires complets et fonctionnels qui :
- Utilisent JUnit 5 (@Test, @BeforeEach, @AfterEach)
- Testent toutes les méthodes publiques de la classe
- Couvrent les cas nominaux, limites et d'erreur
- Utilisent des assertions pertinentes (assertEquals, assertTrue, assertThrows, etc.)
- Suivent les bonnes pratiques de tests unitaires
- Atteignent une couverture de code élevée

Retourne UNIQUEMENT le code du test, sans explication ni markdown."""

    elif test_type == "selenium":
        return f"""Tu es un expert en tests E2E avec Selenium pour {language}.
Génère un test Selenium complet et fonctionnel qui :
- Configure le WebDriver correctement
- Teste les interactions utilisateur (clics, saisies, navigation)
- Vérifie les éléments de la page et leur état
- Gère les attentes explicites (WebDriverWait)
- Nettoie les ressources (@AfterEach)
- Suit les bonnes pratiques Selenium

Retourne UNIQUEMENT le code du test, sans explication ni markdown."""

    return f"Génère un test {test_type} complet en {language}. Retourne UNIQUEMENT le code, sans explication."

def _build_user_prompt(code: str, test_type: str, language: str) -> str:
    """Construit le prompt utilisateur avec le code source."""
    return f"""Génère un test {test_type} complet en {language} pour le code suivant :

```{language.lower()}
{code}
```

Assure-toi que le test :
1. Compile sans erreur
2. Contient plusieurs méthodes de test (@Test)
3. Utilise des assertions variées et pertinentes
4. Couvre les cas nominaux ET les cas d'erreur
5. Suit les conventions de nommage (nom du test explicite)
6. Est prêt à l'exécution

Retourne UNIQUEMENT le code du test, sans balises markdown ni explication."""

def generate_test_case_with_mistral(
    code: str,
    test_type: str = "rest-assured",
    language: str = "java",
    model: Optional[str] = None
) -> str:
    """
    Génère un cas de test avec Mistral AI.

    Args:
        code: Code source à tester
        test_type: Type de test (unit, rest-assured, selenium)
        language: Langage de programmation
        model: Modèle Mistral à utiliser (optionnel)

    Returns:
        Code du test généré

    Raises:
        ValueError: Si la clé API Mistral est manquante
        Exception: Si l'appel API échoue
    """
    if not MISTRAL_API_KEY:
        raise ValueError(
            "Clé API Mistral manquante. Ajoutez MISTRAL_API_KEY dans votre fichier .env"
        )

    system_prompt = _build_system_prompt(test_type, language)
    user_prompt = _build_user_prompt(code, test_type, language)

    payload = {
        "model": model or DEFAULT_MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,  # Moins de créativité pour du code
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            MISTRAL_API_URL,
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code == 401:
            raise Exception("Clé API Mistral invalide. Vérifiez votre MISTRAL_API_KEY dans .env")
        elif response.status_code == 429:
            raise Exception("Quota Mistral dépassé. Attendez quelques instants ou changez de provider.")
        elif response.status_code == 400:
            error_detail = response.json().get("message", "Requête invalide")
            raise Exception(f"Erreur Mistral (400): {error_detail}")
        elif response.status_code != 200:
            raise Exception(f"Erreur Mistral API (status {response.status_code}): {response.text}")

        response.raise_for_status()
        data = response.json()

        # Extraction du contenu généré
        if "choices" not in data or len(data["choices"]) == 0:
            raise Exception("Réponse Mistral vide ou invalide")

        content = data["choices"][0].get("message", {}).get("content", "")

        if not content or not content.strip():
            raise Exception("Le modèle Mistral n'a généré aucun contenu")

        return content.strip()

    except requests.exceptions.Timeout:
        raise Exception("Timeout lors de l'appel à l'API Mistral (60s). Réessayez.")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Impossible de se connecter à l'API Mistral ({MISTRAL_API_URL})")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erreur lors de l'appel Mistral: {str(e)}")

def list_available_models() -> list:
    """Liste les modèles Mistral disponibles"""
    if not MISTRAL_API_KEY:
        return []

    # Modèles Mistral connus (l'API ne fournit pas de liste dynamique)
    known_models = [
        {"id": "mistral-small-latest", "name": "Mistral Small", "description": "Rapide et économique", "provider": "mistral"},
        {"id": "mistral-medium-latest", "name": "Mistral Medium", "description": "Équilibré", "provider": "mistral"},
        {"id": "mistral-large-latest", "name": "Mistral Large", "description": "Le plus performant", "provider": "mistral"},
    ]

    try:
        # Vérifier que l'API est accessible
        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
        r = requests.get("https://api.mistral.ai/v1/models", headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            # Retourner les modèles réels si disponibles
            models = data.get("data", [])
            if models:
                return [
                    {
                        "id": m["id"],
                        "name": m.get("id", "").replace("-", " ").title(),
                        "description": m.get("description", ""),
                        "provider": "mistral"
                    }
                    for m in models
                ]
        # Sinon retourner les modèles connus
        return known_models
    except Exception as e:
        print(f"Erreur lors de la récupération des modèles Mistral: {e}")
        # Retourner les modèles connus même en cas d'erreur
        return known_models
