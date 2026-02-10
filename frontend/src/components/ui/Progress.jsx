import { cn } from '@/lib/utils'

function Progress({ value = 0, max = 100, className, label, showCount, current, total }) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div className={cn('rounded-lg bg-card p-4 shadow-lg', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">{label}</span>
        {showCount && (
          <span className="text-sm font-medium text-text-secondary">
            {current}/{total}
          </span>
        )}
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-primary transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-text-muted">
        Procesando facturas... {Math.round(percentage)}%
      </p>
    </div>
  )
}

export default Progress
