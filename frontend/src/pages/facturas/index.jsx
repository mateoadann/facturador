import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Eye, Loader2, Mail, MailX, Send, SlidersHorizontal } from 'lucide-react'
import { api } from '@/api/client'
import {
  Button,
  Badge,
  ErrorBadgeInfo,
  Progress,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui'
import { formatCUIT } from '@/lib/utils'
import { useJobStatus } from '@/hooks/useJobStatus'
import { usePermission } from '@/hooks/usePermission'
import { toast } from '@/stores/toastStore'
import { useDownloadsStore } from '@/stores/downloadsStore'
import BulkEmailModal from './BulkEmailModal'
import BulkPdfDownloadModal from './BulkPdfDownloadModal'
import FacturasFiltersSidebar from './FacturasFiltersSidebar'
import FacturaViewModal from './FacturaViewModal'

const TIPO_COMPROBANTE_LABELS = {
  1: 'Factura A',
  2: 'Nota de Debito A',
  3: 'Nota de Credito A',
  6: 'Factura B',
  7: 'Nota de Debito B',
  8: 'Nota de Credito B',
  11: 'Factura C',
  12: 'Nota de Debito C',
  13: 'Nota de Credito C',
}

function formatDateShort(date) {
  if (!date) return ''
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return String(date)
  const day = String(parsed.getDate()).padStart(2, '0')
  const month = String(parsed.getMonth() + 1).padStart(2, '0')
  const year = String(parsed.getFullYear()).slice(-2)
  return `${day}/${month}/${year}`
}

function formatComprobanteSimple(tipo, numero) {
  const tipoStr = TIPO_COMPROBANTE_LABELS[tipo] || `T${tipo}`
  if (numero == null) return tipoStr
  return `${tipoStr} ${Number(numero)}`
}

function Facturas() {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState({
    estadoVista: 'finalizados',
    facturador_id: '',
    lote_ids: [],
    receptor_ids: [],
    tipo_comprobantes: [],
    fecha_desde: '',
    fecha_hasta: '',
    page: 1,
  })
  const [downloadingFacturaId, setDownloadingFacturaId] = useState(null)
  const [sendingEmailId, setSendingEmailId] = useState(null)
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)
  const [isBulkPdfModalOpen, setIsBulkPdfModalOpen] = useState(false)
  const [isFiltersOpen, setIsFiltersOpen] = useState(false)
  const [emailTaskId, setEmailTaskId] = useState(null)
  const [selectedFacturaId, setSelectedFacturaId] = useState(null)
  const canSendEmail = usePermission('email:enviar')
  const canDownloadComprobante = usePermission('facturas:comprobante')
  const addZipTask = useDownloadsStore((s) => s.addZipTask)

  const { data, isLoading } = useQuery({
    queryKey: ['facturas', filters],
    queryFn: async () => {
      const { estadoVista, ...rest } = filters
      const params = { ...rest, per_page: 20 }
      if (estadoVista === 'finalizados') {
        params.estados = 'autorizado,error'
      } else {
        params.estado = estadoVista
      }
      Object.keys(params).forEach((key) => {
        if (!params[key]) delete params[key]
      })
      if (Array.isArray(params.lote_ids) && params.lote_ids.length > 0) {
        params.lote_ids = params.lote_ids.join(',')
      } else {
        delete params.lote_ids
      }
      if (Array.isArray(params.receptor_ids) && params.receptor_ids.length > 0) {
        params.receptor_ids = params.receptor_ids.join(',')
      } else {
        delete params.receptor_ids
      }
      if (Array.isArray(params.tipo_comprobantes) && params.tipo_comprobantes.length > 0) {
        params.tipo_comprobantes = params.tipo_comprobantes.join(',')
      } else {
        delete params.tipo_comprobantes
      }
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

  const { data: lotesData } = useQuery({
    queryKey: ['lotes', { para_email: true }],
    queryFn: async () => {
      const response = await api.lotes.list({ para_email: true, per_page: 200 })
      return response.data
    },
    enabled: canSendEmail || canDownloadComprobante,
  })

  const { data: lotesFiltersData } = useQuery({
    queryKey: ['lotes', { per_page: 200 }],
    queryFn: async () => {
      const response = await api.lotes.list({ per_page: 200 })
      return response.data
    },
  })

  const { data: receptoresData } = useQuery({
    queryKey: ['receptores', { per_page: 300 }],
    queryFn: async () => {
      const response = await api.receptores.list({ per_page: 300 })
      return response.data
    },
  })

  const { data: emailJobStatus } = useJobStatus(emailTaskId, {
    enabled: !!emailTaskId,
  })

  const { data: lotesProcesandoData } = useQuery({
    queryKey: ['lotes', { estado: 'procesando', per_page: 50 }],
    queryFn: async () => {
      const response = await api.lotes.list({ estado: 'procesando', per_page: 50 })
      return response.data
    },
    refetchInterval: 2000,
  })

  const loteProcesando = (lotesProcesandoData?.items || [])[0] || null

  const { data: facturacionJobStatus } = useJobStatus(loteProcesando?.celery_task_id, {
    enabled: !!loteProcesando?.celery_task_id,
    refetchInterval: 2000,
  })

  const sendLoteEmailsMutation = useMutation({
    mutationFn: ({ loteId, mode }) => api.lotes.sendEmails(loteId, { mode }),
    onSuccess: (response) => {
      setEmailTaskId(response?.data?.task_id || null)
      setIsBulkModalOpen(false)
      toast.info('Envio de emails iniciado', 'El lote se esta procesando en segundo plano')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo iniciar el envio masivo')
    },
  })

  const generarZipLoteMutation = useMutation({
    mutationFn: ({ loteId }) => api.lotes.generarComprobantesZip(loteId),
    onSuccess: (response, { loteId }) => {
      const taskId = response?.data?.task_id
      if (taskId) {
        const selectedLote = lotes.find((l) => l.id === loteId)
        addZipTask({
          taskId,
          loteId,
          loteEtiqueta: selectedLote?.etiqueta || 'sin etiqueta',
          createdAt: new Date().toISOString(),
        })
      }
      setIsBulkPdfModalOpen(false)
      toast.info('Generacion de ZIP encolada', 'El archivo se descargara automaticamente al finalizar')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo iniciar la descarga del lote')
    },
  })

  const facturas = data?.items || []
  const facturadores = facturadoresData?.items || []
  const lotes = lotesData?.items || []
  const lotesFiltros = lotesFiltersData?.items || []
  const receptores = receptoresData?.items || []

  const activeFiltersCount = [
    filters.estadoVista !== 'finalizados',
    !!filters.facturador_id,
    filters.lote_ids.length > 0,
    filters.receptor_ids.length > 0,
    filters.tipo_comprobantes.length > 0,
    !!filters.fecha_desde,
    !!filters.fecha_hasta,
  ].filter(Boolean).length

  const hasPagination = (data?.total || 0) > 0

  const renderPagination = (position) => (
    <div className={`flex items-center justify-between px-4 py-3 ${position === 'top' ? 'border-b border-border' : 'border-t border-border'}`}>
      <span className="text-sm text-text-secondary">
        Página {data?.page || filters.page} de {data?.pages || 1} · Mostrando {facturas.length} de {data?.total || 0} facturas
      </span>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={(data?.page || filters.page) <= 1}
          onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
        >
          Anterior
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={(data?.page || filters.page) >= (data?.pages || 1)}
          onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
        >
          Siguiente
        </Button>
      </div>
    </div>
  )

  const getEstadoBadge = (estado, factura) => {
    if (estado === 'error') {
      return (
        <ErrorBadgeInfo
          errorCodigo={factura?.error_codigo}
          errorMensaje={factura?.error_mensaje}
          floating
        />
      )
    }

    const variants = {
      autorizado: 'success',
      pendiente: 'warning',
      borrador: 'default',
    }
    const labels = {
      autorizado: 'Autorizado',
      pendiente: 'Pendiente',
      borrador: 'Borrador',
    }
    return <Badge variant={variants[estado]}>{labels[estado]}</Badge>
  }

  const handleSendEmail = async (factura) => {
    if (!canSendEmail) {
      return
    }

    setSendingEmailId(factura.id)
    try {
      await api.facturas.sendEmail(factura.id)
      queryClient.invalidateQueries(['facturas'])
      queryClient.invalidateQueries(['lotes'])
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
      const cuit = String(factura.facturador?.cuit || '').replace(/\D/g, '').padStart(11, '0')
      const tipo = String(factura.tipo_comprobante || 0).padStart(3, '0')
      const ptoVta = String(factura.punto_venta || 0).padStart(5, '0')
      const nro = String(factura.numero_comprobante || 0).padStart(8, '0')
      const fallback = `${cuit}_${tipo}_${ptoVta}_${nro}.pdf`
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

  if (emailJobStatus?.status === 'SUCCESS' || emailJobStatus?.status === 'FAILURE') {
    if (emailTaskId) {
      setEmailTaskId(null)
      queryClient.invalidateQueries(['facturas'])
      queryClient.invalidateQueries(['lotes'])

      if (emailJobStatus.status === 'SUCCESS') {
        const result = emailJobStatus.result
        toast.success(
          'Envio masivo completado',
          result
            ? `${result.sent || 0} enviados, ${result.skipped || 0} omitidos, ${result.errors || 0} errores`
            : 'Proceso completado'
        )
      } else {
        toast.error('Error al enviar emails', emailJobStatus.error || 'Fallo la tarea de envio masivo')
      }
    }
  }

  return (
    <div className="space-y-6">
      {loteProcesando && (
        <Progress
          value={facturacionJobStatus?.progress?.percent || 0}
          max={100}
          label={`Facturando lote: ${loteProcesando.etiqueta}`}
          showCount
          current={facturacionJobStatus?.progress?.current || 0}
          total={facturacionJobStatus?.progress?.total || loteProcesando.total_facturas || 0}
        />
      )}

      {emailTaskId && emailJobStatus?.status === 'PROGRESS' && (
        <Progress
          value={emailJobStatus.progress?.percent || 0}
          max={100}
          label="Enviando emails del lote..."
          showCount
          current={emailJobStatus.progress?.current || 0}
          total={emailJobStatus.progress?.total || 0}
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          variant="secondary"
          icon={SlidersHorizontal}
          onClick={() => setIsFiltersOpen(true)}
        >
          Filtros{activeFiltersCount > 0 ? ` (${activeFiltersCount})` : ''}
        </Button>

        <div className="flex flex-wrap items-center gap-3">
        {canSendEmail && (
          <Button
            variant="secondary"
            icon={Send}
            onClick={() => setIsBulkModalOpen(true)}
            disabled={sendLoteEmailsMutation.isPending || !!emailTaskId}
          >
            Enviar emails del lote
          </Button>
        )}

        {canDownloadComprobante && (
          <Button
            variant="secondary"
            icon={Download}
            onClick={() => setIsBulkPdfModalOpen(true)}
            disabled={generarZipLoteMutation.isPending}
          >
            Descarga PDF de Lotes
          </Button>
        )}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        {hasPagination && renderPagination('top')}

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Comprobante</TableHead>
              <TableHead>Receptor</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Ver</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Email</TableHead>
              <TableHead className="w-36">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : facturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-text-muted">
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
                      {formatComprobanteSimple(
                        factura.tipo_comprobante,
                        factura.numero_comprobante
                      )}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{factura.receptor?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(factura.receptor?.doc_nro)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>{formatDateShort(factura.fecha_emision)}</TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setSelectedFacturaId(factura.id)}
                    >
                      <Eye className="h-[16px] w-[16px]" />
                      Ver
                    </Button>
                  </TableCell>
                  <TableCell>{getEstadoBadge(factura.estado, factura)}</TableCell>
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
                      {canSendEmail && factura.estado === 'autorizado' && factura.receptor?.email && (
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

        {hasPagination && renderPagination('bottom')}
      </div>

      <BulkEmailModal
        isOpen={isBulkModalOpen}
        onClose={() => setIsBulkModalOpen(false)}
        lotes={lotes}
        onConfirm={({ loteId, mode }) => sendLoteEmailsMutation.mutate({ loteId, mode })}
        isSubmitting={sendLoteEmailsMutation.isPending}
      />

      <BulkPdfDownloadModal
        isOpen={isBulkPdfModalOpen}
        onClose={() => setIsBulkPdfModalOpen(false)}
        lotes={lotes}
        onConfirm={({ loteId }) => generarZipLoteMutation.mutate({ loteId })}
        isSubmitting={generarZipLoteMutation.isPending}
      />

      <FacturasFiltersSidebar
        isOpen={isFiltersOpen}
        onClose={() => setIsFiltersOpen(false)}
        filters={filters}
        onApply={setFilters}
        facturadores={facturadores}
        lotes={lotesFiltros}
        receptores={receptores}
      />

      <FacturaViewModal
        isOpen={!!selectedFacturaId}
        onClose={() => setSelectedFacturaId(null)}
        facturaId={selectedFacturaId}
      />
    </div>
  )
}

export default Facturas
