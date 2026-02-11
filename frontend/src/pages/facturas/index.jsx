import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Download, Loader2, Mail, MailX, Send } from 'lucide-react'
import { api } from '@/api/client'
import {
  Button,
  Badge,
  Input,
  Select,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui'
import { formatCUIT, formatCurrency, formatDate, formatComprobante } from '@/lib/utils'
import { toast } from '@/stores/toastStore'

function Facturas() {
  const [filters, setFilters] = useState({
    estado: '',
    facturador_id: '',
    fecha_desde: '',
    fecha_hasta: '',
    page: 1,
  })
  const [downloadingFacturaId, setDownloadingFacturaId] = useState(null)
  const [sendingEmailId, setSendingEmailId] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['facturas', filters],
    queryFn: async () => {
      const params = { ...filters, per_page: 20 }
      Object.keys(params).forEach((key) => {
        if (!params[key]) delete params[key]
      })
      const response = await api.facturas.list(params)
      return response.data
    },
  })

  const { data: facturadoresData } = useQuery({
    queryKey: ['facturadores'],
    queryFn: async () => {
      const response = await api.facturadores.list({ per_page: 100 })
      return response.data
    },
  })

  const facturas = data?.items || []
  const facturadores = facturadoresData?.items || []

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

  const handleSendEmail = async (factura) => {
    setSendingEmailId(factura.id)
    try {
      await api.facturas.sendEmail(factura.id)
      toast.success('Email enviado', `Comprobante enviado a ${factura.receptor?.email || 'el receptor'}`)
    } catch (error) {
      toast.error('Error al enviar email', error.response?.data?.error || 'No se pudo enviar el email')
    } finally {
      setSendingEmailId(null)
    }
  }

  const handleDownloadPdf = async (factura) => {
    setDownloadingFacturaId(factura.id)

    try {
      const response = await api.facturas.getComprobantePdf(factura.id, { force: true })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      const contentDisposition = response.headers?.['content-disposition'] || ''
      const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/) 
      const fallback = `comprobante-${factura.punto_venta || 0}-${factura.numero_comprobante || factura.id}.pdf`
      a.href = url
      a.download = fileNameMatch?.[1] || fallback
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      toast.error('Error', error.response?.data?.error || 'No se pudo generar el PDF')
    } finally {
      setDownloadingFacturaId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-4">
        <Select
          label="Estado"
          value={filters.estado}
          onChange={(e) => setFilters({ ...filters, estado: e.target.value, page: 1 })}
          className="w-40"
        >
          <option value="">Todos</option>
          <option value="autorizado">Autorizado</option>
          <option value="error">Error</option>
          <option value="pendiente">Pendiente</option>
          <option value="borrador">Borrador</option>
        </Select>

        <Select
          label="Facturador"
          value={filters.facturador_id}
          onChange={(e) => setFilters({ ...filters, facturador_id: e.target.value, page: 1 })}
          className="w-48"
        >
          <option value="">Todos</option>
          {facturadores.map((f) => (
            <option key={f.id} value={f.id}>
              {f.razon_social}
            </option>
          ))}
        </Select>

        <Input
          label="Desde"
          type="date"
          value={filters.fecha_desde}
          onChange={(e) => setFilters({ ...filters, fecha_desde: e.target.value, page: 1 })}
          className="w-40"
        />

        <Input
          label="Hasta"
          type="date"
          value={filters.fecha_hasta}
          onChange={(e) => setFilters({ ...filters, fecha_hasta: e.target.value, page: 1 })}
          className="w-40"
        />

        <Button
          variant="secondary"
          onClick={() => setFilters({ estado: '', facturador_id: '', fecha_desde: '', fecha_hasta: '', page: 1 })}
        >
          Limpiar
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Comprobante</TableHead>
              <TableHead>Facturador</TableHead>
              <TableHead>Receptor</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Importe</TableHead>
              <TableHead>CAE</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="w-36">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : facturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-text-muted">
                  No se encontraron facturas
                </TableCell>
              </TableRow>
            ) : (
              facturas.map((factura) => {
                const isDownloading = downloadingFacturaId === factura.id

                return (
                <TableRow key={factura.id}>
                  <TableCell>
                    <span className="font-medium">
                      {formatComprobante(
                        factura.tipo_comprobante,
                        factura.punto_venta,
                        factura.numero_comprobante
                      )}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{factura.facturador?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(factura.facturador?.cuit)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{factura.receptor?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(factura.receptor?.doc_nro)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>{formatDate(factura.fecha_emision)}</TableCell>
                  <TableCell className="font-medium">
                    {formatCurrency(factura.importe_total)}
                  </TableCell>
                  <TableCell>
                    {factura.cae ? (
                      <div>
                        <p className="font-mono text-xs">{factura.cae}</p>
                        <p className="text-xs text-text-muted">
                          Vto: {formatDate(factura.cae_vencimiento)}
                        </p>
                      </div>
                    ) : (
                      <span className="text-text-muted">-</span>
                    )}
                  </TableCell>
                  <TableCell>{getEstadoBadge(factura.estado)}</TableCell>
                  <TableCell>
                    {factura.estado === 'autorizado' ? (
                      factura.email_enviado ? (
                        <div className="flex items-center gap-1.5 text-success">
                          <Mail className="h-4 w-4" />
                          <span className="text-xs">Enviado</span>
                        </div>
                      ) : factura.email_error ? (
                        <div className="flex items-center gap-1.5 text-error" title={factura.email_error}>
                          <MailX className="h-4 w-4" />
                          <span className="text-xs">Error</span>
                        </div>
                      ) : (
                        <span className="text-xs text-text-muted">-</span>
                      )
                    ) : (
                      <span className="text-xs text-text-muted">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={factura.estado !== 'autorizado' || isDownloading}
                        onClick={() => handleDownloadPdf(factura)}
                      >
                        {isDownloading ? (
                          <Loader2 className="h-[18px] w-[18px] animate-spin" />
                        ) : (
                          <Download className="h-[18px] w-[18px]" />
                        )}
                        PDF
                      </Button>
                      {factura.estado === 'autorizado' && factura.receptor?.email && (
                        <button
                          className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                          onClick={() => handleSendEmail(factura)}
                          disabled={sendingEmailId === factura.id}
                          title={factura.email_enviado ? 'Reenviar email' : 'Enviar email'}
                        >
                          {sendingEmailId === factura.id ? (
                            <Loader2 className="h-4 w-4 animate-spin text-text-secondary" />
                          ) : (
                            <Send className="h-4 w-4 text-text-secondary" />
                          )}
                        </button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data?.pages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <span className="text-sm text-text-secondary">
              Mostrando {facturas.length} de {data.total} facturas
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={filters.page <= 1}
                onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
              >
                Anterior
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={filters.page >= data.pages}
                onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
              >
                Siguiente
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Facturas
