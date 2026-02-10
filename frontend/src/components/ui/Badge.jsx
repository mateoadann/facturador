import { cn } from '@/lib/utils'

const variants = {
  success: 'bg-success-light text-success-foreground',
  error: 'bg-error-light text-error-foreground',
  warning: 'bg-warning-light text-warning-foreground',
  default: 'bg-secondary text-text-secondary',
}

function Badge({ variant = 'default', children, className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        variants[variant],
        className
      )}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', {
          'bg-success': variant === 'success',
          'bg-error': variant === 'error',
          'bg-warning': variant === 'warning',
          'bg-text-secondary': variant === 'default',
        })}
      />
      {children}
    </span>
  )
}

export default Badge
