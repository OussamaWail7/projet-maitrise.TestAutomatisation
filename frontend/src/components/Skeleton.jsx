// Composant Skeleton pour les loading states
export function Skeleton({ className = "", variant = "default" }) {
  const variants = {
    default: "h-4 w-full",
    title: "h-8 w-3/4",
    text: "h-4 w-5/6",
    circle: "h-12 w-12 rounded-full",
    button: "h-10 w-24",
    card: "h-32 w-full",
  };

  return (
    <div
      className={`animate-pulse rounded-lg bg-gray-200 dark:bg-gray-800 ${variants[variant] || variants.default} ${className}`}
      aria-label="Loading..."
    />
  );
}

export function SkeletonTable({ rows = 3, cols = 5 }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={`header-${i}`} variant="text" className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="flex gap-4">
          {Array.from({ length: cols }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} className="h-6 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-black/10 bg-white p-5 dark:border-white/10 dark:bg-gray-900">
      <Skeleton variant="title" className="mb-3" />
      <Skeleton variant="text" className="mb-2" />
      <Skeleton variant="text" className="mb-2 w-4/5" />
      <Skeleton variant="text" className="w-2/3" />
    </div>
  );
}
