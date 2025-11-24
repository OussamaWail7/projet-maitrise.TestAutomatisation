# backend/selenium_runner.py
import os, re, subprocess, tempfile, shutil
from typing import Dict, List, Tuple, Optional

SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL", "http://localhost:4444/wd/hub")

def _safe_write(path: str, content: str) -> None:
    """Écrit un fichier de manière sécurisée"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")

def _requirements_txt() -> str:
    """Requirements pour les tests Selenium Python"""
    return """selenium==4.15.0
pytest==7.4.3
pytest-html==4.1.1"""

def _inject_remote_url(test_code: str) -> str:
    """
    ✅ Injecte l'URL Selenium Grid dans le code de test
    Remplace les configurations webdriver.Chrome() par webdriver.Remote()
    """
    # Si le code contient déjà webdriver.Remote, ne rien modifier
    if "webdriver.Remote" in test_code:
        return test_code

    # Remplacer webdriver.Chrome() par webdriver.Remote avec Selenium Grid
    code = test_code.replace(
        "webdriver.Chrome()",
        f"webdriver.Remote(command_executor='{SELENIUM_REMOTE_URL}', options=webdriver.ChromeOptions())"
    )

    # Remplacer webdriver.Firefox() par webdriver.Remote
    code = code.replace(
        "webdriver.Firefox()",
        f"webdriver.Remote(command_executor='{SELENIUM_REMOTE_URL}', options=webdriver.FirefoxOptions())"
    )

    # Ajouter l'import si nécessaire
    if "from selenium import webdriver" not in code and "import webdriver" not in code:
        code = "from selenium import webdriver\n" + code

    return code

def _ensure_pytest_compatible(test_code: str) -> str:
    """
    ✅ S'assure que le code de test est compatible pytest
    """
    # Si le code contient déjà des fonctions de test pytest, OK
    if re.search(r'def test_\w+\(', test_code):
        return test_code

    # Si c'est du code selenium brut, l'envelopper dans une fonction test
    if "driver" in test_code.lower() and "def test_" not in test_code:
        wrapped = f"""import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_selenium_scenario():
    \"\"\"Test Selenium généré automatiquement\"\"\"
{chr(10).join('    ' + line for line in test_code.split(chr(10)))}
"""
        return wrapped

    return test_code

def _parse_pytest_output(output: str) -> Dict:
    """
    ✅ Parse la sortie pytest pour extraire les métriques
    """
    metrics = {
        'tests_total': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'tests_skipped': 0,
        'duration_seconds': 0.0
    }

    # Parser le résumé pytest: "3 passed in 2.45s"
    match = re.search(r'(\d+) passed', output)
    if match:
        metrics['tests_passed'] = int(match.group(1))

    match = re.search(r'(\d+) failed', output)
    if match:
        metrics['tests_failed'] = int(match.group(1))

    match = re.search(r'(\d+) skipped', output)
    if match:
        metrics['tests_skipped'] = int(match.group(1))

    match = re.search(r'in ([\d\.]+)s', output)
    if match:
        metrics['duration_seconds'] = float(match.group(1))

    metrics['tests_total'] = metrics['tests_passed'] + metrics['tests_failed'] + metrics['tests_skipped']

    return metrics

def run_selenium(params: dict) -> Tuple[bool, str, List[Dict], Dict]:
    """
    ✅ Exécute les tests Selenium avec pytest et Selenium Grid

    Args:
        params: {
            'test_code': str,  # Code de test Selenium Python
            'url': str         # URL optionnelle (pour rétrocompatibilité)
        }

    Returns:
        (success, logs, artifacts, pytest_metrics)
    """
    test_code = params.get("test_code", "")

    # Si pas de code de test fourni, faire un test simple de vérification
    if not test_code or not test_code.strip():
        url = params.get("url", "https://example.org")
        test_code = f"""from selenium import webdriver

def test_basic_navigation():
    driver = webdriver.Remote(
        command_executor='{SELENIUM_REMOTE_URL}',
        options=webdriver.ChromeOptions()
    )
    try:
        driver.get('{url}')
        assert driver.title
        print(f'Page title: {{driver.title}}')
    finally:
        driver.quit()
"""

    # Créer un répertoire temporaire pour le test
    tmpdir = tempfile.mkdtemp(prefix="selenium-test-")

    try:
        # Préparer le code de test
        test_code = _inject_remote_url(test_code)
        test_code = _ensure_pytest_compatible(test_code)

        # Écrire les fichiers
        _safe_write(os.path.join(tmpdir, "requirements.txt"), _requirements_txt())
        _safe_write(os.path.join(tmpdir, "test_selenium.py"), test_code)

        logs = [f"[SELENIUM] Selenium Grid URL: {SELENIUM_REMOTE_URL}"]

        # Installer les dépendances
        logs.append("[SELENIUM] Installation des dépendances...")
        install_cmd = ["pip", "install", "-q", "-r", os.path.join(tmpdir, "requirements.txt")]
        p = subprocess.Popen(install_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(timeout=60)

        if p.returncode != 0:
            logs.append(f"[SELENIUM] Avertissement lors de l'installation: {err}")

        # Exécuter les tests avec pytest
        logs.append("[SELENIUM] Exécution des tests avec pytest...")
        pytest_cmd = [
            "pytest",
            os.path.join(tmpdir, "test_selenium.py"),
            "-v",
            "--tb=short",
            f"--html={os.path.join(tmpdir, 'report.html')}",
            "--self-contained-html"
        ]

        p = subprocess.Popen(pytest_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=tmpdir)
        out, err = p.communicate(timeout=180)  # 3 minutes max

        success = p.returncode == 0

        # Combiner la sortie
        full_output = out + ("\n--- STDERR ---\n" + err if err else "")
        logs.append(full_output)

        # Parser les métriques
        metrics = _parse_pytest_output(full_output)
        logs.append(f"[SELENIUM] Tests: {metrics['tests_total']}, Passed: {metrics['tests_passed']}, Failed: {metrics['tests_failed']}")

        # Collecter les artifacts
        artifacts: List[Dict] = []

        # Rapport HTML pytest
        report_html = os.path.join(tmpdir, "report.html")
        if os.path.exists(report_html):
            size = os.path.getsize(report_html)
            artifacts.append({"name": "report.html", "url": None, "size": size})

        # Screenshots si présents
        for file in os.listdir(tmpdir):
            if file.endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(tmpdir, file)
                size = os.path.getsize(filepath)
                artifacts.append({"name": file, "url": None, "size": size})

        return success, "\n".join(logs) + "\n", artifacts, metrics

    except subprocess.TimeoutExpired:
        return False, "[SELENIUM] ERREUR: Timeout (180s dépassé)\n", [], {}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return False, f"[SELENIUM] ERREUR: {e}\n{error_trace}\n", [], {}
    finally:
        # Nettoyer le répertoire temporaire
        shutil.rmtree(tmpdir, ignore_errors=True)
