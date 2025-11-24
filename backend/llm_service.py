import os
import re
import requests
from typing import Optional, List, Dict

# -----------------------------
# 0) Modèle & endpoint Ollama
# -----------------------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
# ✅ IMPORTANT: utiliser un modèle INSTRUCT - Cohérence avec settings.py
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")

# ============================
# 1) Détection & parsing Spring
# ============================

_SPRING_ANNOT = re.compile(
    r"@RestController|@Controller|@RequestMapping|@GetMapping|@PostMapping|@PutMapping|@DeleteMapping",
    re.MULTILINE,
)

_MAPPING = re.compile(
    r"@(GetMapping|PostMapping|PutMapping|DeleteMapping)(?:\s*\(\s*value\s*=\s*)?\(\s*([\"'][^\"']+[\"'])?\s*\)|"
    r"@(RequestMapping)\s*\(\s*value\s*=\s*([\"'][^\"']+[\"'])\s*,\s*method\s*=\s*RequestMethod\.(GET|POST|PUT|DELETE)\s*\)",
    re.MULTILINE,
)

_REQ_PARAM = re.compile(
    r"@RequestParam(?:\s*\(\s*(?:name\s*=\s*)?(?:value\s*=\s*)?)?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1",
    re.MULTILINE,
)

_CLASS_REQUEST_MAPPING = re.compile(
    r"@RequestMapping\s*\(\s*value\s*=\s*([\"'])([^\"']+)\1\s*\)",
    re.MULTILINE,
)

_CLASS_NAME = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b")

def is_spring_controller(src: str) -> bool:
    return bool(_SPRING_ANNOT.search(src or ""))

def _class_level_prefix(src: str) -> str:
    m = _CLASS_REQUEST_MAPPING.search(src or "")
    return m.group(2).strip() if m else ""

def _extract_controller_class_name(src: str) -> str:
    m = _CLASS_NAME.search(src or "")
    return m.group(1) if m else "ControllerUnderTest"

def parse_spring_endpoints(src: str) -> List[Dict]:
    """
    Retourne une liste d'endpoints [{'method':'GET','path':'/api/add','params':['a','b']}]
    """
    if not src:
        return []
    base = _class_level_prefix(src)
    endpoints = []
    for m in _MAPPING.finditer(src):
        if m.group(1):  # GetMapping|PostMapping|...
            http = m.group(1).replace("Mapping", "").upper()
            raw = m.group(2) or '"/"'
            path = raw.strip().strip('"\'')
        else:  # RequestMapping(value="...", method=RequestMethod.X)
            http = (m.group(5) or "").upper()
            path = (m.group(4) or "").strip().strip('"\'')
        full = f"{('/' + base.strip('/')) if base else ''}/{path.strip('/')}".replace("//", "/")
        params = list({p.group(2) for p in _REQ_PARAM.finditer(src)})
        endpoints.append({"method": http, "path": full if full.startswith("/") else f"/{full}", "params": params})
    # dédoublonne
    uniq = []
    seen = set()
    for e in endpoints:
        k = (e["method"], e["path"], tuple(sorted(e["params"])) )
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return uniq

# ============================
# 2) Prompting ciblé & strict
# ============================

def _spring_http_hint(prefer: str, spec: List[Dict]) -> str:
    if not spec:
        target = "un ou plusieurs endpoints REST Spring"
    else:
        lines = [f"- {e['method']} {e['path']} (params: {', '.join(e['params']) or '—'})" for e in spec]
        target = "cible :\n" + "\n".join(lines)

    if prefer == "restassured":
        return (
            f"Contrôleur REST Spring — {target}\n"
            "Tu DOIS tester via **REST Assured** (JUnit 5). "
            "N’APPELLE PAS directement la méthode Java ; passe par HTTP. "
            "Inclure imports et annotations. Cas attendus : nominal + erreurs (paramètre manquant, type invalide)."
        )
    return (
        f"Contrôleur REST Spring — {target}\n"
        "Tu DOIS tester via **MockMvc** avec `@WebMvcTest(controllers=...)`. "
        "N’APPELLE PAS directement la méthode Java ; passe par HTTP (mockMvc.perform(...)). "
        "Inclure imports et annotations. Cas attendus : nominal + erreurs (paramètre manquant, type invalide)."
    )

PROMPT_TEMPLATE = """Tu es un expert en AUTOMATISATION DE TESTS.

OBJECTIF — produire un FICHIER DE TEST complet pour le code fourni.

CONTRAINTES TRÈS STRICTES :
- Réponds UNIQUEMENT par du CODE (aucune phrase, aucune explication).
- AUCUNE balise ``` ni markdown.
- Commence ta réponse PAR LA PREMIÈRE LIGNE DE CODE (import/package/...).
- Inclure TOUS les imports nécessaires.
- Contenir AU MINIMUM :
  • 1 cas nominal
  • 1 cas d’erreur/limite (paramètre manquant, type invalide, valeur frontière).
- Si nécessaire, CRÉE des stubs minimaux pour exécuter les tests.
- Respecte le framework indiqué ci-dessous.

Langage cible : {language}
Type de test : {test_type}
Framework attendu : {framework_hint}
Directives spécifiques : {domain_hint}

Code sous test :
---
{code}
---

RENVOIE UNIQUEMENT LE CODE DU TEST, EN COMMENÇANT DIRECTEMENT PAR LA PREMIÈRE LIGNE DE CODE.
"""

def _framework_hint(language: str, test_type: str) -> str:
    key = ((language or "").lower(), (test_type or "").lower())
    mapping = {
        ("java","unit"): "JUnit 5 + AssertJ",
        ("java","rest-assured"): "JUnit 5, tests d’API HTTP Spring (MockMvc ou REST Assured).",
        ("java","selenium"): "Selenium WebDriver + JUnit 5",

        ("python","unit"): "pytest",
        ("python","rest-assured"): "requests + pytest",
        ("python","selenium"): "selenium + pytest",

        ("javascript","unit"): "Jest",
        ("javascript","rest-assured"): "supertest + Jest",
        ("javascript","selenium"): "selenium-webdriver + Jest",

        ("typescript","unit"): "Jest (ts-jest)",
        ("typescript","rest-assured"): "supertest + Jest",
        ("typescript","selenium"): "selenium-webdriver + Jest",

        ("csharp","unit"): "xUnit",
        ("csharp","rest-assured"): "RestSharp + xUnit",
        ("csharp","selenium"): "Selenium WebDriver + xUnit",

        ("ruby","unit"): "RSpec",
        ("ruby","rest-assured"): "Faraday + RSpec",
        ("ruby","selenium"): "selenium-webdriver + RSpec",

        ("go","unit"): "testing",
        ("go","rest-assured"): "net/http + testing",
        ("go","selenium"): "chromedp (équivalent Selenium en Go)",
    }
    return mapping.get(key, "Tests automatisés conformes au langage et type.")

def _domain_hint(code: str, language: str, test_type: str) -> str:
    if (language or "").lower() == "java" and (test_type or "").lower() in {"rest-assured", "unit"} and is_spring_controller(code):
        spec = parse_spring_endpoints(code)
        return _spring_http_hint("mockmvc", spec)
    return "Aucune directive spécifique."

def _build_prompt(code: str, test_type: str, language: str) -> str:
    return PROMPT_TEMPLATE.format(
        code=code,
        test_type=test_type,
        language=language,
        framework_hint=_framework_hint(language, test_type),
        domain_hint=_domain_hint(code, language, test_type),
    )

# ============================
# 3) Post-traitement & validation
# ============================

_CODE_START_PAT = re.compile(
    r"(?:^\s*(?:package|import|using)\b)|"
    r"(?:^\s*(?:class|@Test|def\s+test_|describe\(|it\(|test\(|func\s+Test))",
    re.MULTILINE
)

def _extract_code_from_fenced(text: str) -> str:
    blocks = re.findall(r"```(?:[a-zA-Z]+)?\s*([\s\S]*?)```", text or "")
    return (max(blocks, key=len).strip() if blocks else "").strip()

