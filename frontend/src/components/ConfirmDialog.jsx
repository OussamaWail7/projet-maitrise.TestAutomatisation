import { AlertCircle, X } from "lucide-react";

export default function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirmer l'action",
  message = "Êtes-vous sûr de vouloir continuer ?",
  confirmText = "Confirmer",
  cancelText = "Annuler",
  variant = "warning", // "warning" | "danger" | "info"
}) {
  if (!isOpen) return null;

  const variants = {
    warning: {
      icon: "text-amber-600",
      button: "bg-amber-600 hover:bg-amber-700",
      bg: "bg-amber-50 dark:bg-amber-900/20",
    },
    danger: {
      icon: "text-rose-600",
      button: "bg-rose-600 hover:bg-rose-700",
      bg: "bg-rose-50 dark:bg-rose-900/20",
    },
    info: {
      icon: "text-indigo-600",
      button: "bg-indigo-600 hover:bg-indigo-700",
      bg: "bg-indigo-50 dark:bg-indigo-900/20",
    },
  };

  const style = variants[variant] || variants.warning;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-black/10 bg-white p-6 shadow-xl dark:border-white/10 dark:bg-gray-900">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-800"
          aria-label="Fermer"
        >
          <X size={16} />
        </button>

        {/* Icon */}
        <div className={`mb-4 inline-flex rounded-full ${style.bg} p-3`}>
          <AlertCircle size={24} className={style.icon} />
        </div>

        {/* Title */}
        <h2 id="dialog-title" className="mb-2 text-xl font-semibold">
          {title}
        </h2>

        {/* Message */}
        <p className="mb-6 text-sm text-gray-600 dark:text-gray-400">
          {message}
        </p>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={onConfirm}
            className={`flex-1 rounded-xl px-4 py-2 text-sm font-medium text-white transition ${style.button}`}
          >
            {confirmText}
          </button>
          <button
            onClick={onClose}
            className="flex-1 rounded-xl border border-black/10 px-4 py-2 text-sm font-medium transition hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            {cancelText}
          </button>
        </div>
      </div>
    </div>
  );
}
