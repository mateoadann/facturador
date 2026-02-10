import { cn } from '@/lib/utils'

function Card({ className, children, ...props }) {
  return (
    <div
      className={cn(
        'rounded-lg bg-card p-5 shadow-sm',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function MetricCard({ label, value, className }) {
  return (
    <Card className={cn('flex flex-col gap-2', className)}>
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-3xl font-semibold text-text-primary">{value}</span>
    </Card>
  )
}

export { Card, MetricCard }
export default Card
