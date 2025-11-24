import os
from textwrap import dedent
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ✅ Rendre la clé optionnelle pour permettre l'utilisation exclusive d'Ollama
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

DEFAULT_GEMINI_MODEL = os.getenv("GOOGLE_MODEL", "gemini-flash-latest")

GOAL_BY_TYPE = {
    "unit": "Écris des tests unitaires couvrant cas nominal et cas d'erreur (limite/exception).",
    "rest-assured": "Écris des tests d'API HTTP avec requêtes et assertions (statut, en-têtes, corps).",
    "selenium": "Écris des tests E2E navigateur robustes (localisateurs stables, actions, assertions).",
}

FRAMEWORK_HINT = {
    ("java","unit"): "JUnit 5 + AssertJ",
    ("python","unit"): "pytest",
    ("javascript","unit"): "Jest",
    ("typescript","unit"): "Jest (ts-jest)",
    ("csharp","unit"): "xUnit",
    ("ruby","unit"): "RSpec",
    ("go","unit"): "testing",

    ("java","rest-assured"): "REST Assured + JUnit 5",
    ("python","rest-assured"): "requests + pytest",
    ("javascript","rest-assured"): "supertest + Jest",
    ("typescript","rest-assured"): "supertest + Jest",
    ("csharp","rest-assured"): "RestSharp + xUnit",
    ("ruby","rest-assured"): "Faraday + RSpec",
    ("go","rest-assured"): "net/http + testing",

    ("java","selenium"): "Selenium WebDriver + JUnit 5",
    ("python","selenium"): "selenium + pytest",
    ("javascript","selenium"): "selenium-webdriver + Jest",
    ("typescript","selenium"): "selenium-webdriver + Jest",
    ("csharp","selenium"): "Selenium WebDriver + xUnit",
    ("ruby","selenium"): "selenium-webdriver + RSpec",
    ("go","selenium"): "chromedp (équivalent Selenium en Go)",
}

def _build_prompt(code: str, test_type: str, language: str) -> str:
    goal = GOAL_BY_TYPE.get(test_type, "")
    hint = FRAMEWORK_HINT.get((language, test_type), "")

    # Few-shot examples par langage/type
    example = _get_example(language, test_type)

    return dedent(f"""
    Tu es un expert en AUTOMATISATION DE TESTS {language.upper()}.

    OBJECTIF: {goal}
    FRAMEWORK: {hint}

    RÈGLES STRICTES:
    1. Code COMPLET et COMPILABLE (tous les imports)
    2. Au moins 3 tests: nominal + limite + erreur
    3. Assertions SPÉCIFIQUES et PRÉCISES
    4. Noms de tests DESCRIPTIFS (shouldDoSomethingWhen...)
    5. Setup/Teardown si nécessaire
    6. AUCUNE explication, AUCUNE balise ```, SEULEMENT le code

    EXEMPLE DE BONNE PRATIQUE:
    {example}

    CODE À TESTER:
    ---
    {code}
    ---

    GÉNÈRE le test complet maintenant (sans ```):
    """).strip()

def _get_example(language: str, test_type: str) -> str:
    """Retourne un exemple de test pour few-shot learning"""
    examples = {
        ("java", "unit"): """
// Input: public int add(int a, int b) { return a + b; }
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    @Test
    void shouldAddTwoPositiveNumbers() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(2, 3));
    }

    @Test
    void shouldHandleNegativeNumbers() {
        Calculator calc = new Calculator();
        assertEquals(-1, calc.add(-3, 2));
    }

    @Test
    void shouldHandleZero() {
        Calculator calc = new Calculator();
        assertEquals(5, calc.add(5, 0));
    }
}""",
        ("java", "rest-assured"): """
// Input: @GetMapping("/users/{id}") public User getUser(Long id)
import io.restassured.RestAssured;
import org.junit.jupiter.api.Test;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

class UserApiTest {
    @Test
    void shouldReturnUserWhenIdExists() {
        given()
            .pathParam("id", 1)
        .when()
            .get("/users/{id}")
        .then()
            .statusCode(200)
            .body("id", equalTo(1))
            .body("name", notNullValue());
    }

    @Test
    void shouldReturn404WhenUserNotFound() {
        given()
            .pathParam("id", 99999)
        .when()
            .get("/users/{id}")
        .then()
            .statusCode(404);
    }
}""",
        ("python", "unit"): """
# Input: def add(a, b): return a + b
import pytest

def test_add_positive_numbers():
    assert add(2, 3) == 5

def test_add_negative_numbers():
    assert add(-3, 2) == -1

def test_add_with_zero():
    assert add(5, 0) == 5

def test_add_type_error():
    with pytest.raises(TypeError):
        add("a", 3)""",
        ("python", "selenium"): """
# Input: Page de connexion à tester
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pytest

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_login_success(driver):
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("user@test.com")
    driver.find_element(By.ID, "password").send_keys("password123")
    driver.find_element(By.ID, "loginBtn").click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "dashboard"))
    )
    assert "Dashboard" in driver.title

def test_login_invalid_credentials(driver):
    driver.get("https://example.com/login")
    driver.find_element(By.ID, "username").send_keys("wrong@test.com")
    driver.find_element(By.ID, "password").send_keys("wrong")
    driver.find_element(By.ID, "loginBtn").click()

    error = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
    )
    assert "Invalid credentials" in error.text"""
    }

    return examples.get((language, test_type), "# Aucun exemple disponible, génère selon les règles")

def generate_test_case_with_gemini(code: str, test_type: str, language: str, model: Optional[str] = None) -> str:
    # ✅ Vérifier que la clé API est configurée avant de générer
    if not api_key:
        raise ValueError(
            "Clé API Google manquante dans .env (GOOGLE_API_KEY). "
            "Veuillez la configurer ou utiliser le provider 'ollama' à la place."
        )

    prompt = _build_prompt(code, test_type, language)
    model_name = model or DEFAULT_GEMINI_MODEL
    m = genai.GenerativeModel(model_name)
    out = m.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,  # ✅ Augmenté de 0.2 à 0.4 pour plus de créativité
            top_p=0.95,       # ✅ Augmenté pour plus de diversité
            top_k=40,         # ✅ Ajouté pour meilleure qualité
            candidate_count=1,
        )
    )
    text = (getattr(out, "text", "") or "").strip()
    return text.replace("```", "").strip()

def list_available_models() -> list:
    """Liste les modèles Gemini disponibles"""
    if not api_key:
        return []
    try:
        models = genai.list_models()
        return [
            {
                "id": m.name.replace("models/", ""),
                "name": m.display_name,
                "description": m.description or "",
                "provider": "gemini"
            }
            for m in models
            if "generateContent" in m.supported_generation_methods
        ]
    except Exception as e:
        print(f"Erreur lors de la récupération des modèles Gemini: {e}")
        return []
