import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Play, Eye, Trash2 } from 'lucide-react'
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
  Checkbox,
  Progress,
} from '@/components/ui'
import { formatCUIT, formatCurrency, formatDate } from '@/lib/utils'
import ImportModal from './ImportModal'
import FacturarModal from './FacturarModal'
import ItemsModal from './ItemsModal'
import { useJobStatus } from '@/hooks/useJobStatus'
import { toast } from '@/stores/toastStore'

function Facturar() {
  const queryClient = useQueryClient()
  const [selectedLote, setSelectedLote] = useState(null)
  const [selectedFacturas, setSelectedFacturas] = useState([])
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [isFacturarOpen, setIsFacturarOpen] = useState(false)
  const [itemsFactura, setItemsFactura] = useState(null)
  const [activeTaskId, setActiveTaskId] = useState(null)

  // Fetch lotes
  const { data: lotesData } = useQuery({
    queryKey: ['lotes', { estado: 'pendiente' }],
    queryFn: async () => {
      const response = await api.lotes.list({ estado: 'pendiente' })
      return response.data
    },
  })

  // Fetch facturas del lote seleccionado
  const { data: facturasData, isLoading: isLoadingFacturas } = useQuery({
    queryKey: ['facturas', { lote_id: selectedLote }],
    queryFn: async () => {
      const response = await api.facturas.list({ lote_id: selectedLote })
      return response.data
    },
    enabled: !!selectedLote,
  })

  // Job status polling
  const { data: jobStatus } = useJobStatus(activeTaskId, {
    enabled: !!activeTaskId,
  })

  // Mutations
  const deleteFacturasMutation = useMutation({
    mutationFn: (ids) => api.facturas.bulkDelete(ids),
    onSuccess: (response) => {
      queryClient.invalidateQueries(['facturas'])
      queryClient.invalidateQueries(['lotes'])
      setSelectedFacturas([])

      const deletedLoteIds = response?.data?.deleted_lote_ids || []
      if (selectedLote && deletedLoteIds.includes(selectedLote)) {
        setSelectedLote(null)
      }

      toast.success('Facturas eliminadas correctamente')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudieron eliminar las facturas')
    },
  })

  const facturas = facturasData?.items || []
  const lotes = lotesData?.items || []

  useEffect(() => {
    if (!lotesData) return
    if (!selectedLote) return

    const stillExists = lotes.some((lote) => lote.id === selectedLote)
    if (!stillExists) {
      setSelectedLote(null)
      setSelectedFacturas([])
    }
  }, [lotes, lotesData, selectedLote])

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

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedFacturas(facturas.filter((f) => f.estado === 'pendiente').map((f) => f.id))
    } else {
      setSelectedFacturas([])
    }
  }

  const handleSelectFactura = (id, checked) => {
    if (checked) {
      setSelectedFacturas([...selectedFacturas, id])
    } else {
      setSelectedFacturas(selectedFacturas.filter((fId) => fId !== id))
    }
  }

  const handleFacturarSuccess = (taskId) => {
    setActiveTaskId(taskId)
    setIsFacturarOpen(false)
  }

  // Check if job completed
  if (jobStatus?.status === 'SUCCESS' || jobStatus?.status === 'FAILURE') {
    if (activeTaskId) {
      queryClient.invalidateQueries(['facturas'])
      queryClient.invalidateQueries(['lotes'])
      setActiveTaskId(null)
      if (jobStatus.status === 'SUCCESS') {
        const result = jobStatus.result
        toast.success(
          'Lote procesado',
          result ? `${result.ok} autorizadas, ${result.errores} con error` : 'Facturación completada'
        )
      } else {
        toast.error('Error al facturar', jobStatus.error || 'Ocurrió un error al procesar el lote')
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Progress bar when processing */}
      {activeTaskId && jobStatus?.status === 'PROGRESS' && (
        <Progress
          value={jobStatus.progress?.percent || 0}
          max={100}
          label="Facturando lote..."
          showCount
          current={jobStatus.progress?.current || 0}
          total={jobStatus.progress?.total || 0}
        />
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Lote selector */}
          <select
            className="h-10 rounded-md border border-border bg-card px-3 text-sm"
            value={selectedLote || ''}
            onChange={(e) => setSelectedLote(e.target.value || null)}
          >
            <option value="">Seleccionar lote...</option>
            {lotes.map((lote) => (
              <option key={lote.id} value={lote.id}>
                {lote.etiqueta}
                {lote.facturador
                  ? ` - ${lote.facturador.razon_social} (${lote.facturador.ambiente})`
                  : ''}
                {` (${lote.total_facturas} facturas)`}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          {selectedFacturas.length > 0 && (
            <Button
              variant="danger"
              icon={Trash2}
              onClick={() => deleteFacturasMutation.mutate(selectedFacturas)}
            >
              Eliminar ({selectedFacturas.length})
            </Button>
          )}
          <Button
            variant="secondary"
            icon={Upload}
            onClick={() => setIsImportOpen(true)}
          >
            Importar CSV
          </Button>
          <Button
            icon={Play}
            onClick={() => setIsFacturarOpen(true)}
            disabled={!selectedLote || facturas.filter((f) => f.estado === 'pendiente').length === 0}
          >
            Facturar
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={
                    selectedFacturas.length > 0 &&
                    selectedFacturas.length === facturas.filter((f) => f.estado === 'pendiente').length
                  }
                  onChange={handleSelectAll}
                />
              </TableHead>
              <TableHead>Receptor</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Importe</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="w-20">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoadingFacturas ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : facturas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-text-muted">
                  {selectedLote
                    ? 'No hay facturas en este lote'
                    : 'Selecciona un lote para ver las facturas'}
                </TableCell>
              </TableRow>
            ) : (
              facturas.map((factura) => (
                <TableRow key={factura.id}>
                  <TableCell>
                    <Checkbox
                      checked={selectedFacturas.includes(factura.id)}
                      onChange={(checked) => handleSelectFactura(factura.id, checked)}
                      disabled={factura.estado !== 'pendiente'}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{factura.receptor?.razon_social}</p>
                      <p className="text-xs text-text-muted">
                        {formatCUIT(factura.receptor?.doc_nro)}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {factura.tipo_comprobante === 1 ? 'FC A' :
                     factura.tipo_comprobante === 6 ? 'FC B' :
                     factura.tipo_comprobante === 11 ? 'FC C' : `T${factura.tipo_comprobante}`}
                  </TableCell>
                  <TableCell>{formatDate(factura.fecha_emision)}</TableCell>
                  <TableCell>{formatCurrency(factura.importe_total)}</TableCell>
                  <TableCell>{getEstadoBadge(factura.estado)}</TableCell>
                  <TableCell>
                    <button
                      className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                      onClick={() => setItemsFactura(factura)}
                    >
                      <Eye className="h-4 w-4 text-text-secondary" />
                    </button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Modals */}
      <ImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={(loteId) => {
          setSelectedLote(loteId)
          setIsImportOpen(false)
          queryClient.invalidateQueries(['lotes'])
        }}
      />

      <FacturarModal
        isOpen={isFacturarOpen}
        onClose={() => setIsFacturarOpen(false)}
        lotes={lotes}
        selectedLote={selectedLote}
        onSuccess={handleFacturarSuccess}
      />

      <ItemsModal
        factura={itemsFactura}
        onClose={() => setItemsFactura(null)}
      />
    </div>
  )
}

export default Facturar
