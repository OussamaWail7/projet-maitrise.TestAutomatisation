// src/pages/Executions.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Clock, RefreshCcw, Search, X, Copy, Play, FileDown, ExternalLink, BarChart3, Award } from "lucide-react";
import { apiJson, getApiBase } from "../lib/api";
import { SkeletonTable } from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import CodeViewer from "../components/CodeViewer";

const STATUS_COLORS = {
  queued: "bg-gray-100 text-gray-800 dark:bg-gray-900/40 dark:text-gray-200",
  running: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200",
};

function StatusBadge({ status }) {
  const s = String(status || "").toLowerCase();
  const cls = STATUS_COLORS[s] || "bg-gray-100 text-gray-800 dark:bg-gray-900/40 dark:text-gray-200";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{s || "—"}</span>;
}

/** Composant barre de progression pour couverture */
function CoverageBar({ label, percentage, total, covered }) {
  const pct = Math.min(100, Math.max(0, percentage || 0));
  let barColor = "bg-red-500";
  if (pct >= 80) barColor = "bg-emerald-500";
  else if (pct >= 60) barColor = "bg-yellow-500";
  else if (pct >= 40) barColor = "bg-orange-500";

  return (
    <div className="mb-2">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-gray-600 dark:text-gray-400">
          {pct.toFixed(1)}% <span className="opacity-60">({covered}/{total})</span>
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className={`h-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/** Badge de note qualité */
function QualityGrade({ grade }) {
  const gradeColors = {
    "A+": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
    "A": "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200",
    "B": "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
    "C": "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200",
    "D": "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200",
    "F": "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200",
  };
  const cls = gradeColors[grade] || gradeColors["F"];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-lg font-bold ${cls}`}>
      <Award size={18} /> {grade}
    </span>
  );
}

