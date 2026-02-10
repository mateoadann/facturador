import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

const Input = forwardRef(({ className, label, error, ...props }, ref) => {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-text-primary">{label}</label>
      )}
      <input
        ref={ref}
        className={cn(
          'h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-text-primary',
          'placeholder:text-text-muted',
          'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
          'disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-error focus:ring-error',
          className
        )}
        {...props}
      />
      {error && <span className="text-xs text-error">{error}</span>}
    </div>
  )
})

Input.displayName = 'Input'

export default Input
