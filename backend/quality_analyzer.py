# backend/quality_analyzer.py
import re
from typing import Dict, List, Tuple, Optional

def _detect_test_language(test_code: str) -> str:
    """
    Détecte le langage du test (java, python, javascript, etc.)
    """
    code = test_code or ""

    # Python/Selenium
    if re.search(r'def test_\w+\(|import pytest|from selenium|driver\.', code):
        return "python"

    # Java
    if re.search(r'@Test|public class|import org\.junit', code):
        return "java"

    # JavaScript/TypeScript
    if re.search(r'describe\(|it\(|test\(|expect\(', code):
        return "javascript"

    return "unknown"

def _count_assertions(test_code: str) -> int:
    """Compte le nombre d'assertions dans le code de test."""
    patterns = [
        r'\bassert\w+\(',  # assert*, assertEquals, assertTrue, etc.
        r'\.should\(',     # RestAssured .should()
        r'\.expect\(',     # Expect assertions
        r'verify\(',       # Mockito verify
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, test_code or "", re.IGNORECASE))
    return count

def _count_test_methods(test_code: str) -> int:
    """Compte le nombre de méthodes de test (@Test)."""
    return len(re.findall(r'@Test\s+(?:public\s+)?void\s+\w+', test_code or ""))

def _has_setup_teardown(test_code: str) -> bool:
    """Vérifie si le test a des méthodes setup/teardown."""
    setup_patterns = [r'@Before\b', r'@BeforeEach\b', r'@BeforeAll\b']
    teardown_patterns = [r'@After\b', r'@AfterEach\b', r'@AfterAll\b']
    code = test_code or ""
    has_setup = any(re.search(p, code) for p in setup_patterns)
    has_teardown = any(re.search(p, code) for p in teardown_patterns)
    return has_setup or has_teardown

def _has_exception_handling(test_code: str) -> bool:
    """Vérifie si le test gère les exceptions."""
    patterns = [
        r'@Test\s*\(\s*expected\s*=',  # @Test(expected=...)
        r'assertThrows\(',              # assertThrows
        r'try\s*\{',                    # try-catch
    ]
    return any(re.search(p, test_code or "") for p in patterns)

def _has_comments(test_code: str) -> bool:
    """Vérifie si le test contient des commentaires."""
    return bool(re.search(r'//|/\*|\*/|#', test_code or ""))

# ===============================================
# Fonctions d'analyse pour Python/Selenium
# ===============================================

def _count_assertions_python(test_code: str) -> int:
    """Compte les assertions dans les tests Python/Selenium."""
    patterns = [
        r'\bassert\s+',           # assert standard Python
        r'\.assert_',             # unittest assertions (assertEqual, assertTrue, etc.)
        r'WebDriverWait\(',       # Attentes explicites Selenium
        r'expected_conditions',   # Conditions Selenium
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, test_code or "", re.IGNORECASE))
    return count

def _count_test_methods_python(test_code: str) -> int:
    """Compte les méthodes de test Python (def test_)."""
    return len(re.findall(r'def test_\w+\(', test_code or ""))

def _has_setup_teardown_python(test_code: str) -> bool:
    """Vérifie si le test Python a des méthodes setup/teardown."""
    setup_patterns = [
        r'def setUp\(',
        r'def setUpClass\(',
        r'@pytest\.fixture',
        r'def setup\(',
    ]
    teardown_patterns = [
        r'def tearDown\(',
        r'def tearDownClass\(',
        r'\.quit\(\)',     # driver.quit()
        r'\.close\(\)',    # driver.close()
    ]
    code = test_code or ""
    has_setup = any(re.search(p, code) for p in setup_patterns)
    has_teardown = any(re.search(p, code) for p in teardown_patterns)
    return has_setup or has_teardown

def _has_exception_handling_python(test_code: str) -> bool:
    """Vérifie si le test Python gère les exceptions."""
    patterns = [
        r'pytest\.raises\(',        # pytest.raises
        r'with\s+self\.assertRaises',  # unittest assertRaises
        r'try:\s*\n',               # try-except
        r'except\s+\w+',            # except block
    ]
    return any(re.search(p, test_code or "") for p in patterns)

def _has_waits_selenium(test_code: str) -> bool:
    """Vérifie si le test Selenium utilise des attentes explicites."""
    patterns = [
        r'WebDriverWait\(',
        r'expected_conditions',
        r'time\.sleep\(',
    ]
    return any(re.search(p, test_code or "") for p in patterns)

def _has_page_object_pattern(test_code: str) -> bool:
    """Vérifie si le test utilise le pattern Page Object."""
    patterns = [
        r'class\s+\w+Page\s*[\(:]',  # LoginPage, HomePage, etc.
        r'self\.page\.',
        r'page\s*=\s*\w+Page\(',
    ]
    return any(re.search(p, test_code or "") for p in patterns)

