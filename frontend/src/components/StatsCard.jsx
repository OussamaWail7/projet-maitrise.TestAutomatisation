import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function StatsCard({
  title,
  value,
  icon: Icon,
  trend = null, // { value: +5, direction: 'up' }
  description = "",
  color = "indigo"
}) {
  const colors = {
    indigo: "from-indigo-500 to-indigo-600",
    emerald: "from-emerald-500 to-emerald-600",
    amber: "from-amber-500 to-amber-600",
    rose: "from-rose-500 to-rose-600",
    purple: "from-purple-500 to-purple-600",
    blue: "from-blue-500 to-blue-600",
  };

  const gradientClass = colors[color] || colors.indigo;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-black/10 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-white/10 dark:bg-gray-900">
      {/* Background gradient */}
      <div className={`absolute right-0 top-0 h-32 w-32 bg-gradient-to-br ${gradientClass} opacity-10 blur-3xl`} />

      <div className="relative">
        {/* Icon */}
        {Icon && (
          <div className={`mb-3 inline-flex rounded-xl bg-gradient-to-br ${gradientClass} p-3 text-white`}>
            <Icon size={24} />
          </div>
        )}

        {/* Title */}
        <h3 className="mb-1 text-sm font-medium text-gray-600 dark:text-gray-400">
          {title}
        </h3>

        {/* Value */}
        <div className="mb-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            {value}
          </span>

          {/* Trend */}
          {trend && (
            <span className={`flex items-center gap-1 text-sm font-medium ${
              trend.direction === 'up' ? 'text-emerald-600' :
              trend.direction === 'down' ? 'text-rose-600' :
              'text-gray-500'
            }`}>
              {trend.direction === 'up' && <TrendingUp size={16} />}
              {trend.direction === 'down' && <TrendingDown size={16} />}
              {trend.direction === 'neutral' && <Minus size={16} />}
              {trend.value > 0 && '+'}{trend.value}%
            </span>
          )}
        </div>

        {/* Description */}
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