/** Helpers robustes */
const getExecId = (obj) => obj?.id || obj?._id || "";
const getTestId = (obj) => obj?.test_case_id || obj?.testId || obj?.test_id || "";
const getCreatedAt = (obj) => {
  const v = obj?.created_at;
  if (!v) return new Date();
  try { return new Date(v); } catch { return new Date(); }
};
const absUrl = (maybeRelative, apiBase) => {
  if (!maybeRelative) return null;
  if (/^https?:\/\//i.test(maybeRelative)) return maybeRelative;
  // nettoie éventuels doubles slash
  const base = (apiBase || "").replace(/\/+$/, "");
  const path = String(maybeRelative).replace(/^\/+/, "");
  return `${base}/${path}`;
};

export default function Executions() {
  const [searchParams] = useSearchParams();
  const focusId = searchParams.get("focus") || "";

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const [contains, setContains] = useState("");
  const [status, setStatus] = useState("");
  const [kind, setKind] = useState("");
  const [limit, setLimit] = useState(50);

  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(null);

  const [polling, setPolling] = useState(true);
  const timerRef = useRef(null);
  const errorCountRef = useRef(0); // ✅ Compteur d'erreurs consécutives

  const apiBase = getApiBase();

  const fetchList = async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (limit) qs.set("limit", String(limit));
      if (contains.trim()) qs.set("contains", contains.trim());
      if (status) qs.set("status", status);
      if (kind) qs.set("kind", kind);
      const data = await apiJson(`/executions?${qs.toString()}`);
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchOne = async (id) => {
    if (!id) return;
    try {
      const data = await apiJson(`/executions/${id}`);
      setSelected(data || null);
      errorCountRef.current = 0; // ✅ Réinitialiser le compteur d'erreurs en cas de succès
      if (data && (data.status === "success" || data.status === "failed")) {
        setPolling(false);
      }
    } catch (e) {
      errorCountRef.current += 1; // ✅ Incrémenter le compteur d'erreurs
      // ✅ Arrêter le polling après 5 erreurs consécutives pour éviter une boucle infinie
      if (errorCountRef.current >= 5) {
        console.error(`Arrêt du polling après ${errorCountRef.current} erreurs consécutives`);
        setPolling(false);
      }
    }
  };

  // Premier chargement
  useEffect(() => {
    fetchList();
  }, []); // eslint-disable-line

  // Ouvrir automatiquement la modale si ?focus=...
  useEffect(() => {
    if (focusId) {
      setOpen(true);
      fetchOne(focusId);
    }
  }, [focusId]);

  // Polling du focus si ouvert et en cours
  useEffect(() => {
    const curId = getExecId(selected);
    if (!open || !curId) return;
    if (!polling) return;

    timerRef.current = setInterval(() => {
      fetchOne(curId);
    }, 2000); // 2s

    return () => clearInterval(timerRef.current);
  }, [open, selected, polling]);

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(String(text || ""));
    } catch {
      // ignore
    }
  };

  const rerunByTest = async (sel) => {
    const testId = getTestId(sel);
    if (!testId) return;
    const execId = getExecId(sel);
    try {
      const res = await apiJson(`/test-cases/${testId}/run`, {
        method: "POST",
        body: { language: sel?.language || "java", notes: `Re-run from exec ${execId}` },
      });
      if (res?.execId) {
        window.location.href = `/executions?focus=${res.execId}`;
      }
    } catch (e) {
      alert(`Échec re-run: ${e?.message || "erreur inconnue"}`);
    }
  };

  const refreshSelected = () => {
    const curId = getExecId(selected);
    if (curId) fetchOne(curId);
  };

  const openDetails = (row) => {
    setSelected(row);
    setOpen(true);
    const st = (row?.status || "").toLowerCase();
    setPolling(st === "running" || st === "queued");
  };

  const cols = useMemo(
    () => [
      { key: "created_at", label: "Date" },
      { key: "kind", label: "Type" },
      { key: "language", label: "Langage" },
      { key: "status", label: "Statut" },
      { key: "test_case_id", label: "Test ID" },
      { key: "id", label: "Exec ID" },
      { key: "_actions", label: "Action" },
    ],
    []
  );

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-black/10 bg-white/70 p-5 backdrop-blur-md dark:border-white/10 dark:bg-gray-900/60">
        <h1 className="text-xl font-semibold">Exécutions</h1>
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Suivi des exécutions (logs, artefacts, re-run). API :{" "}
          <code className="rounded bg-black/5 px-1">{apiBase}</code>
        </p>
      </div>

      {/* Filtres */}
      <div className="rounded-2xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-gray-900">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-sm md:col-span-2">
            <span className="mb-1 block">Recherche texte</span>
            <div className="relative">
              <input
                value={contains}
                onChange={(e) => setContains(e.target.value)}
                placeholder="mots dans logs/id/test"
                className="w-full rounded-xl border border-black/10 bg-gray-50 p-2 pl-8 dark:bg-gray-950"
              />
              <Search size={14} className="absolute left-2 top-2.5 opacity-70" />
            </div>
          </label>

          <label className="text-sm">
            <span className="mb-1 block">Statut</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white p-2 dark:bg-gray-950"
            >
              <option value="">Tous</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="success">success</option>
              <option value="failed">failed</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-1 block">Kind</span>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value)}
              className="w-full rounded-xl border border-black/10 bg-white p-2 dark:bg-gray-950"
            >
              <option value="">Tous</option>
              <option value="java-maven">java-maven</option>
              <option value="python-pytest">python-pytest</option>
              <option value="selenium">selenium</option>
              <option value="gatling">gatling</option>
              <option value="jmeter">jmeter</option>
            </select>
          </label>

          <label className="text-sm">
            <span className="mb-1 block">Limite</span>
            <input
              type="number"
              min={1}
              max={200}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value || 50))}
              className="w-full rounded-xl border border-black/10 bg-gray-50 p-2 dark:bg-gray-950"
            />
          </label>
        </div>

        <div className="mt-3 flex gap-3">
          <button
            onClick={fetchList}
            className="rounded-xl bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
          >
            Appliquer les filtres
          </button>
          <button
            onClick={() => {
              setContains("");
              setStatus("");
              setKind("");
              setLimit(50);
              fetchList();
            }}
            className="rounded-xl border border-black/10 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {/* Liste */}
      <div className="rounded-2xl border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-gray-900">
        {loading ? (
          <SkeletonTable rows={5} cols={7} />
        ) : items.length === 0 ? (
          <EmptyState
            icon="search"
            title="Aucune exécution trouvée"
            description="Essayez de modifier vos filtres ou lancez une nouvelle exécution depuis la page Générateur."
            action={
              <Link
                to="/generator"
                className="rounded-xl bg-indigo-700 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-800"
              >
                Créer une exécution
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] table-fixed text-sm">
              <colgroup>
                <col className="w-[190px]" />
                <col className="w-[160px]" />
                <col className="w-[120px]" />
                <col className="w-[120px]" />
                <col className="w-[210px]" />
                <col className="w-[260px]" />
                <col className="w-[140px]" />
              </colgroup>
              <thead className="text-left">
                <tr className="border-b border-black/10 dark:border-white/10">
                  {cols.map((c) => (
                    <th key={c.key} className="py-2 pr-4">{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const execId = getExecId(it);
                  const testId = getTestId(it);
                  const created = getCreatedAt(it);
                  return (
                    <tr key={execId || Math.random()} className="border-b border-black/5 dark:border-white/5 align-top">
                      <td className="py-2 pr-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1">
                          <Clock size={14} />
                          {created.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-2 pr-4">{it.kind || "—"}</td>
                      <td className="py-2 pr-4">{it.language || "—"}</td>
                      <td className="py-2 pr-4"><StatusBadge status={it.status} /></td>
                      <td className="py-2 pr-4">
                        {testId ? (
                          <code className="rounded bg-black/5 px-2 py-0.5">{testId}</code>
                        ) : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex items-center gap-2">
                          <code className="rounded bg-black/5 px-2 py-0.5">{execId || "—"}</code>
                          {execId ? (
                            <button
                              onClick={() => copyToClipboard(execId)}
                              className="inline-flex items-center gap-1 rounded border border-black/10 px-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-800"
                              title="Copier l'ID"
                            >
                              <Copy size={14} />
                            </button>
                          ) : null}
                        </div>
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => openDetails({ ...it, id: execId, test_case_id: testId })}
                            className="rounded-lg border border-black/10 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            Détails
                          </button>
                          {testId ? (
                            <button
                              onClick={() => rerunByTest({ ...it, id: execId, test_case_id: testId })}
                              className="inline-flex items-center gap-1 rounded-lg bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-800"
                            >
                              <Play size={14} /> Re-run
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modale Détails */}
      {open && selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <div className="relative z-10 w-[min(1100px,95vw)] max-h-[90vh] overflow-hidden rounded-2xl border border-black/10 bg-white p-4 shadow-xl dark:border-white/10 dark:bg-gray-900">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">Détails de l’exécution</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {getCreatedAt(selected).toLocaleString()} • {selected.kind || "—"} • {selected.language || "—"} •{" "}
                  <StatusBadge status={selected.status} />
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={refreshSelected}
                  className="rounded-lg border border-black/10 p-1.5 hover:bg-gray-50 dark:hover:bg-gray-800"
                  title="Rafraîchir"
                >
                  <RefreshCcw size={16} />
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="rounded-lg border border-black/10 p-1.5 hover:bg-gray-50 dark:hover:bg-gray-800"
                  aria-label="Fermer"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="mt-2 space-y-4">
              {/* Grille supérieure : Informations, Métriques, Analyse */}
              <div className="grid gap-4 md:grid-cols-3">
                {/* Informations */}
                <section className="rounded-xl border border-black/10 p-3 dark:border-white/10">
                  <h3 className="mb-2 text-sm font-medium">Informations</h3>
                  <dl className="text-xs leading-relaxed">
                    <div className="mb-1 flex gap-2"><dt className="w-20 text-gray-500">Exec ID</dt><dd><code className="rounded bg-black/5 px-2 py-0.5 text-[10px]">{getExecId(selected)}</code></dd></div>
                    <div className="mb-1 flex gap-2"><dt className="w-20 text-gray-500">Test ID</dt><dd>{getTestId(selected) ? <code className="rounded bg-black/5 px-2 py-0.5 text-[10px]">{getTestId(selected)}</code> : "—"}</dd></div>
                    <div className="mb-1 flex gap-2"><dt className="w-20 text-gray-500">Début</dt><dd>{selected.started_at ? new Date(selected.started_at).toLocaleString() : "—"}</dd></div>
                    <div className="mb-1 flex gap-2"><dt className="w-20 text-gray-500">Fin</dt><dd>{selected.finished_at ? new Date(selected.finished_at).toLocaleString() : "—"}</dd></div>
                    <div className="mb-1 flex gap-2"><dt className="w-20 text-gray-500">Notes</dt><dd>{selected.notes || "—"}</dd></div>
                  </dl>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {getTestId(selected) ? (
                      <button
                        onClick={() => rerunByTest(selected)}
                        className="inline-flex items-center gap-1 rounded-lg bg-indigo-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-800"
                      >
                        <Play size={14} /> Re-run
                      </button>
                    ) : null}
                    <Link
                      to={`/history`}
                      className="inline-flex items-center gap-1 rounded-lg border border-black/10 px-3 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <ExternalLink size={14} /> Historique
                    </Link>
                  </div>

                  {selected.artifacts?.length ? (
                    <div className="mt-4">
                      <h4 className="mb-1 text-xs font-medium">Artefacts</h4>
                      <ul className="space-y-1">
                        {selected.artifacts.map((a, idx) => (
                          <li key={idx} className="flex items-center justify-between rounded border border-black/10 px-2 py-1 text-xs dark:border-white/10">
                            <span className="truncate text-[10px]">{a.name || `artifact-${idx}`}</span>
                            {a.url ? (
                              <a
                                href={absUrl(a.url, apiBase)}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 rounded border border-black/10 px-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-800"
                              >
                                <FileDown size={12} />
                              </a>
                            ) : (
                              <span className="opacity-60">—</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </section>

                {/* Métriques JaCoCo */}
                {selected.jacoco_metrics ? (
                  <section className="rounded-xl border border-black/10 p-3 dark:border-white/10">
                    <h3 className="mb-2 flex items-center gap-1 text-sm font-medium">
                      <BarChart3 size={16} /> Couverture de Code
                    </h3>
                    <CoverageBar
                      label="Lignes"
                      percentage={selected.jacoco_metrics.line_coverage}
                      total={selected.jacoco_metrics.lines_total}
                      covered={selected.jacoco_metrics.lines_covered}
                    />
                    <CoverageBar
                      label="Branches"
                      percentage={selected.jacoco_metrics.branch_coverage}
                      total={selected.jacoco_metrics.branches_total}
                      covered={selected.jacoco_metrics.branches_covered}
                    />
                    <CoverageBar
                      label="Instructions"
                      percentage={selected.jacoco_metrics.instruction_coverage}
                      total={selected.jacoco_metrics.instructions_total}
                      covered={selected.jacoco_metrics.instructions_covered}
                    />
                  </section>
                ) : null}

                {/* Analyse de Qualité */}
                {selected.quality_analysis ? (
                  <section className="rounded-xl border border-black/10 p-3 dark:border-white/10">
                    <h3 className="mb-2 flex items-center gap-1 text-sm font-medium">
                      <Award size={16} /> Analyse de Qualité
                    </h3>
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-xs text-gray-600 dark:text-gray-400">Note globale</span>
                      <QualityGrade grade={selected.quality_analysis.grade} />
                    </div>
                    <div className="mb-3 space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Score global</span>
                        <span className="font-semibold">{selected.quality_analysis.overall_score}/100</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Qualité du test</span>
                        <span className="font-semibold">{selected.quality_analysis.test_quality_score}/100</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Couverture</span>
                        <span className="font-semibold">{selected.quality_analysis.coverage_score}/100</span>
                      </div>
                    </div>
                    {selected.quality_analysis.recommendations?.length ? (
                      <div>
                        <h4 className="mb-1 text-xs font-medium">Recommandations</h4>
                        <ul className="max-h-32 space-y-1 overflow-auto text-[10px] leading-relaxed">
                          {selected.quality_analysis.recommendations.map((rec, idx) => (
                            <li key={idx} className="rounded bg-black/5 px-2 py-1 dark:bg-white/5">
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </section>
                ) : null}
              </div>

              {/* Logs en pleine largeur en dessous */}
              <section className="rounded-xl border border-black/10 p-3 dark:border-white/10">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-sm font-medium">Logs</h3>
                  <div className="flex items-center gap-2">
                    <label className="text-xs inline-flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={polling}
                        onChange={(e) => setPolling(e.target.checked)}
                      />
                      Auto-refresh
                    </label>
                    {selected.logs_url ? (
                      <a
                        href={absUrl(selected.logs_url, apiBase)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded border border-black/10 px-2 py-1 text-xs hover:bg-gray-50 dark:hover:bg-gray-800"
                      >
                        Ouvrir brut
                      </a>
                    ) : null}
                  </div>
                </div>
                <CodeViewer
                  code={selected.logs || "(aucun log pour le moment)"}
                  language="text"
                  showLineNumbers={false}
                  maxHeight="60vh"
                  fileName="execution.log"
                />
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
