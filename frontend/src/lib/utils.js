import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount, currency = 'ARS') {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency,
  }).format(amount)
}

export function formatCUIT(cuit) {
  if (!cuit) return ''
  const clean = cuit.replace(/\D/g, '')
  if (clean.length !== 11) return cuit
  return `${clean.slice(0, 2)}-${clean.slice(2, 10)}-${clean.slice(10)}`
}

export function formatDate(date) {
  if (!date) return ''

  let parsedDate = null

  if (date instanceof Date) {
    parsedDate = date
  } else if (typeof date === 'string') {
    const raw = date.trim()

    if (/^\d{8}$/.test(raw)) {
      const year = Number(raw.slice(0, 4))
      const month = Number(raw.slice(4, 6)) - 1
      const day = Number(raw.slice(6, 8))
      parsedDate = new Date(year, month, day)
    } else if (/^\d{2}\/\d{2}\/\d{4}$/.test(raw)) {
      const [day, month, year] = raw.split('/').map(Number)
      parsedDate = new Date(year, month - 1, day)
    } else {
      parsedDate = new Date(raw)
    }
  } else {
    parsedDate = new Date(date)
  }

  if (Number.isNaN(parsedDate?.getTime?.())) {
    return String(date)
  }

  return new Intl.DateTimeFormat('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(parsedDate)
}

export function formatComprobante(tipo, puntoVenta, numero) {
  const tipos = {
    1: 'FC A',
    2: 'ND A',
    3: 'NC A',
    6: 'FC B',
    7: 'ND B',
    8: 'NC B',
    11: 'FC C',
    12: 'ND C',
    13: 'NC C',
  }
  const tipoStr = tipos[tipo] || `T${tipo}`
  const pv = String(puntoVenta).padStart(4, '0')
  const nro = String(numero).padStart(8, '0')
  return `${tipoStr} ${pv}-${nro}`
}
