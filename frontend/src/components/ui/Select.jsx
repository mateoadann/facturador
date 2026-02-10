import { forwardRef } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const Select = forwardRef(({ className, label, error, children, ...props }, ref) => {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-text-primary">{label}</label>
      )}
      <div className="relative">
        <select
          ref={ref}
          className={cn(
            'h-10 w-full appearance-none rounded-md border border-border bg-card px-3 pr-10 text-sm text-text-primary',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-error focus:ring-error',
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-secondary pointer-events-none" />
      </div>
      {error && <span className="text-xs text-error">{error}</span>}
    </div>
  )
})

Select.displayName = 'Select'

export default Select
