import { forwardRef, useEffect, useRef } from 'react'
import AirDatepicker from 'air-datepicker'
import localeEs from 'air-datepicker/locale/es'
import 'air-datepicker/air-datepicker.css'
import { cn } from '@/lib/utils'

function parseISO(str, mode) {
  if (!str) return null
  if (mode === 'month') {
    const [year, month] = str.split('-').map(Number)
    if (!year || !month) return null
    return new Date(year, month - 1, 1)
  }
  const [year, month, day] = str.split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function toISO(date, mode) {
  if (!date) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  if (mode === 'month') return `${year}-${month}`
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const DatePicker = forwardRef(
  (
    {
      value = '',
      onChange,
      mode = 'day',
      label,
      error,
      disabled = false,
      className,
      min,
      max,
      placeholder,
      name,
      id,
      position,
    },
    ref
  ) => {
    const inputRef = useRef(null)
    const dpRef = useRef(null)
    const isInternalRef = useRef(false)

    // Merge forwarded ref with internal ref
    const setRef = (el) => {
      inputRef.current = el
      if (typeof ref === 'function') ref(el)
      else if (ref) ref.current = el
    }

    // Initialize and destroy datepicker
    useEffect(() => {
      if (!inputRef.current) return

      const isMonth = mode === 'month'
      const minDate = min ? parseISO(min, mode) : undefined
      const maxDate = max ? parseISO(max, mode) : undefined

      const dp = new AirDatepicker(inputRef.current, {
        locale: localeEs,
        dateFormat: isMonth ? 'MMMM yyyy' : 'dd/MM/yyyy',
        view: isMonth ? 'months' : 'days',
        minView: isMonth ? 'months' : 'days',
        minDate,
        maxDate,
        autoClose: true,
        isMobile: false,
        ...(position && { position }),
        onSelect: ({ date }) => {
          if (isInternalRef.current) return
          if (!date) {
            onChange?.('')
            return
          }
          const selected = Array.isArray(date) ? date[0] : date
          onChange?.(toISO(selected, mode))
        },
      })

      dpRef.current = dp

      // Set initial value
      if (value) {
        const parsed = parseISO(value, mode)
        if (parsed) {
          isInternalRef.current = true
          dp.selectDate(parsed, { silent: true })
          isInternalRef.current = false
        }
      }

      return () => {
        dp.destroy()
        dpRef.current = null
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [mode])

    // Sync value prop changes
    useEffect(() => {
      const dp = dpRef.current
      if (!dp) return

      isInternalRef.current = true

      if (value) {
        const parsed = parseISO(value, mode)
        if (parsed) {
          dp.clear({ silent: true })
          dp.selectDate(parsed, { silent: true })
        }
      } else {
        dp.clear({ silent: true })
      }

      isInternalRef.current = false
    }, [value, mode])

    // Sync min/max/disabled
    useEffect(() => {
      const dp = dpRef.current
      if (!dp) return

      const updates = {}
      if (min !== undefined) updates.minDate = min ? parseISO(min, mode) : false
      if (max !== undefined) updates.maxDate = max ? parseISO(max, mode) : false

      if (Object.keys(updates).length > 0) {
        dp.update(updates)
      }
    }, [min, max, mode])

    return (
      <div className={cn('flex flex-col gap-1.5', className)}>
        {label && (
          <label className="text-sm font-medium text-text-primary">{label}</label>
        )}
        <input
          ref={setRef}
          name={name}
          id={id}
          placeholder={placeholder}
          disabled={disabled}
          readOnly
          className={cn(
            'h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-text-primary',
            'placeholder:text-text-muted',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'cursor-pointer',
            error && 'border-error focus:ring-error'
          )}
        />
        {error && <span className="text-xs text-error">{error}</span>}
      </div>
    )
  }
)

DatePicker.displayName = 'DatePicker'

export default DatePicker
