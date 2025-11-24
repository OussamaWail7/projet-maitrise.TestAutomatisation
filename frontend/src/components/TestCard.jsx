import { Clock, Code2, Play, Eye } from "lucide-react";

export default function TestCard({ test, onViewDetails, onExecute, isExecuting }) {
  const statusColors = {
    draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200",
    confirmed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200",
  };

  const typeLabels = {
    unit: "Unitaire",
    "rest-assured": "API (REST)",
    selenium: "UI (Selenium)",
  };

  const languageColors = {
    java: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200",
    python: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
    javascript: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200",
    typescript: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
    csharp: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200",
    ruby: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
    go: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200",
  };

  const status = (test.status || "confirmed").toLowerCase();
  const statusCls = statusColors[status] || statusColors.confirmed;
  const langCls = languageColors[test.language] || languageColors.java;

  return (
    <div className="group rounded-xl border border-black/10 bg-white p-4 transition hover:shadow-md dark:border-white/10 dark:bg-gray-900">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-base font-semibold">
              {typeLabels[test.test_type] || test.test_type}
            </span>
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusCls}`}>
              {status}
            </span>
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${langCls}`}>
              {test.language || "java"}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span className="inline-flex items-center gap-1">
              <Clock size={12} />
              {new Date(test.created_at || Date.now()).toLocaleString()}
            </span>
            {test.provider && (
              <span className="inline-flex items-center gap-1">
                <Code2 size={12} />
                {test.provider}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Code preview */}
      {test.generated_test && (
        <div className="mb-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-950">
          <pre className="overflow-hidden text-ellipsis whitespace-nowrap font-mono text-xs text-gray-700 dark:text-gray-300">
            {test.generated_test.slice(0, 100)}...
          </pre>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewDetails(test)}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border border-black/10 px-3 py-2 text-sm font-medium transition hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          <Eye size={14} />
          Voir détails
        </button>
        <button
          onClick={() => onExecute(test)}
          disabled={isExecuting}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isExecuting ? (
            <>
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-r-transparent" />
              En cours...
            </>
          ) : (
            <>
              <Play size={14} />
              Exécuter
            </>
          )}
        </button>
      </div>
    </div>
  );
}
