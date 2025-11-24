import { useState } from "react";
import { Copy, Check, Download, Maximize2 } from "lucide-react";

/**
 * Composant d'affichage de code avec syntax highlighting basique
 * Pour un highlighting complet, installer react-syntax-highlighter
 */
export default function CodeViewer({
  code = "",
  language = "java",
  showLineNumbers = true,
  maxHeight = "400px",
  fileName = "",
  editable = false,
  onChange = null
}) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const downloadCode = () => {
    const extensions = {
      java: "java",
      python: "py",
      javascript: "js",
      typescript: "ts",
      csharp: "cs",
      ruby: "rb",
      go: "go",
    };
    const ext = extensions[language] || "txt";
    const filename = fileName || `code.${ext}`;

    const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const lines = code.split("\n");

  return (
    <div className="overflow-hidden rounded-xl border border-black/10 bg-white dark:border-white/10 dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-black/10 bg-gray-50 px-4 py-2 dark:border-white/10 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
            {language}
          </span>
          {fileName && (
            <span className="text-xs text-gray-400">• {fileName}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={expanded ? "Réduire" : "Agrandir"}
          >
            <Maximize2 size={14} />
          </button>
          <button
            onClick={downloadCode}
            className="rounded p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700"
            title="Télécharger"
          >
            <Download size={14} />
          </button>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs font-medium hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            {copied ? (
              <>
                <Check size={14} className="text-emerald-600" />
                Copié
              </>
            ) : (
              <>
                <Copy size={14} />
                Copier
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code content */}
      <div
        className="overflow-auto bg-gray-950 p-4 font-mono text-sm"
        style={{ maxHeight: expanded ? "80vh" : maxHeight }}
      >
        {editable ? (
          <textarea
            value={code}
            onChange={(e) => onChange?.(e.target.value)}
            className="h-full w-full resize-none bg-transparent text-gray-100 outline-none"
            style={{ minHeight: maxHeight }}
          />
        ) : (
          <div className="relative">
            {showLineNumbers && (
              <div className="absolute left-0 top-0 select-none pr-4 text-right text-gray-600">
                {lines.map((_, i) => (
                  <div key={i} className="leading-6">
                    {i + 1}
                  </div>
                ))}
              </div>
            )}
            <pre className={`leading-6 ${showLineNumbers ? "pl-12" : ""}`}>
              <code className="text-gray-100">
                {code || "(vide)"}
              </code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
