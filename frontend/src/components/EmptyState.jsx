import { FileQuestion, Inbox, Search, AlertCircle } from "lucide-react";

export default function EmptyState({
  icon = "inbox",
  title = "Aucune donnée",
  description = "Il n'y a rien à afficher pour le moment.",
  action = null
}) {
  const icons = {
    inbox: <Inbox size={48} className="opacity-40" />,
    search: <Search size={48} className="opacity-40" />,
    file: <FileQuestion size={48} className="opacity-40" />,
    alert: <AlertCircle size={48} className="opacity-40" />,
  };

  return (
    <div className="flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-black/10 bg-gray-50/50 p-12 text-center dark:border-white/10 dark:bg-gray-900/30">
      <div className="mb-4 text-gray-400 dark:text-gray-600">
        {icons[icon] || icons.inbox}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-gray-700 dark:text-gray-300">
        {title}
      </h3>
      <p className="mb-6 max-w-sm text-sm text-gray-500 dark:text-gray-400">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}
