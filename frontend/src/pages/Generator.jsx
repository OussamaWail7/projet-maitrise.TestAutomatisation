// src/pages/Generator.jsx
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { apiJson, getApiBase } from "../lib/api";
import CodeViewer from "../components/CodeViewer";
import LoadingSpinner from "../components/LoadingSpinner";

export default function Generator() {
  const [code, setCode] = useState("");
  const [testType, setTestType] = useState("unit");
  const [language, setLanguage] = useState("java");
  const [provider, setProvider] = useState(localStorage.getItem("provider") || "gemini");
  const [model, setModel] = useState(() => {
    const savedProvider = localStorage.getItem("provider") || "gemini";
    return localStorage.getItem(`${savedProvider}Model`) || "";
  });

  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");
  const [savedId, setSavedId] = useState(null);

  // Modèles disponibles
  const [availableModels, setAvailableModels] = useState({});
  const [loadingModels, setLoadingModels] = useState(true);
  const [defaultConfig, setDefaultConfig] = useState({ provider: "gemini", model: "" });

  // Map UI -> backend
  const backendTypeMap = {
    unit: "unit",
    api: "rest-assured",
    ui: "selenium",
  };

  // Refs
  const codeRef = useRef(null);
  const resultRef = useRef(null);
  const abortRef = useRef(null);

  // Auto-resize textareas
  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.style.height = "0px";
      codeRef.current.style.height = Math.min(codeRef.current.scrollHeight, 480) + "px";
    }
  }, [code]);

  useEffect(() => {
    if (resultRef.current) {
      resultRef.current.style.height = "0px";
      resultRef.current.style.height = Math.min(resultRef.current.scrollHeight, 480) + "px";
    }
  }, [result]);

  // Charger les modèles disponibles au montage
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await apiJson("/models");
        setAvailableModels(data.by_provider || {});
        setDefaultConfig({
          provider: data.default_provider || "gemini",
          model: data.default_model || ""
        });

        // Si pas de modèle sélectionné, utiliser le défaut
        if (!model && data.default_model) {
          setModel(data.default_model);
          localStorage.setItem(`${provider}Model`, data.default_model);
        }
      } catch (err) {
        console.error("Erreur chargement modèles:", err);
        // Fallback si l'endpoint n'est pas accessible
        setAvailableModels({});
      } finally {
        setLoadingModels(false);
      }
    };
    fetchModels();
  }, []);

  // Mettre à jour le modèle quand le provider change
  useEffect(() => {
    const savedModel = localStorage.getItem(`${provider}Model`);
    const models = availableModels[provider] || [];

    if (savedModel && models.find(m => m.id === savedModel)) {
      setModel(savedModel);
    } else if (models.length > 0) {
      const firstModel = models[0].id;
      setModel(firstModel);
      localStorage.setItem(`${provider}Model`, firstModel);
    }
  }, [provider, availableModels]);

  const onProviderChange = (newProvider) => {
    setProvider(newProvider);
    localStorage.setItem("provider", newProvider);
  };

  const onModelChange = (newModel) => {
    setModel(newModel);
    localStorage.setItem(`${provider}Model`, newModel);
  };

  const handlePreview = async () => {
    if (!code.trim()) {
      setError("Veuillez saisir un extrait de code avant de lancer la génération.");
      return;
    }
    setLoading(true);
    setError("");
    setResult("");
    setStatus("idle");

    // Timeout & abort
    abortRef.current?.abort?.();
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);
    abortRef.current = controller;

    try {
      const mappedType = backendTypeMap[testType] ?? "unit";
      const payload = {
        code,
        test_type: mappedType,
        language,
        provider,
        model: model || undefined
      };

      const data = await apiJson("/generate-test-preview", {
        method: "POST",
        body: payload,
        signal: controller.signal
      });

      const cleaned = (data.result || "").replace(/```(?:\w+)?|```/g, "").trim();
      setResult(cleaned);
      setStatus("draft");
    } catch (e) {
      if (e.name === 'AbortError') {
        setError("Génération interrompue (timeout 120s). Le modèle est peut-être trop lent.");
      } else {
        setError(e.message || "Erreur lors de la génération.");
      }
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!result.trim()) {
      toast.error("Aucun résultat à enregistrer.");
      return;
    }
    setSaving(true);
    setError("");

    try {
      const mappedType = backendTypeMap[testType] ?? "unit";
      const payload = {
        code,
        generated_test: result,
        test_type: mappedType,
        language,
        status: "confirmed",
        provider,
        model
      };
      const created = await apiJson("/test-cases", { method: "POST", body: payload });
      setSavedId(created?._id || null);
      setStatus("confirmed");
      toast.success("Cas de test enregistré.");
    } catch (e) {
      setError(e.message || "Erreur lors de l'enregistrement.");
    } finally {
      setSaving(false);
    }
  };

  const handleRetry = () => {
    setResult("");
    setStatus("idle");
    setError("");
  };

  const copyToClipboard = () => {
    if (!result) return;
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const downloadResult = () => {
    if (!result) return;
    const extByLang = { java:"java", python:"py", javascript:"js", typescript:"ts", csharp:"cs", ruby:"rb", go:"go" };
    const nameByType = { unit:"UnitTest", api:"ApiTest", ui:"UiTest" };
    const ext = extByLang[language] || "txt";
    const blob = new Blob([result], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${nameByType[testType]}.${ext}`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  // Obtenir les modèles du provider actuel
  const currentProviderModels = availableModels[provider] || [];
  const hasModels = currentProviderModels.length > 0;

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: .5 }}
        className="rounded-3xl border border-black/10 bg-white/70 p-6 backdrop-blur-md dark:border-white/10 dark:bg-gray-900/60"
      >
        <h1 className="text-2xl font-bold">
          Génération automatisée de cas de test
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
          Saisissez un extrait de code, sélectionnez le type de test, le langage, et le provider.
          Prévisualisez, éditez si nécessaire, puis confirmez pour enregistrer en base.
        </p>
        <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
          <span>API: <code className="rounded bg-black/5 px-1">{getApiBase()}</code></span>
          {loadingModels && <span className="text-indigo-600">⟳ Chargement des modèles...</span>}
          {!loadingModels && hasModels && (
            <span className="text-emerald-600">✓ {Object.values(availableModels).flat().length} modèles détectés</span>
          )}
        </div>
      </motion.div>

      {/* Grille principale */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Entrée */}
        <section className="rounded-2xl border border-black/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-gray-900">
          <h2 className="mb-3 text-base font-semibold">Entrée</h2>

          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium">Code à analyser</label>
            <span className="text-xs text-gray-500">
              {code.split('\n').length} lignes • {code.length} caractères
            </span>
          </div>
          <textarea
            ref={codeRef}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Ex. : méthode métier, contrôleur REST ou composant UI."
            className="w-full resize-none rounded-xl border border-black/10 bg-gray-50 p-3 font-mono text-[13px] leading-5
                       text-gray-900 outline-none focus:ring-2 focus:ring-indigo-400 dark:bg-gray-950 dark:text-gray-100"
          />

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              <span className="mb-1 block">Type de test</span>
              <select
                value={testType}
                onChange={(e) => setTestType(e.target.value)}
                className="w-full rounded-xl border border-black/10 bg-white p-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400
                           dark:bg-gray-950 dark:text-gray-100"
              >
                <option value="unit">Unit (unitaire)</option>
                <option value="api">API (HTTP)</option>
                <option value="ui">UI (end-to-end)</option>
              </select>
            </label>

            <label className="text-sm">
              <span className="mb-1 block">Langage cible</span>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl border border-black/10 bg-white p-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400
                           dark:bg-gray-950 dark:text-gray-100"
              >
                <option value="java">Java</option>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="typescript">TypeScript</option>
                <option value="csharp">C#</option>
                <option value="ruby">Ruby</option>
                <option value="go">Go</option>
              </select>
            </label>

            <label className="text-sm">
              <span className="mb-1 block">
                Provider LLM
                {loadingModels && <span className="ml-2 text-xs text-gray-400">(chargement...)</span>}
              </span>
              <select
                value={provider}
                onChange={(e) => onProviderChange(e.target.value)}
                disabled={loadingModels}
                className="w-full rounded-xl border border-black/10 bg-white p-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400
                           dark:bg-gray-950 dark:text-gray-100 disabled:opacity-60"
              >
                {Object.keys(availableModels).length > 0 ? (
                  Object.keys(availableModels).map((p) => (
                    <option key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)} ({availableModels[p].length} modèle{availableModels[p].length > 1 ? 's' : ''})
                    </option>
                  ))
                ) : (
                  <>
                    <option value="gemini">Gemini</option>
                    <option value="ollama">Ollama</option>
                    <option value="mistral">Mistral</option>
                  </>
                )}
              </select>
            </label>

            <label className="text-sm">
              <span className="mb-1 block">
                Modèle
                {hasModels && (
                  <span className="ml-2 text-xs text-gray-400">
                    ({currentProviderModels.length} disponible{currentProviderModels.length > 1 ? 's' : ''})
                  </span>
                )}
              </span>
              <select
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
                disabled={loadingModels || !hasModels}
                className="w-full rounded-xl border border-black/10 bg-white p-2 text-sm outline-none focus:ring-2 focus:ring-indigo-400
                           dark:bg-gray-950 dark:text-gray-100 disabled:opacity-60"
              >
                {hasModels ? (
                  currentProviderModels.map((m) => (
                    <option key={m.id} value={m.id} title={m.description}>
                      {m.name}
                    </option>
                  ))
                ) : (
                  <option value="">Aucun modèle disponible</option>
                )}
              </select>
              {hasModels && currentProviderModels.find(m => m.id === model)?.description && (
                <p className="mt-1 text-xs text-gray-500">
                  {currentProviderModels.find(m => m.id === model).description}
                </p>
              )}
            </label>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <button
              onClick={handlePreview}
              disabled={loading || !code.trim() || !model}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-700 px-4 py-2
                         text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Génération en cours…
                </>
              ) : (
                "Prévisualiser (sans enregistrer)"
              )}
            </button>

            <button
              onClick={handleRetry}
              disabled={loading || (!result && status !== "draft")}
              className="inline-flex w-full items-center justify-center rounded-xl border border-black/10 px-4 py-2
                         text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Réinitialiser le résultat
            </button>
          </div>

          {!!error && (
            <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
              {error}
            </p>
          )}
        </section>

        {/* Résultat */}
        <section className="rounded-2xl border border-black/10 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-gray-900">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">Résultat (éditable)</h2>
              {result && (
                <span className="text-xs text-gray-500">
                  {result.split('\n').length} lignes • {result.length} caractères
                </span>
              )}
            </div>
          </div>

          {loading ? (
            <div className="flex h-[420px] items-center justify-center rounded-xl border border-black/10 bg-gray-50 dark:bg-gray-950">
              <LoadingSpinner size="lg" text="Génération du test en cours..." />
            </div>
          ) : result ? (
            <CodeViewer
              code={result}
              language={language}
              showLineNumbers={true}
              maxHeight="420px"
              fileName={`Test.${language === 'java' ? 'java' : language === 'python' ? 'py' : language === 'javascript' ? 'js' : 'txt'}`}
              editable={true}
              onChange={setResult}
            />
          ) : (
            <div className="flex h-[420px] items-center justify-center rounded-xl border border-dashed border-black/10 bg-gray-50/50 dark:bg-gray-950/50">
              <p className="text-sm text-gray-500">
                Le cas de test généré s'affichera ici. Vous pourrez l'éditer avant de confirmer.
              </p>
            </div>
          )}

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={handleConfirmSave}
              disabled={!result || saving}
              className="inline-flex items-center justify-center rounded-xl bg-emerald-700 px-4 py-2
                         text-sm font-medium text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Enregistrement…" : "Confirmer et enregistrer"}
            </button>
            <button
              onClick={async () => {
                if (!savedId) { toast.error("Enregistrez d'abord le test."); return; }
                try {
                  const d = await apiJson(`/test-cases/${savedId}/run`, { method: "POST", body: { language } });
                  toast.success(`Exécution lancée: ${d.execId}`);
                } catch (e) { toast.error(e.message); }
              }}
              disabled={!result || !savedId}
              className="inline-flex items-center justify-center rounded-xl border border-black/10 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60"
            >
              Exécuter maintenant
            </button>
            {status !== "idle" && (
              <span className={`text-xs ${status === "confirmed" ? "text-emerald-600" : "text-amber-600"}`}>
                Statut : {status}
              </span>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