def _calculate_selenium_quality_score(test_code: str) -> Tuple[float, List[str]]:
    """
    Calcule un score de qualité pour un test Selenium/Python (0-100).
    Retourne: (score, [recommandations])
    """
    score = 0.0
    recommendations = []

    # 1. Assertions (25 points)
    assertion_count = _count_assertions_python(test_code)
    if assertion_count == 0:
        recommendations.append("❌ Aucune assertion trouvée - Ajoutez des assertions (assert, WebDriverWait)")
    elif assertion_count < 3:
        score += 12
        recommendations.append("⚠️ Peu d'assertions - Validez plus d'éléments de la page")
    else:
        score += 25

    # 2. Méthodes de test (20 points)
    test_method_count = _count_test_methods_python(test_code)
    if test_method_count == 0:
        recommendations.append("❌ Aucune fonction test_ trouvée - Utilisez def test_nom()")
    elif test_method_count < 3:
        score += 10
        recommendations.append("⚠️ Peu de tests - Couvrez plus de scénarios utilisateur")
    else:
        score += 20

    # 3. Setup/Teardown et cleanup (20 points)
    if _has_setup_teardown_python(test_code):
        score += 20
    else:
        recommendations.append("❌ Pas de cleanup - Ajoutez driver.quit() dans tearDown ou finally")

    # 4. Attentes explicites (15 points)
    if _has_waits_selenium(test_code):
        score += 15
    else:
        recommendations.append("⚠️ Utilisez WebDriverWait au lieu de time.sleep pour plus de stabilité")

    # 5. Gestion des exceptions (10 points)
    if _has_exception_handling_python(test_code):
        score += 10
    else:
        recommendations.append("💡 Ajoutez pytest.raises pour tester les cas d'erreur")

    # 6. Documentation (5 points)
    if _has_comments(test_code):
        score += 5
    else:
        recommendations.append("💡 Ajoutez des docstrings pour expliquer les scénarios de test")

    # 7. Page Object Pattern (5 points) - Bonus
    if _has_page_object_pattern(test_code):
        score += 5
        recommendations.append("✅ Excellente pratique - Utilisation du pattern Page Object")
    else:
        recommendations.append("💡 Utilisez le pattern Page Object pour améliorer la maintenabilité")

    return score, recommendations

def _calculate_test_quality_score(test_code: str) -> Tuple[float, List[str]]:
    """
    Calcule un score de qualité du test (0-100) basé sur l'analyse statique.
    Retourne: (score, [recommandations])
    """
    score = 0.0
    recommendations = []

    # 1. Assertions (30 points)
    assertion_count = _count_assertions(test_code)
    if assertion_count == 0:
        recommendations.append("❌ Aucune assertion trouvée - Ajoutez des assertions pour valider le comportement")
    elif assertion_count < 3:
        score += 15
        recommendations.append("⚠️ Peu d'assertions - Augmentez la couverture des cas limites")
    else:
        score += 30

    # 2. Méthodes de test (20 points)
    test_method_count = _count_test_methods(test_code)
    if test_method_count == 0:
        recommendations.append("❌ Aucune méthode @Test trouvée - Vérifiez les annotations JUnit")
    elif test_method_count < 3:
        score += 10
        recommendations.append("⚠️ Peu de méthodes de test - Couvrez plus de scénarios")
    else:
        score += 20

    # 3. Setup/Teardown (15 points)
    if _has_setup_teardown(test_code):
        score += 15
    else:
        recommendations.append("💡 Ajoutez @Before/@After pour initialiser/nettoyer les ressources")

    # 4. Gestion des exceptions (15 points)
    if _has_exception_handling(test_code):
        score += 15
    else:
        recommendations.append("💡 Testez les cas d'erreur avec assertThrows ou @Test(expected=...)")

    # 5. Documentation (10 points)
    if _has_comments(test_code):
        score += 10
    else:
        recommendations.append("💡 Ajoutez des commentaires pour expliquer la logique des tests")

    # 6. Organisation du code (10 points)
    lines = (test_code or "").split('\n')
    if len(lines) > 10 and len(lines) < 200:  # Taille raisonnable
        score += 10
    elif len(lines) >= 200:
        recommendations.append("⚠️ Test très long - Divisez en plusieurs méthodes de test")
    else:
        recommendations.append("⚠️ Test très court - Vérifiez qu'il couvre suffisamment de cas")

    return score, recommendations

