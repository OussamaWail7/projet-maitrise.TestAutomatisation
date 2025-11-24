"""
Script de benchmark complet pour le Chapitre 3
Mesure: Latence, Taux de succès, Couverture JaCoCo, Temps de cycle
"""
import sys
import io

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import json
import statistics
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Import des services
try:
    from gemini_service import generate_test_case_with_gemini
    GEMINI_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Gemini non disponible: {e}")
    GEMINI_AVAILABLE = False

try:
    from llm_service import generate_test_case_ollama
    OLLAMA_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Ollama non disponible: {e}")
    OLLAMA_AVAILABLE = False

try:
    from mistral_service import generate_test_case_with_mistral
    MISTRAL_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Mistral non disponible: {e}")
    MISTRAL_AVAILABLE = False

from test_runner import run_java_maven
from quality_analyzer import analyze_test_quality


# ========================================
# CORPUS DE TEST
# ========================================

CORPUS = [
    {
        "id": 1,
        "name": "Simple Calculator",
        "code": """public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }

    public double divide(int a, int b) {
        if (b == 0) throw new ArithmeticException("Division by zero");
        return (double) a / b;
    }
}""",
        "type": "unit",
        "language": "java"
    },
    {
        "id": 2,
        "name": "String Utilities",
        "code": """public class StringUtils {
    public boolean isEmpty(String str) {
        return str == null || str.trim().isEmpty();
    }

    public String reverse(String str) {
        if (str == null) return null;
        return new StringBuilder(str).reverse().toString();
    }

    public int countWords(String str) {
        if (isEmpty(str)) return 0;
        return str.trim().split("\\s+").length;
    }
}""",
        "type": "unit",
        "language": "java"
    },
    {
        "id": 3,
        "name": "REST Controller - User",
        "code": """@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/hello")
    public String hello(@RequestParam String name) {
        return "Hello " + name;
    }

    @PostMapping("/create")
    public String createUser(@RequestParam String username, @RequestParam String email) {
        if (username == null || username.isEmpty()) {
            throw new IllegalArgumentException("Username cannot be empty");
        }
        return "User created: " + username;
    }
}""",
        "type": "rest-assured",
        "language": "java"
    },
    {
        "id": 4,
        "name": "MathUtils",
        "code": """public class MathUtils {
    public long factorial(int n) {
        if (n < 0) throw new IllegalArgumentException("n must be >= 0");
        if (n == 0 || n == 1) return 1;
        long result = 1;
        for (int i = 2; i <= n; i++) {
            result *= i;
        }
        return result;
    }

    public boolean isPrime(int n) {
        if (n <= 1) return false;
        if (n == 2) return true;
        if (n % 2 == 0) return false;
        for (int i = 3; i * i <= n; i += 2) {
            if (n % i == 0) return false;
        }
        return true;
    }
}""",
        "type": "unit",
        "language": "java"
    },
    {
        "id": 5,
        "name": "REST Controller - Calculator API",
        "code": """@RestController
@RequestMapping("/api/calc")
public class CalculatorController {

    @GetMapping("/add")
    public int add(@RequestParam int a, @RequestParam int b) {
        return a + b;
    }

    @GetMapping("/divide")
    public double divide(@RequestParam int a, @RequestParam int b) {
        if (b == 0) throw new ArithmeticException("Division by zero");
        return (double) a / b;
    }
}""",
        "type": "rest-assured",
        "language": "java"
    }
]


# ========================================
# FONCTIONS DE BENCHMARK
# ========================================

def measure_single_generation(provider: str, model: str, code: str, test_type: str) -> Dict:
    """
    Mesure une génération unique
    Retourne: {latency, success, test_code, error}
    """
    start = time.time()

    try:
        if provider == "gemini" and GEMINI_AVAILABLE:
            test_code = generate_test_case_with_gemini(
                code=code,
                test_type=test_type,
                language="java",
                model=model
            )
        elif provider == "ollama" and OLLAMA_AVAILABLE:
            test_code = generate_test_case_ollama(
                code=code,
                test_type=test_type,
                language="java",
                model=model
            )
        elif provider == "mistral" and MISTRAL_AVAILABLE:
            test_code = generate_test_case_with_mistral(
                code=code,
                test_type=test_type,
                language="java",
                model=model
            )
        else:
            raise ValueError(f"Provider {provider} non disponible")

        latency = time.time() - start

        return {
            "latency": latency,
            "success": True,
            "test_code": test_code,
            "error": None
        }

    except Exception as e:
        latency = time.time() - start
        return {
            "latency": latency,
            "success": False,
            "test_code": None,
            "error": str(e)
        }


