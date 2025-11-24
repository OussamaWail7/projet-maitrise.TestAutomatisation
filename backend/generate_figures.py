"""
Script pour générer les graphiques du Chapitre 3
Figures 3.5 et 3.6
"""
import sys
import io

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import matplotlib.pyplot as plt
import json
import os
from glob import glob
from datetime import datetime

# Configuration matplotlib pour affichage français
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['figure.titlesize'] = 14


def find_latest_benchmark_file():
    """
    Trouve le fichier de benchmark le plus récent
    """
    files = glob("benchmark_results_*.json")
    if not files:
        return None
    # Trier par date de modification
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def load_benchmark_results(filepath=None):
    """
    Charge les résultats du benchmark
    """
    if filepath is None:
        filepath = find_latest_benchmark_file()

    if filepath is None:
        print("❌ Aucun fichier de résultats trouvé!")
        print("Lancez d'abord: python benchmark_complete.py")
        return None

    print(f"📂 Chargement: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_figure_3_5_latency(results, output_path='Figure3_5_Latence.png'):
    """
    Figure 3.5 - Graphique de comparaison des latences P50/P95
    """
    if not results:
        print("⚠️ Aucun résultat à afficher")
        return

    providers = []
    p50_values = []
    p95_values = []

    for r in results:
        label = f"{r['provider'].capitalize()}\n{r['model'][:20]}"
        providers.append(label)
        p50_values.append(r['gen_latency_p50'])
        p95_values.append(r['gen_latency_p95'])

    # Créer le graphique
    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(providers))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], p50_values, width,
                    label='P50 (50e percentile)', color='#4CAF50', alpha=0.9)
    bars2 = ax.bar([i + width/2 for i in x], p95_values, width,
                    label='P95 (95e percentile)', color='#FF9800', alpha=0.9)

    # Ajouter les valeurs sur les barres
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}s',
                    ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('Provider / Modèle', fontweight='bold')
    ax.set_ylabel('Latence de Génération (secondes)', fontweight='bold')
    ax.set_title('Figure 3.5 - Comparaison des Latences de Génération de Tests', fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(providers, fontsize=10)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Ajouter une ligne de référence à 10s
    ax.axhline(y=10, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Seuil acceptable (10s)')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: {output_path}")

    return fig


def generate_figure_3_6_quality(results, output_path='Figure3_6_Qualite.png'):
    """
    Figure 3.6 - Graphiques de Couverture JaCoCo et Score de Qualité
    """
    if not results:
        print("⚠️ Aucun résultat à afficher")
        return

    providers = []
    coverages = []
    success_rates = []
    quality_scores = []

    for r in results:
        label = f"{r['provider'].capitalize()}\n{r['model'][:20]}"
        providers.append(label)
        coverages.append(r['jacoco_coverage_mean'])
        success_rates.append(r['compile_success_rate'])
        quality_scores.append(r['quality_score_mean'])

    # Créer 3 sous-graphiques
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    # Graphique 1: Couverture JaCoCo
    bars1 = ax1.bar(providers, coverages, color='#2196F3', alpha=0.9)
    ax1.set_ylabel('Couverture (%)', fontweight='bold')
    ax1.set_title('Couverture JaCoCo Moyenne', fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    ax1.axhline(y=80, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax1.text(len(providers)-0.5, 82, 'Objectif 80%', fontsize=8, color='green')

    # Ajouter valeurs
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

    # Graphique 2: Taux de Succès de Compilation
    bars2 = ax2.bar(providers, success_rates, color='#4CAF50', alpha=0.9)
    ax2.set_ylabel('Taux de Succès (%)', fontweight='bold')
    ax2.set_title('Taux de Succès de Compilation', fontweight='bold')
    ax2.set_ylim(0, 100)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)
    ax2.axhline(y=85, color='orange', linestyle='--', alpha=0.5, linewidth=1)
    ax2.text(len(providers)-0.5, 87, 'Objectif 85%', fontsize=8, color='orange')

    # Ajouter valeurs
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

    # Graphique 3: Score de Qualité
    bars3 = ax3.bar(providers, quality_scores, color='#9C27B0', alpha=0.9)
    ax3.set_ylabel('Score (/100)', fontweight='bold')
    ax3.set_title('Score de Qualité Moyen', fontweight='bold')
    ax3.set_ylim(0, 100)
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.set_axisbelow(True)

    # Ajouter valeurs
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height:.1f}', ha='center', va='bottom', fontsize=9)

    plt.suptitle('Figure 3.6 - Métriques de Qualité de Génération de Tests', fontweight='bold', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: {output_path}")

    return fig


def generate_figure_3_7_cycle_time(results, output_path='Figure3_7_TempsConsommation.png'):
    """
    Figure 3.7 (BONUS) - Décomposition du temps de cycle
    """
    if not results:
        print("⚠️ Aucun résultat à afficher")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    providers = []
    gen_times = []
    compile_times = []

    for r in results:
        label = f"{r['provider'].capitalize()}\n{r['model'][:20]}"
        providers.append(label)
        gen_times.append(r['gen_latency_mean'])
        compile_times.append(r['compile_time_mean'])

    x = range(len(providers))
    width = 0.6

    # Barres empilées
    bars1 = ax.bar(x, gen_times, width, label='Génération LLM', color='#FF5722', alpha=0.9)
    bars2 = ax.bar(x, compile_times, width, bottom=gen_times,
                   label='Compilation + Exécution Maven', color='#607D8B', alpha=0.9)

    # Ajouter les totaux au-dessus
    for i, (g, c) in enumerate(zip(gen_times, compile_times)):
        total = g + c
        ax.text(i, total, f'{total:.1f}s', ha='center', va='bottom', fontweight='bold', fontsize=10)

    ax.set_ylabel('Temps (secondes)', fontweight='bold')
    ax.set_title('Figure 3.7 - Décomposition du Temps de Cycle Complet', fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(providers, fontsize=10)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: {output_path}")

    return fig


def generate_table_3_3_detailed(results, output_path='Tableau3_3_Details.txt'):
    """
    Génère le Tableau 3.3 avec détails par cas de test
    """
    if not results:
        print("⚠️ Aucun résultat")
        return

    lines = []
    lines.append("="*120)
    lines.append("TABLEAU 3.3 - ANALYSE QUALITATIVE PAR CAS DE TEST")
    lines.append("="*120)
    lines.append(f"{'Cas de Test':<25} {'Provider':<15} {'Modèle':<25} {'Succès':<8} {'JaCoCo':<8} {'Score':<8}")
    lines.append("-"*120)

    for r in results:
        provider = r['provider'].capitalize()
        model = r['model'][:22]

        # Accéder aux résultats individuels
        raw_results = r.get('raw_results', [])

        for detail in raw_results:
            case_name = detail.get('case_name', 'N/A')[:22]
            success = "✅" if detail.get('compile_success', False) else "❌"
            coverage = detail.get('jacoco_line_coverage', 0)
            score = detail.get('quality_score', 0)

            lines.append(f"{case_name:<25} {provider:<15} {model:<25} {success:<8} {coverage:>6.1f}% {score:>6.0f}/100")

    lines.append("="*120)

    output_text = "\n".join(lines)
    print("\n" + output_text)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)

    print(f"\n✅ Tableau sauvegardé: {output_path}")


def main():
    """
    Point d'entrée principal
    """
    print("="*80)
    print("🎨 GÉNÉRATION DES FIGURES - CHAPITRE 3")
    print("="*80)

    # Charger les résultats
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = None

    results = load_benchmark_results(filepath)

    if not results:
        print("\n❌ Impossible de charger les résultats")
        print("Usage: python generate_figures.py [chemin_vers_benchmark_results.json]")
        return

    print(f"\n📊 {len(results)} provider(s) trouvé(s)\n")

    # Générer les figures
    print("🖼️ Génération Figure 3.5 (Latence)...")
    generate_figure_3_5_latency(results)

    print("\n🖼️ Génération Figure 3.6 (Qualité)...")
    generate_figure_3_6_quality(results)

    print("\n🖼️ Génération Figure 3.7 (Temps de Cycle)...")
    generate_figure_3_7_cycle_time(results)

    print("\n📋 Génération Tableau 3.3 (Détails)...")
    generate_table_3_3_detailed(results)

    print("\n" + "="*80)
    print("✅ GÉNÉRATION TERMINÉE!")
    print("="*80)
    print("\nFichiers générés:")
    print("  - Figure3_5_Latence.png")
    print("  - Figure3_6_Qualite.png")
    print("  - Figure3_7_TempsConsommation.png")
    print("  - Tableau3_3_Details.txt")
    print("\n💡 Insérez ces figures dans votre Chapitre 3 avec les légendes appropriées.")


if __name__ == "__main__":
    main()
