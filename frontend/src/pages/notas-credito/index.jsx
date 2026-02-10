import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus, Download, Loader2 } from 'lucide-react'
import { api } from '@/api/client'
import {
  Button,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Select,
} from '@/components/ui'
import { formatCUIT, formatCurrency, formatDate, formatComprobante } from '@/lib/utils'
import { toast } from '@/stores/toastStore'

// Tipos de comprobante de nota de crédito
const NC_TIPOS = [3, 8, 13] // NC A, NC B, NC C

function NotasCredito() {
  const [filters, setFilters] = useState({
    estado: '',
    page: 1,
  })
  const [downloadingNotaId, setDownloadingNotaId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['notas-credito', filters],
    queryFn: async () => {
      const params = { ...filters, per_page: 20 }
      // Filtrar solo notas de crédito
      const response = await api.facturas.list(params)
      return {
        ...response.data,
        items: response.data.items.filter((f) => NC_TIPOS.includes(f.tipo_comprobante)),
      }
    },
  })

  const notasCredito = data?.items || []

  const getEstadoBadge = (estado) => {
    const variants = {
      autorizado: 'success',
      error: 'error',
      pendiente: 'warning',
      borrador: 'default',
    }
    const labels = {
      autorizado: 'Autorizado',
      error: 'Error',
      pendiente: 'Pendiente',
      borrador: 'Borrador',
    }
    return <Badge variant={variants[estado]}>{labels[estado]}</Badge>
  }

  const handleDownloadPdf = async (nota) => {
    setDownloadingNotaId(nota.id)

    try {
      const response = await api.facturas.getComprobantePdf(nota.id, { force: true })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      const contentDisposition = response.headers?.['content-disposition'] || ''
      const fileNameMatch = contentDisposition.match(/filename="?([^\"]+)"?/)
      const fallback = `nota-credito-${nota.punto_venta || 0}-${nota.numero_comprobante || nota.id}.pdf`
      a.href = url
      a.download = fileNameMatch?.[1] || fallback
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Error', error.response?.data?.error || 'No se pudo generar el PDF')
    } finally {
      setDownloadingNotaId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select
            value={filters.estado}
            onChange={(e) => setFilters({ ...filters, estado: e.target.value, page: 1 })}
            className="w-40"
          >
            <option value="">Todos los estados</option>
            <option value="autorizado">Autorizado</option>
            <option value="error">Error</option>
            <option value="pendiente">Pendiente</option>
          </Select>
        </div>

        <Button icon={Plus}>
          Nueva Nota de Crédito
        </Button>
      </div>

      {/* Info card */}
      <div className="rounded-lg bg-primary/5 p-4">
        <p className="text-sm text-text-secondary">
          Las notas de crédito se pueden crear desde la sección <strong>Facturar</strong> importando
          un CSV con tipo de comprobante 3 (NC A), 8 (NC B) o 13 (NC C), e indicando el comprobante
          asociado (cbte_asoc_tipo, cbte_asoc_pto_vta, cbte_asoc_nro).
        </p>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Comprobante</TableHead>
              <TableHead>Facturador</TableHead>
              <TableHead>Receptor</TableHead>
              <TableHead>Comprobante Asociado</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Importe</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="w-28">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : notasCredito.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-text-muted">
                  No se encontraron notas de crédito
                </TableCell>
              </TableRow>
            ) : (
              notasCredito.map((nc) => {
                const isDownloading = downloadingNotaId === nc.id

                return (
                <TableRow key={nc.id}>
                  <TableCell>
                    <span className="font-medium">
                      {formatComprobante(nc.tipo_comprobante, nc.punto_venta, nc.numero_comprobante)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{nc.facturador?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(nc.facturador?.cuit)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{nc.receptor?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(nc.receptor?.doc_nro)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {nc.cbte_asoc_tipo ? (
                      <span className="text-sm">
                        {formatComprobante(nc.cbte_asoc_tipo, nc.cbte_asoc_pto_vta, nc.cbte_asoc_nro)}
                      </span>
                    ) : (
                      <span className="text-text-muted">-</span>
                    )}
                  </TableCell>
                  <TableCell>{formatDate(nc.fecha_emision)}</TableCell>
                  <TableCell className="font-medium text-error">
                    -{formatCurrency(nc.importe_total)}
                  </TableCell>
                  <TableCell>{getEstadoBadge(nc.estado)}</TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={nc.estado !== 'autorizado' || isDownloading}
                      onClick={() => handleDownloadPdf(nc)}
                    >
                      {isDownloading ? (
                        <Loader2 className="h-[18px] w-[18px] animate-spin" />
                      ) : (
                        <Download className="h-[18px] w-[18px]" />
                      )}
                      PDF
                    </Button>
                  </TableCell>
                </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

export default NotasCredito