def measure_compilation_execution(code: str, test_code: str) -> Dict:
    """
    Mesure la compilation et l'exécution
    Retourne: {compile_success, compile_time, jacoco_metrics, logs}
    """
    start_compile = time.time()

    try:
        success, logs, artifacts, jacoco_metrics = run_java_maven(code, test_code)
        compile_time = time.time() - start_compile

        return {
            "compile_success": success,
            "compile_time": compile_time,
            "jacoco_metrics": jacoco_metrics,
            "logs": logs[:500]  # Limiter la taille
        }

    except Exception as e:
        compile_time = time.time() - start_compile
        return {
            "compile_success": False,
            "compile_time": compile_time,
            "jacoco_metrics": {},
            "logs": str(e)
        }


def benchmark_provider(provider: str, model: str, corpus: List[Dict], iterations: int = 1) -> Dict:
    """
    Benchmark complet pour un provider
    """
    print(f"\n{'='*60}")
    print(f"🚀 BENCHMARK: {provider.upper()} - {model}")
    print(f"{'='*60}")

    results = []

    for case in corpus:
        print(f"\n📝 Test #{case['id']}: {case['name']}")

        for iteration in range(iterations):
            print(f"   Iteration {iteration + 1}/{iterations}...", end=" ")

            # 1. Génération
            gen_result = measure_single_generation(
                provider=provider,
                model=model,
                code=case['code'],
                test_type=case['type']
            )

            if not gen_result['success']:
                print(f"❌ ÉCHEC GEN: {gen_result['error'][:50]}")
                results.append({
                    "case_id": case['id'],
                    "case_name": case['name'],
                    "iteration": iteration + 1,
                    "gen_success": False,
                    "gen_latency": gen_result['latency'],
                    "gen_error": gen_result['error'],
                    "compile_success": False,
                    "total_time": gen_result['latency']
                })
                continue

            # 2. Compilation + Exécution
            exec_result = measure_compilation_execution(
                code=case['code'],
                test_code=gen_result['test_code']
            )

            # 3. Analyse qualité
            quality_score = 0
            if exec_result['compile_success']:
                try:
                    quality_result = analyze_test_quality(
                        test_code=gen_result['test_code'],
                        jacoco_metrics=exec_result['jacoco_metrics']
                    )
                    quality_score = quality_result.get('score', 0)
                except:
                    pass

            total_time = gen_result['latency'] + exec_result['compile_time']

            status = "✅" if exec_result['compile_success'] else "❌"
            print(f"{status} (Gen: {gen_result['latency']:.2f}s, Compile: {exec_result['compile_time']:.2f}s, Score: {quality_score}/100)")

            results.append({
                "case_id": case['id'],
                "case_name": case['name'],
                "iteration": iteration + 1,
                "gen_success": True,
                "gen_latency": gen_result['latency'],
                "compile_success": exec_result['compile_success'],
                "compile_time": exec_result['compile_time'],
                "total_time": total_time,
                "jacoco_line_coverage": exec_result['jacoco_metrics'].get('line_coverage', 0),
                "jacoco_branch_coverage": exec_result['jacoco_metrics'].get('branch_coverage', 0),
                "quality_score": quality_score
            })

    return aggregate_results(provider, model, results)