def _calculate_coverage_score(jacoco_metrics: Dict) -> Tuple[float, List[str]]:
    """
    Calcule un score de couverture (0-100) basé sur les métriques JaCoCo.
    Retourne: (score, [recommandations])
    """
    if not jacoco_metrics:
        return 0.0, ["⚠️ Aucune métrique de couverture disponible"]

    score = 0.0
    recommendations = []

    # Pondération: 50% lignes, 30% branches, 20% instructions
    line_cov = jacoco_metrics.get('line_coverage', 0.0)
    branch_cov = jacoco_metrics.get('branch_coverage', 0.0)
    instruction_cov = jacoco_metrics.get('instruction_coverage', 0.0)

    # Score de couverture de lignes (50 points max)
    score += (line_cov / 100) * 50
    if line_cov < 50:
        recommendations.append(f"❌ Couverture de lignes faible ({line_cov:.1f}%) - Ciblez au moins 70%")
    elif line_cov < 70:
        recommendations.append(f"⚠️ Couverture de lignes moyenne ({line_cov:.1f}%) - Visez 80%+")
    elif line_cov >= 90:
        recommendations.append(f"✅ Excellente couverture de lignes ({line_cov:.1f}%)")

    # Score de couverture de branches (30 points max)
    score += (branch_cov / 100) * 30
    if branch_cov < 50:
        recommendations.append(f"❌ Couverture de branches faible ({branch_cov:.1f}%) - Testez tous les chemins conditionnels")
    elif branch_cov < 70:
        recommendations.append(f"⚠️ Couverture de branches moyenne ({branch_cov:.1f}%) - Améliorez les tests de conditions")

    # Score de couverture d'instructions (20 points max)
    score += (instruction_cov / 100) * 20

    # Détails des métriques
    lines_total = jacoco_metrics.get('lines_total', 0)
    lines_covered = jacoco_metrics.get('lines_covered', 0)
    if lines_total > 0:
        lines_missed = lines_total - lines_covered
        if lines_missed > 0:
            recommendations.append(f"📊 {lines_missed}/{lines_total} lignes non couvertes")

    return score, recommendations

def analyze_test_quality(test_code: str, jacoco_metrics: Optional[Dict] = None, pytest_metrics: Optional[Dict] = None) -> Dict:
    """
    Analyse complète de la qualité d'un test.

    Args:
        test_code: Code du test à analyser
        jacoco_metrics: Métriques JaCoCo pour tests Java (optionnel)
        pytest_metrics: Métriques pytest pour tests Python (optionnel)

    Retourne un dictionnaire avec:
    - overall_score: score global (0-100)
    - test_quality_score: score qualité du code de test (0-100)
    - coverage_score: score de couverture (0-100) si applicable
    - recommendations: liste de recommandations
    - metrics: métriques détaillées
    - language: langage détecté
    """
    # Détecter le langage du test
    language = _detect_test_language(test_code)

    # Choisir la bonne fonction d'analyse selon le langage
    if language == "python":
        test_score, test_recs = _calculate_selenium_quality_score(test_code)

        # Pour Python/Selenium, pas de couverture JaCoCo mais on peut utiliser pytest metrics
        if pytest_metrics:
            # Convertir les métriques pytest en score
            total_tests = pytest_metrics.get('tests_total', 0)
            passed_tests = pytest_metrics.get('tests_passed', 0)
            if total_tests > 0:
                pass_rate = (passed_tests / total_tests) * 100
                coverage_score = pass_rate
                coverage_recs = [f"✅ {passed_tests}/{total_tests} tests passés ({pass_rate:.1f}%)"]
            else:
                coverage_score = 0.0
                coverage_recs = ["⚠️ Aucun test exécuté"]
        else:
            coverage_score = 0.0
            coverage_recs = []

        # Métriques détaillées pour Python
        metrics = {
            'language': 'python',
            'assertion_count': _count_assertions_python(test_code),
            'test_method_count': _count_test_methods_python(test_code),
            'has_setup_teardown': _has_setup_teardown_python(test_code),
            'has_exception_handling': _has_exception_handling_python(test_code),
            'has_waits': _has_waits_selenium(test_code),
            'has_page_object': _has_page_object_pattern(test_code),
            'has_comments': _has_comments(test_code),
            'code_lines': len((test_code or "").split('\n')),
        }
        if pytest_metrics:
            metrics.update(pytest_metrics)

    else:  # Java ou autre
        test_score, test_recs = _calculate_test_quality_score(test_code)
        coverage_score, coverage_recs = _calculate_coverage_score(jacoco_metrics or {})

        # Métriques détaillées pour Java
        metrics = {
            'language': 'java',
            'assertion_count': _count_assertions(test_code),
            'test_method_count': _count_test_methods(test_code),
            'has_setup_teardown': _has_setup_teardown(test_code),
            'has_exception_handling': _has_exception_handling(test_code),
            'has_comments': _has_comments(test_code),
            'code_lines': len((test_code or "").split('\n')),
        }
        if jacoco_metrics:
            metrics.update(jacoco_metrics)

    # Score global (pondéré)
    if coverage_score > 0:
        overall_score = (test_score * 0.5) + (coverage_score * 0.5)
    else:
        # Si pas de métriques de couverture, le score qualité compte pour 100%
        overall_score = test_score

    # Recommandations combinées
    all_recommendations = test_recs + coverage_recs

    return {
        'overall_score': round(overall_score, 1),
        'test_quality_score': round(test_score, 1),
        'coverage_score': round(coverage_score, 1),
        'recommendations': all_recommendations,
        'metrics': metrics,
        'grade': _get_grade(overall_score),
        'language': language,
    }

def _get_grade(score: float) -> str:
    """Convertit un score en note."""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"
