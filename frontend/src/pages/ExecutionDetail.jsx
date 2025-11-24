import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { apiJson, getApiBase } from "../lib/api";

export default function ExecutionDetail() {
  const { execId } = useParams();
  const [item, setItem] = useState(null);
  const [busy, setBusy] = useState(false);
  const [logFilter, setLogFilter] = useState("all"); // all, errors, warnings, info

  const load = async () => {
    const data = await apiJson(`/executions/${execId}`);
    setItem(data);
  };

  useEffect(() => { load(); }, [execId]);

  const rerun = async () => {
    setBusy(true);
    try {
      const data = await apiJson(`/executions/${execId}/rerun`, { method: "POST" });
      await load();
      alert(`Relancé: ${data.execId}`);
    } finally {
      setBusy(false);
    }
  };

  // Fonction pour colorer les lignes de logs
  const formatLogLine = (line, index) => {
    const lowerLine = line.toLowerCase();

    // Déterminer le type de log
    let bgColor = "bg-gray-50 dark:bg-gray-800/50";
    let textColor = "text-gray-700 dark:text-gray-300";
    let icon = "●";
    let iconColor = "text-gray-400";

    if (lowerLine.includes("error") || lowerLine.includes("exception") || lowerLine.includes("failed")) {
      bgColor = "bg-red-50 dark:bg-red-900/20";
      textColor = "text-red-800 dark:text-red-300";
      icon = "✖";
      iconColor = "text-red-500";
    } else if (lowerLine.includes("warn") || lowerLine.includes("warning")) {
      bgColor = "bg-amber-50 dark:bg-amber-900/20";
      textColor = "text-amber-800 dark:text-amber-300";
      icon = "⚠";
      iconColor = "text-amber-500";
    } else if (lowerLine.includes("success") || lowerLine.includes("✓") || lowerLine.includes("passed")) {
      bgColor = "bg-emerald-50 dark:bg-emerald-900/20";
      textColor = "text-emerald-800 dark:text-emerald-300";
      icon = "✓";
      iconColor = "text-emerald-500";
    } else if (lowerLine.includes("info") || lowerLine.includes("[info]")) {
      bgColor = "bg-blue-50 dark:bg-blue-900/20";
      textColor = "text-blue-800 dark:text-blue-300";
      icon = "ℹ";
      iconColor = "text-blue-500";
    } else if (lowerLine.includes("test") || lowerLine.includes("running")) {
      bgColor = "bg-purple-50 dark:bg-purple-900/20";
      textColor = "text-purple-800 dark:text-purple-300";
      icon = "▶";
      iconColor = "text-purple-500";
    }

    return (
      <div key={index} className={`px-3 py-1.5 ${bgColor} border-l-2 border-transparent hover:border-indigo-400`}>
        <span className={`${iconColor} mr-2 font-bold`}>{icon}</span>
        <span className={`${textColor} font-mono text-sm`}>{line}</span>
      </div>
    );
  };

  // Filtrer les logs selon le filtre sélectionné
  const getFilteredLogs = () => {
    if (!item?.logs) return [];
    const lines = item.logs.split('\n').filter(l => l.trim());

    if (logFilter === "errors") {
      return lines.filter(l =>
        l.toLowerCase().includes("error") ||
        l.toLowerCase().includes("exception") ||
        l.toLowerCase().includes("failed")
      );
    } else if (logFilter === "warnings") {
      return lines.filter(l =>
        l.toLowerCase().includes("warn") ||
        l.toLowerCase().includes("warning")
      );
    } else if (logFilter === "info") {
      return lines.filter(l =>
        l.toLowerCase().includes("info") ||
        l.toLowerCase().includes("success") ||
        l.toLowerCase().includes("passed")
      );
    }
    return lines;
  };

  if (!item) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <div className="h-12 w-12 mx-auto mb-4 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-gray-600 dark:text-gray-400">Chargement de l'exécution...</p>
      </div>
    </div>
  );

  const base = getApiBase();
  const filteredLogs = getFilteredLogs();

  // Calculer les statistiques
  const totalLines = item.logs ? item.logs.split('\n').filter(l => l.trim()).length : 0;
  const errorCount = item.logs ? item.logs.split('\n').filter(l =>
    l.toLowerCase().includes("error") ||
    l.toLowerCase().includes("exception") ||
    l.toLowerCase().includes("failed")
  ).length : 0;
  const warningCount = item.logs ? item.logs.split('\n').filter(l =>
    l.toLowerCase().includes("warn") ||
    l.toLowerCase().includes("warning")
  ).length : 0;

  const statusColors = {
    success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    pending: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
  };

  return (
    <div className="space-y-6">
      {/* En-tête amélioré */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-black/10 bg-gradient-to-br from-white/90 to-gray-50/90 p-6 backdrop-blur-md dark:border-white/10 dark:from-gray-900/90 dark:to-gray-800/90"
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold mb-2">Exécution #{item._id?.slice(-8)}</h1>
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="flex items-center gap-1.5">
                <span className="font-medium text-gray-600 dark:text-gray-400">Type:</span>
                <span className="px-2 py-0.5 rounded-lg bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300">
                  {item.kind}
                </span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="font-medium text-gray-600 dark:text-gray-400">Statut:</span>
                <span className={`px-2 py-0.5 rounded-lg font-medium ${statusColors[item.status] || statusColors.pending}`}>
                  {item.status}
                </span>
              </span>
              {item.created_at && (
                <span className="flex items-center gap-1.5">
                  <span className="font-medium text-gray-600 dark:text-gray-400">Créé:</span>
                  <span>{new Date(item.created_at).toLocaleString('fr-FR')}</span>
                </span>
              )}
            </div>
          </div>
          <button
            onClick={rerun}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? (
              <>
                <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Relancement...
              </>
            ) : (
              <>
                <span>🔄</span>
                Relancer
              </>
            )}
          </button>
        </div>
      </motion.div>

      {/* Métriques JaCoCo si disponibles */}
      {item.jacoco_metrics && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-gray-900"
        >
          <h2 className="text-lg font-semibold mb-4">Couverture de Code (JaCoCo)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(item.jacoco_metrics).map(([key, value]) => (
              <div key={key} className="text-center p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20">
                <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
                  {typeof value === 'number' ? `${value.toFixed(1)}%` : value}
                </div>
                <div className="text-xs uppercase tracking-wide text-gray-600 dark:text-gray-400 mt-1">
                  {key.replace(/_/g, ' ')}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Analyse Qualité si disponible */}
      {item.quality_analysis && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-gray-900"
        >
          <h2 className="text-lg font-semibold mb-4">Analyse Qualité</h2>
          <div className="space-y-3">
            {item.quality_analysis.score && (
              <div className="flex items-center justify-between p-3 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20">
                <span className="font-medium">Score Global</span>
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                  {item.quality_analysis.score}/100
                </span>
              </div>
            )}
            {item.quality_analysis.recommendations && (
              <div className="space-y-2">
                <h3 className="font-medium text-sm text-gray-600 dark:text-gray-400">Recommandations:</h3>
                <ul className="space-y-1">
                  {item.quality_analysis.recommendations.map((rec, idx) => (
                    <li key={idx} className="text-sm flex items-start gap-2">
                      <span className="text-amber-500">→</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Section Logs améliorée */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="rounded-2xl border border-black/10 bg-white dark:border-white/10 dark:bg-gray-900"
      >
        {/* En-tête des logs avec filtres */}
        <div className="border-b border-black/10 p-4 dark:border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Logs d'Exécution</h2>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800">
                {totalLines} lignes
              </span>
              {errorCount > 0 && (
                <span className="px-2 py-1 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                  {errorCount} erreurs
                </span>
              )}
              {warningCount > 0 && (
                <span className="px-2 py-1 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  {warningCount} warnings
                </span>
              )}
            </div>
          </div>

          {/* Filtres */}
          <div className="flex gap-2">
            {["all", "errors", "warnings", "info"].map((filter) => (
              <button
                key={filter}
                onClick={() => setLogFilter(filter)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  logFilter === filter
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                }`}
              >
                {filter === "all" ? "Tous" : filter === "errors" ? "Erreurs" : filter === "warnings" ? "Warnings" : "Info"}
                {filter !== "all" && (
                  <span className="ml-1 opacity-70">
                    ({filter === "errors" ? errorCount : filter === "warnings" ? warningCount : totalLines - errorCount - warningCount})
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Contenu des logs */}
        <div className="p-4">
          {filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>Aucun log {logFilter !== "all" ? `de type "${logFilter}"` : "disponible"}.</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto rounded-lg border border-gray-200 dark:border-gray-700">
              {filteredLogs.map((line, idx) => formatLogLine(line, idx))}
            </div>
          )}
        </div>
      </motion.div>

      {/* Artefacts */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="rounded-2xl border border-black/10 bg-white p-6 dark:border-white/10 dark:bg-gray-900"
      >
        <h2 className="text-lg font-semibold mb-4">Artefacts Générés</h2>
        {(!item.artifacts || item.artifacts.length === 0) ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p>Aucun artefact généré pour cette exécution.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {item.artifacts.map((id) => (
              <a
                key={id}
                href={`${base}/artifact/${id}`}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-indigo-400 hover:bg-indigo-50 transition dark:border-gray-700 dark:hover:border-indigo-500 dark:hover:bg-indigo-900/20"
              >
                <span className="text-2xl">📄</span>
                <div className="flex-1">
                  <div className="font-medium text-sm">{id}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Cliquez pour télécharger</div>
                </div>
                <span className="text-indigo-600 dark:text-indigo-400">→</span>
              </a>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