def aggregate_results(provider: str, model: str, results: List[Dict]) -> Dict:
    """
    Agrège les résultats
    """
    total = len(results)
    gen_successes = [r for r in results if r.get('gen_success', False)]
    compile_successes = [r for r in results if r.get('compile_success', False)]

    gen_latencies = [r['gen_latency'] for r in gen_successes]
    compile_times = [r['compile_time'] for r in compile_successes]
    total_times = [r['total_time'] for r in compile_successes]
    coverages = [r['jacoco_line_coverage'] for r in compile_successes]
    quality_scores = [r.get('quality_score', 0) for r in compile_successes]

    def percentile(data, p):
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    return {
        "provider": provider,
        "model": model,
        "total_tests": total,
        "gen_success_count": len(gen_successes),
        "gen_success_rate": len(gen_successes) / total * 100 if total > 0 else 0,
        "compile_success_count": len(compile_successes),
        "compile_success_rate": len(compile_successes) / total * 100 if total > 0 else 0,

        # Latence génération
        "gen_latency_mean": statistics.mean(gen_latencies) if gen_latencies else 0,
        "gen_latency_p50": percentile(gen_latencies, 50),
        "gen_latency_p95": percentile(gen_latencies, 95),

        # Temps compilation
        "compile_time_mean": statistics.mean(compile_times) if compile_times else 0,

        # Temps total
        "total_time_mean": statistics.mean(total_times) if total_times else 0,

        # Couverture JaCoCo
        "jacoco_coverage_mean": statistics.mean(coverages) if coverages else 0,

        # Score qualité
        "quality_score_mean": statistics.mean(quality_scores) if quality_scores else 0,

        # Détails
        "raw_results": results
    }


def print_summary_table(all_results: List[Dict]):
    """
    Affiche le tableau récapitulatif (Tableau 3.1)
    """
    print("\n" + "="*80)
    print("📊 TABLEAU 3.1 - MÉTRIQUES DE PERFORMANCE")
    print("="*80)
    print(f"{'Provider':<15} {'Modèle':<25} {'P50 (s)':<10} {'P95 (s)':<10} {'Succès':<10} {'JaCoCo':<10}")
    print("-"*80)

    for r in all_results:
        print(f"{r['provider']:<15} {r['model']:<25} "
              f"{r['gen_latency_p50']:<10.2f} {r['gen_latency_p95']:<10.2f} "
              f"{r['compile_success_rate']:<10.1f}% {r['jacoco_coverage_mean']:<10.1f}%")

    print("="*80)


def print_cycle_time_table(all_results: List[Dict]):
    """
    Affiche le tableau de temps de cycle (Tableau 3.2)
    """
    print("\n" + "="*80)
    print("📊 TABLEAU 3.2 - TEMPS DE CYCLE COMPLET")
    print("="*80)

    for r in all_results:
        gen_time = r['gen_latency_mean']
        compile_time = r['compile_time_mean']
        total_time = r['total_time_mean']

        if total_time == 0:
            continue

        gen_pct = gen_time / total_time * 100
        compile_pct = compile_time / total_time * 100

        print(f"\n{r['provider'].upper()} - {r['model']}")
        print(f"  1. Génération:    {gen_time:6.2f}s  ({gen_pct:5.1f}%)")
        print(f"  2. Compilation:   {compile_time:6.2f}s  ({compile_pct:5.1f}%)")
        print(f"  TOTAL:            {total_time:6.2f}s  (100.0%)")

    print("="*80)


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    print("="*80)
    print("🎯 BENCHMARK COMPLET - CHAPITRE 3")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Corpus: {len(CORPUS)} cas de test")
    print(f"Iterations par cas: 1")

    # Configuration des providers à tester
    providers_config = []

    if GEMINI_AVAILABLE:
        providers_config.append(("gemini", "gemini-1.5-flash"))
        # Décommentez si vous voulez tester Pro aussi
        # providers_config.append(("gemini", "gemini-1.5-pro"))

    if OLLAMA_AVAILABLE:
        providers_config.append(("ollama", "deepseek-coder:6.7b"))
        # Décommentez si vous avez d'autres modèles
        # providers_config.append(("ollama", "deepseek-coder:33b"))

    if MISTRAL_AVAILABLE:
        providers_config.append(("mistral", "mistral-small-latest"))

    if not providers_config:
        print("\n❌ ERREUR: Aucun provider disponible!")
        print("Vérifiez votre configuration .env")
        exit(1)

    # Lancer les benchmarks
    all_results = []

    for provider, model in providers_config:
        result = benchmark_provider(provider, model, CORPUS, iterations=1)
        all_results.append(result)

    # Affichage des résultats
    print_summary_table(all_results)
    print_cycle_time_table(all_results)

    # Sauvegarde JSON
    output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Résultats sauvegardés: {output_file}")
    print("\n✅ Benchmark terminé!")
