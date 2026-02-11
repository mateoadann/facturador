import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import {
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Input,
  Select,
  Button,
} from '@/components/ui'

const accionVariants = {
  'login:exitoso': 'primary',
  'login:fallido': 'error',
  'password:cambio': 'warning',
  'logout': 'default',
  'usuario:crear': 'success',
  'usuario:editar': 'warning',
  'usuario:activar': 'success',
  'usuario:desactivar': 'error',
  'facturador:crear': 'success',
  'facturador:editar': 'warning',
  'facturador:desactivar': 'error',
  'facturador:certificados': 'warning',
  'receptor:crear': 'success',
  'receptor:editar': 'warning',
  'receptor:eliminar': 'error',
  'lote:importar': 'success',
  'lote:facturar': 'primary',
  'lote:eliminar': 'error',
  'facturas:eliminar': 'error',
}

function Auditoria() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    accion: '',
    fecha_desde: '',
    fecha_hasta: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['audit', page, filters],
    queryFn: async () => {
      const params = { page, per_page: 20 }
      if (filters.accion) params.accion = filters.accion
      if (filters.fecha_desde) params.fecha_desde = filters.fecha_desde
      if (filters.fecha_hasta) params.fecha_hasta = filters.fecha_hasta
      const response = await api.audit.list(params)
      return response.data
    },
  })

  const logs = data?.items || []
  const totalPages = data?.pages || 1

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const handleFilter = () => {
    setPage(1)
  }

  const handleClearFilters = () => {
    setFilters({ accion: '', fecha_desde: '', fecha_hasta: '' })
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Filtros */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-card p-4">
        <Input
          label="Acción"
          placeholder="ej: login, usuario, facturador"
          value={filters.accion}
          onChange={(e) => setFilters({ ...filters, accion: e.target.value })}
          className="w-48"
        />
        <Input
          label="Desde"
          type="date"
          value={filters.fecha_desde}
          onChange={(e) => setFilters({ ...filters, fecha_desde: e.target.value })}
          className="w-40"
        />
        <Input
          label="Hasta"
          type="date"
          value={filters.fecha_hasta}
          onChange={(e) => setFilters({ ...filters, fecha_hasta: e.target.value })}
          className="w-40"
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleFilter}>
            Filtrar
          </Button>
          <Button variant="secondary" onClick={handleClearFilters}>
            Limpiar
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Usuario</TableHead>
              <TableHead>Acción</TableHead>
              <TableHead>Recurso</TableHead>
              <TableHead>IP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-text-muted">
                  No hay registros de auditoría
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-sm text-text-muted whitespace-nowrap">
                    {formatDate(log.created_at)}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="text-sm font-medium">{log.usuario_nombre || '-'}</p>
                      <p className="text-xs text-text-muted">{log.usuario_email || '-'}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={accionVariants[log.accion] || 'default'}>
                      {log.accion}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    {log.recurso ? (
                      <span>
                        {log.recurso}
                        {log.recurso_id && (
                          <span className="ml-1 text-xs text-text-muted">
                            ({log.recurso_id.substring(0, 8)}...)
                          </span>
                        )}
                      </span>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-text-muted font-mono">
                    {log.ip_address || '-'}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Paginación */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Anterior
          </Button>
          <span className="text-sm text-text-muted">
            Página {page} de {totalPages}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  )
}

export default Auditoria
