import { forwardRef } from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

const Checkbox = forwardRef(({ className, checked, onChange, label, disabled, ...props }, ref) => {
  const handleToggle = () => {
    if (disabled) return
    onChange?.(!checked)
  }

  return (
    <div
      className={cn('flex items-center gap-2', disabled && 'opacity-50')}
      {...props}
    >
      <button
        ref={ref}
        type="button"
        role="checkbox"
        aria-checked={checked}
        disabled={disabled}
        onClick={handleToggle}
        className={cn(
          'flex h-5 w-5 items-center justify-center rounded border-[1.5px] transition-colors',
          checked
            ? 'border-primary bg-primary'
            : 'border-border bg-card hover:border-primary/50',
          className
        )}
      >
        {checked && <Check className="h-3.5 w-3.5 text-primary-foreground" />}
      </button>
      {label && (
        <button
          type="button"
          onClick={handleToggle}
          disabled={disabled}
          className="text-sm text-text-primary"
        >
          {label}
        </button>
      )}
    </div>
  )
})

Checkbox.displayName = 'Checkbox'

export default Checkbox
