import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, CheckCircle, XCircle, Clock, TrendingUp, Users } from 'lucide-react'
import { api } from '@/api/client'
import {
  Button,
  Input,
  MetricCard,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui'
import { formatCurrency } from '@/lib/utils'

function formatMonthOption(value) {
  const [year, month] = value.split('-').map(Number)
  const labels = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
  return `${labels[(month || 1) - 1]} ${year}`
}

function getCurrentMonthValue() {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${now.getFullYear()}-${month}`
}

function Dashboard() {
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonthValue())
  const [historico, setHistorico] = useState(false)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats', { selectedMonth, historico }],
    queryFn: async () => {
      const params = historico
        ? { historico: true }
        : { month: selectedMonth }
      const response = await api.dashboard.getStats(params)
      return response.data
    },
  })

  const trendData = stats?.facturacion_12_meses || []
  const topClientes = stats?.top_clientes || []
  const ticket = stats?.ticket_promedio || null
  const maxTrendTotal = trendData.reduce((max, item) => Math.max(max, item.total || 0), 0)

  const periodoLabel = historico
    ? 'Historico'
    : formatMonthOption(stats?.filtros_aplicados?.month || selectedMonth)

  const ticketVariation = ticket?.variacion_pct
  const ticketVariationLabel =
    ticketVariation == null
      ? 'Sin comparacion'
      : `${ticketVariation > 0 ? '+' : ''}${ticketVariation.toFixed(2)}% vs mes anterior`

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="mb-2 text-lg font-semibold text-text-primary">
              {historico ? 'Total Facturado del Periodo' : 'Total Facturado del Mes'}
            </h2>
            <p className="text-4xl font-bold text-primary">
              {formatCurrency(stats?.total_mes || 0)}
            </p>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <div className="w-full sm:w-auto sm:min-w-[220px]">
              <Input
                type="month"
                label="Mes de analisis"
                value={selectedMonth}
                disabled={historico}
                max={getCurrentMonthValue()}
                onChange={(event) => setSelectedMonth(event.target.value)}
              />
            </div>
            <Button
              variant={historico ? 'primary' : 'secondary'}
              onClick={() => setHistorico((prev) => !prev)}
            >
              Historico
            </Button>
          </div>
        </div>
        <p className="mt-3 text-sm text-text-secondary">
          Periodo seleccionado: <span className="font-medium text-text-primary">{periodoLabel}</span>
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={historico ? 'Facturas del Periodo' : 'Facturas del Mes'}
          value={stats?.facturas_mes || 0}
        />
        <MetricCard
          label={historico ? 'Autorizadas (Periodo)' : 'Autorizadas'}
          value={stats?.autorizadas || 0}
        />
        <MetricCard
          label="Con Errores"
          value={stats?.errores || 0}
        />
        <MetricCard
          label="Pendientes"
          value={stats?.pendientes || 0}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg bg-card p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Facturacion mensual (12 meses)</h2>
            <TrendingUp className="h-5 w-5 text-primary" />
          </div>

          <div className="space-y-3">
            {trendData.map((item) => {
              const widthPercent = maxTrendTotal > 0 ? ((item.total || 0) / maxTrendTotal) * 100 : 0
              return (
                <div key={item.month}>
                  <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                    <span className="text-text-secondary">{item.label}</span>
                    <span className="font-medium text-text-primary">
                      {formatCurrency(item.total || 0)} - {item.cantidad || 0} facturas
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-secondary">
                    <div
                      className="h-2 rounded-full bg-primary transition-all"
                      style={{ width: `${Math.max(widthPercent, 2)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="rounded-lg bg-card p-6 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary">Ticket promedio</h2>
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <p className="text-4xl font-bold text-primary">
            {formatCurrency(ticket?.valor || 0)}
          </p>
          <p className="mt-2 text-sm text-text-secondary">
            Total facturado: <span className="font-medium text-text-primary">{formatCurrency(ticket?.total || 0)}</span>
            {' '}en <span className="font-medium text-text-primary">{ticket?.cantidad || 0}</span> facturas autorizadas
          </p>
          <p className={`mt-2 text-sm ${ticketVariation != null && ticketVariation >= 0 ? 'text-success' : 'text-text-secondary'}`}>
            {ticketVariationLabel}
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-card p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text-primary">Top 10 clientes por facturacion</h2>
          <Users className="h-5 w-5 text-primary" />
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Cliente</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Cantidad</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>% participacion</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {topClientes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-text-muted">No hay datos para el periodo seleccionado</TableCell>
              </TableRow>
            ) : (
              topClientes.map((cliente) => (
                <TableRow key={cliente.receptor_id}>
                  <TableCell className="font-medium">{cliente.razon_social}</TableCell>
                  <TableCell>{cliente.doc_nro}</TableCell>
                  <TableCell>{cliente.cantidad}</TableCell>
                  <TableCell>{formatCurrency(cliente.total || 0)}</TableCell>
                  <TableCell>{cliente.porcentaje?.toFixed?.(2) || '0.00'}%</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Quick Actions */}
      <div className="rounded-lg bg-card p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">
          Acciones Rápidas
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <a
            href="/facturar"
            className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-secondary"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="font-medium text-text-primary">Nueva Factura</p>
              <p className="text-sm text-text-secondary">Importar CSV</p>
            </div>
          </a>
          <a
            href="/facturas"
            className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-secondary"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success/10">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="font-medium text-text-primary">Ver Facturas</p>
              <p className="text-sm text-text-secondary">Historial completo</p>
            </div>
          </a>
          <a
            href="/facturadores"
            className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-secondary"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-warning/10">
              <Clock className="h-6 w-6 text-warning" />
            </div>
            <div>
              <p className="font-medium text-text-primary">Facturadores</p>
              <p className="text-sm text-text-secondary">Configurar emisores</p>
            </div>
          </a>
          <a
            href="/receptores"
            className="flex items-center gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-secondary"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-error/10">
              <XCircle className="h-6 w-6 text-error" />
            </div>
            <div>
              <p className="font-medium text-text-primary">Receptores</p>
              <p className="text-sm text-text-secondary">Gestionar clientes</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
