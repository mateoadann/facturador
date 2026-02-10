import { cn } from '@/lib/utils'

function Table({ children, className }) {
  return (
    <div className={cn('w-full overflow-auto', className)}>
      <table className="w-full border-collapse">{children}</table>
    </div>
  )
}

function TableHeader({ children, className }) {
  return (
    <thead className={cn('bg-[#F9FAFB]', className)}>{children}</thead>
  )
}

function TableBody({ children, className }) {
  return <tbody className={className}>{children}</tbody>
}

function TableRow({ children, className, onClick }) {
  return (
    <tr
      className={cn(
        'border-b border-border transition-colors',
        onClick && 'cursor-pointer hover:bg-secondary/50',
        className
      )}
      onClick={onClick}
    >
      {children}
    </tr>
  )
}

function TableHead({ children, className }) {
  return (
    <th
      className={cn(
        'h-11 px-4 text-left text-xs font-semibold uppercase tracking-wider text-text-secondary',
        className
      )}
    >
      {children}
    </th>
  )
}

function TableCell({ children, className }) {
  return (
    <td className={cn('h-14 px-4 text-sm text-text-primary', className)}>
      {children}
    </td>
  )
}

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell }
