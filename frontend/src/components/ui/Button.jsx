import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

const variants = {
  primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
  secondary: 'bg-card text-text-primary border border-border hover:bg-secondary',
  danger: 'bg-error text-text-on-dark hover:bg-error/90',
  ghost: 'text-text-secondary hover:bg-secondary',
}

const sizes = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
}

const Button = forwardRef(
  ({ className, variant = 'primary', size = 'md', children, icon: Icon, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {Icon && <Icon className="h-[18px] w-[18px]" />}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