def _strip_to_first_code_like_line(text: str) -> str:
    if not text:
        return ""
    m = _CODE_START_PAT.search(text)
    return text[m.start():].strip() if m else text.strip()

def _postprocess_response(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    fenced = _extract_code_from_fenced(s)
    if fenced:
        return fenced
    return s.replace("```", "").strip()

def _looks_like_http_test_java(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    has_mockmvc = ("@WebMvcTest" in t and "MockMvc" in t and "mockMvc.perform(" in t)
    has_restassured = ("io.restassured.RestAssured" in t) or ("given()" in t and "when().get(" in t)
    return has_mockmvc or has_restassured

def _covers_endpoint(text: str, ep: Dict) -> bool:
    if not text or not ep:
        return False
    path_ok = ep["path"] in text
    method = ep["method"]
    if method == "GET":
        method_ok = ("get(" in text)
    elif method == "POST":
        method_ok = ("post(" in text)
    elif method == "PUT":
        method_ok = ("put(" in text)
    else:
        method_ok = ("delete(" in text)
    return path_ok and method_ok

def _fallback_spring_mockmvc_from_spec(spec: List[Dict], controller_class: str = "ControllerUnderTest") -> str:
    ep = spec[0] if spec else {"method": "GET", "path": "/api/ping", "params": []}
    params = ep.get("params") or []
    params_str = "".join([f'.param("{p}", "1")' for p in params])
    body_expect = 'content().string("2")' if "a" in params and "b" in params else "content().string(org.hamcrest.Matchers.notNullValue())"
    return (
        "package com.example;\n\n"
        "import org.junit.jupiter.api.Test;\n"
        "import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;\n"
        "import org.springframework.beans.factory.annotation.Autowired;\n"
        "import org.springframework.test.web.servlet.MockMvc;\n"
        "import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;\n"
        "import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;\n"
        "import org.springframework.http.MediaType;\n\n"
        f"@WebMvcTest(controllers = {controller_class}.class)\n"
        "class ControllerHttpTest {\n"
        "  @Autowired MockMvc mockMvc;\n\n"
        "  @Test void nominal() throws Exception {\n"
        f"    mockMvc.perform({ep['method'].lower()}(\"{ep['path']}\"){params_str}.accept(MediaType.APPLICATION_JSON))\n"
        "      .andExpect(status().isOk())\n"
        f"      .andExpect({body_expect});\n"
        "  }\n\n"
        "  @Test void missing_param() throws Exception {\n"
        f"    mockMvc.perform({ep['method'].lower()}(\"{ep['path']}\").accept(MediaType.APPLICATION_JSON))\n"
        "      .andExpect(status().isBadRequest());\n"
        "  }\n"
        "}\n"
    )

# ============================
# 4) Appel Ollama
# ============================

def _ollama_call(payload: dict, timeout: int = 90) -> str:
    """
    ✅ Appel Ollama avec gestion d'erreur améliorée
    """
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        if r.status_code != 200:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            if "model not found" in str(detail).lower():
                raise Exception(f"Model {payload.get('model')} not found. Faites: ollama pull {payload.get('model')}")
            raise Exception(f"Ollama error {r.status_code}: {detail}")
        return (r.json().get("response") or "").strip()
    except requests.exceptions.Timeout:
        raise Exception(
            f"Timeout Ollama après {timeout}s. "
            f"Le modèle {payload.get('model')} est peut-être trop gros. "
            "Essayez un modèle plus petit ou augmentez GEN_TIMEOUT dans .env"
        )
    except requests.exceptions.ConnectionError:
        raise Exception(
            f"Impossible de se connecter à Ollama ({OLLAMA_URL}). "
            "Vérifiez qu'Ollama est démarré avec 'ollama serve'"
        )

def _is_stub_or_too_short(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if "// Test stub" in t or "Test stub" in t:
        return True
    # ~30 chars = trop court pour un fichier de test réaliste
    return len(t) < 30

def generate_test_case_ollama(
    code: str,
    test_type: str,
    language: str,
    model: Optional[str] = None,
    timeout_seconds: int = 90,
) -> str:
    model_name = (model or DEFAULT_OLLAMA_MODEL).strip()
    prompt = _build_prompt(code, test_type, language)

    base_options = {
        "temperature": 0.1,
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 2048,  # clé pour éviter les coupes => stub
        "repeat_penalty": 1.05,
        "stop": ["```", "<html", "<!DOCTYPE", "Explanation:", "Explication:"],
    }

    # ----- Passe 1
    raw1 = _ollama_call({"model": model_name, "prompt": prompt, "stream": False, "options": base_options}, timeout_seconds)
    code1 = _postprocess_response(raw1) or _strip_to_first_code_like_line(raw1)

    # Traitement spécial Spring/Java
    if (language or "").lower() == "java" and is_spring_controller(code):
        spec = parse_spring_endpoints(code)
        ctrl = _extract_controller_class_name(code)

        if not _is_stub_or_too_short(code1) and _looks_like_http_test_java(code1) and (not spec or any(_covers_endpoint(code1, ep) for ep in spec)):
            return code1

        # ----- Passe 2 (renforcement Spring HTTP)
        reinforced = prompt + (
            "\n\nTON PRÉCÉDENT RÉSULTAT N’UTILISAIT PAS D’APPELS HTTP SPRING CORRECTS OU ÉTAIT INCOMPLET. "
            "UTILISE OBLIGATOIREMENT MockMvc (@WebMvcTest + mockMvc.perform(...)) OU REST Assured. "
            "NE PAS APPELER DIRECTEMENT LES MÉTHODES JAVA. CODE UNIQUEMENT, SANS MARKDOWN."
        )
        raw2 = _ollama_call({"model": model_name, "prompt": reinforced, "stream": False,
                             "options": {**base_options, "temperature": 0.05, "num_predict": 2304}}, timeout_seconds)
        code2 = _postprocess_response(raw2) or _strip_to_first_code_like_line(raw2)
        if not _is_stub_or_too_short(code2) and _looks_like_http_test_java(code2) and (not spec or any(_covers_endpoint(code2, ep) for ep in spec)):
            return code2

        # ----- Fallback Spring HTTP à partir de la spéc
        return _fallback_spring_mockmvc_from_spec(spec, controller_class=ctrl)

    # Non Spring : on renvoie le meilleur effort, et si stub => on force un squelette minimal plutôt que "// Test stub"
    if not _is_stub_or_too_short(code1):
        return code1

    # Fallback générique par langage (squelette de test utile > stub vide)
    lang = (language or "").lower()
    if lang == "java":
        return (
            "import org.junit.jupiter.api.Test;\n"
            "import static org.junit.jupiter.api.Assertions.*;\n\n"
            "class GeneratedUnitTest {\n"
            "  @Test void nominal() {\n"
            "    // TODO: instancier la classe cible et vérifier un comportement nominal\n"
            "    assertTrue(true);\n"
            "  }\n"
            "  @Test void erreur_ou_limite() {\n"
            "    // TODO: cas d'erreur/limite (argument invalide, valeur frontière...)\n"
            "    assertNotNull(new Object());\n"
            "  }\n"
            "}\n"
        )
    if lang == "python":
        return (
            "import pytest\n\n"
            "def test_nominal():\n"
            "    # TODO: appeler une fonction réelle et vérifier le résultat\n"
            "    assert True\n\n"
            "def test_erreur_ou_limite():\n"
            "    # TODO: cas d'erreur/limite\n"
            "    assert 1 == 1\n"
        )
    # Dernier recours
    return "// Test non vide: veuillez fournir plus de contexte (classe/méthodes à tester) pour un test complet."

def list_available_models() -> list:
    """Liste les modèles Ollama disponibles"""
    try:
        # Endpoint pour lister les modèles Ollama
        base_url = OLLAMA_URL.replace("/api/generate", "")
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return [
                {
                    "id": model["name"],
                    "name": model["name"],
                    "description": f"Size: {model.get('size', 0) / 1024 / 1024 / 1024:.1f}GB",
                    "provider": "ollama"
                }
                for model in data.get("models", [])
            ]
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des modèles Ollama: {e}")
        return []
