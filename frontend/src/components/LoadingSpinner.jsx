export default function LoadingSpinner({ size = "md", text = "" }) {
  const sizes = {
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-3",
    lg: "h-12 w-12 border-4",
    xl: "h-16 w-16 border-4",
  };

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`animate-spin rounded-full border-indigo-600 border-t-transparent ${sizes[size] || sizes.md}`}
        role="status"
        aria-label="Loading"
      />
      {text && (
        <p className="text-sm text-gray-600 dark:text-gray-400">{text}</p>
      )}
    </div>
  );
}

export function LoadingOverlay({ text = "Chargement..." }) {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <LoadingSpinner size="lg" text={text} />
    </div>
  );
}
