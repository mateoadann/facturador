import { forwardRef } from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

const Checkbox = forwardRef(({ className, checked, onChange, ...props }, ref) => {
  return (
    <button
      ref={ref}
      role="checkbox"
      aria-checked={checked}
      onClick={() => onChange?.(!checked)}
      className={cn(
        'flex h-5 w-5 items-center justify-center rounded border-[1.5px] transition-colors',
        checked
          ? 'border-primary bg-primary'
          : 'border-border bg-card hover:border-primary/50',
        className
      )}
      {...props}
    >
      {checked && <Check className="h-3.5 w-3.5 text-primary-foreground" />}
    </button>
  )
})

Checkbox.displayName = 'Checkbox'

export default Checkbox
