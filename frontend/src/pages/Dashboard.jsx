import { useQuery } from '@tanstack/react-query'
import { FileText, CheckCircle, XCircle, Clock } from 'lucide-react'
import { api } from '@/api/client'
import { MetricCard } from '@/components/ui'
import { formatCurrency } from '@/lib/utils'

function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await api.dashboard.getStats()
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Facturas del Mes"
          value={stats?.facturas_mes || 0}
        />
        <MetricCard
          label="Autorizadas"
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

      {/* Total Facturado */}
      <div className="rounded-lg bg-card p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold text-text-primary">
          Total Facturado del Mes
        </h2>
        <p className="text-4xl font-bold text-primary">
          {formatCurrency(stats?.total_mes || 0)}
        </p>
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
