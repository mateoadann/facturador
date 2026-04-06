import { forwardRef } from 'react'
import { NumericFormat } from 'react-number-format'
import { cn } from '@/lib/utils'

const CurrencyInput = forwardRef(({ className, label, error, decimalScale = 2, onValueChange, ...props }, ref) => {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-text-primary">{label}</label>
      )}
      <NumericFormat
        getInputRef={ref}
        thousandSeparator="."
        decimalSeparator=","
        decimalScale={decimalScale}
        allowNegative={false}
        inputMode="decimal"
        onValueChange={onValueChange}
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

CurrencyInput.displayName = 'CurrencyInput'

export default CurrencyInput
