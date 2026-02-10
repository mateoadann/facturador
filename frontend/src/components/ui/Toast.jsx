import { X, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useToastStore } from '@/stores/toastStore'

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const styles = {
  success: 'border-success bg-success-light text-success-foreground',
  error: 'border-error bg-error-light text-error-foreground',
  warning: 'border-warning bg-warning-light text-warning-foreground',
  info: 'border-primary bg-primary/5 text-primary',
}

function ToastItem({ toast }) {
  const removeToast = useToastStore((s) => s.removeToast)
  const Icon = icons[toast.type] || Info

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-4 shadow-lg animate-in slide-in-from-right',
        styles[toast.type]
      )}
    >
      <Icon className="mt-0.5 h-5 w-5 flex-shrink-0" />
      <div className="flex-1">
        {toast.title && (
          <p className="text-sm font-semibold">{toast.title}</p>
        )}
        {toast.message && (
          <p className="text-sm opacity-90">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="flex-shrink-0 rounded p-0.5 opacity-70 hover:opacity-100"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <div className="fixed right-4 top-4 z-[100] flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  )
}

export default ToastContainer
