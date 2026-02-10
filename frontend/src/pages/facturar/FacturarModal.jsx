import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { api } from '@/api/client'
import { Button, Modal, Select } from '@/components/ui'
import { toast } from '@/stores/toastStore'
import { formatCUIT } from '@/lib/utils'

function FacturarModal({ isOpen, onClose, lotes, selectedLote, onSuccess }) {
  const [loteId, setLoteId] = useState(selectedLote || '')
  const [facturadorId, setFacturadorId] = useState('')

  const { data: facturadoresData } = useQuery({
    queryKey: ['facturadores', { activo: true, per_page: 200 }],
    queryFn: async () => {
      const response = await api.facturadores.list({ activo: true, per_page: 200 })
      return response.data
    },
    enabled: isOpen,
  })

  const facturadoresDisponibles = (facturadoresData?.items || []).filter(
    (facturador) => facturador.activo && facturador.tiene_certificados
  )

  const facturarMutation = useMutation({
    mutationFn: ({ loteId: targetLoteId, facturadorId: targetFacturadorId }) =>
      api.lotes.facturar(targetLoteId, { facturador_id: targetFacturadorId }),
    onSuccess: (response) => {
      toast.info('Facturación iniciada', 'El lote se está procesando...')
      onSuccess(response.data.task_id)
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo iniciar la facturación')
    },
  })

  const handleFacturar = () => {
    if (loteId && facturadorId) {
      facturarMutation.mutate({ loteId, facturadorId })
    }
  }

  const handleSelectLote = (value) => {
    setLoteId(value)
    if (!value) {
      setFacturadorId('')
      return
    }

    const lote = lotes.find((item) => item.id === value)
    setFacturadorId(lote?.facturador?.id || '')
  }

  const selectedLoteData = lotes.find((l) => l.id === loteId)
  const selectedFacturador = facturadoresDisponibles.find((f) => f.id === facturadorId)
  const pendientes = selectedLoteData?.total_facturas - (selectedLoteData?.facturas_ok || 0) - (selectedLoteData?.facturas_error || 0)

  useEffect(() => {
    if (!isOpen) return
    const nextLoteId = selectedLote || ''
    setLoteId(nextLoteId)

    setFacturadorId('')
  }, [isOpen, selectedLote])

  useEffect(() => {
    if (!isOpen || !loteId || facturadorId) return

    const lote = lotes.find((item) => item.id === loteId)
    if (lote?.facturador?.id) {
      setFacturadorId(lote.facturador.id)
    }
  }, [isOpen, lotes, loteId, facturadorId])

  useEffect(() => {
    if (!facturadorId) return

    const exists = facturadoresDisponibles.some((f) => f.id === facturadorId)
    if (!exists) {
      setFacturadorId('')
    }
  }, [facturadorId, facturadoresDisponibles])

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Facturar Lote"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={handleFacturar}
            disabled={!loteId || !facturadorId || facturarMutation.isPending}
          >
            {facturarMutation.isPending ? 'Iniciando...' : 'Confirmar'}
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        <Select
          label="Seleccione el lote a facturar:"
          value={loteId}
          onChange={(e) => handleSelectLote(e.target.value)}
        >
          <option value="">Seleccionar...</option>
          {lotes.map((lote) => (
            <option key={lote.id} value={lote.id}>
              {lote.etiqueta} ({lote.total_facturas} facturas)
            </option>
          ))}
        </Select>

        <Select
          label="Seleccione el facturador para emitir:"
          value={facturadorId}
          onChange={(e) => setFacturadorId(e.target.value)}
          disabled={!loteId}
        >
          <option value="">Seleccionar...</option>
          {facturadoresDisponibles.map((facturador) => (
            <option key={facturador.id} value={facturador.id}>
              {facturador.razon_social} ({formatCUIT(facturador.cuit)}) - PV {facturador.punto_venta} - {facturador.ambiente}
            </option>
          ))}
        </Select>

        {selectedFacturador && (
          <div className="rounded-md bg-secondary p-3 text-sm text-text-secondary">
            <p>
              Facturador: <span className="font-medium text-text-primary">{selectedFacturador.razon_social}</span>
            </p>
            <p>
              CUIT: <span className="font-medium text-text-primary">{formatCUIT(selectedFacturador.cuit)}</span>
            </p>
            <p>
              Punto de venta: <span className="font-medium text-text-primary">{selectedFacturador.punto_venta}</span>
              {' '}| Ambiente: <span className="font-medium text-text-primary">{selectedFacturador.ambiente === 'production' ? 'production' : 'testing'}</span>
            </p>
          </div>
        )}

        {loteId && facturadoresDisponibles.length === 0 && (
          <div className="rounded-md bg-warning-light p-3 text-sm text-warning-foreground">
            No hay facturadores activos con certificados cargados para seleccionar.
          </div>
        )}

        {loteId && (
          <div className="flex items-start gap-3 rounded-md bg-warning-light p-4">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-warning" />
            <div className="text-sm">
              <p className="font-medium text-warning-foreground">
                Atención
              </p>
              <p className="mt-1 text-warning-foreground/80">
                Se procesarán {pendientes || selectedLoteData?.total_facturas} facturas pendientes.
                Este proceso no se puede deshacer.
              </p>
            </div>
          </div>
        )}

        {facturarMutation.error && (
          <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
            {facturarMutation.error.response?.data?.error || 'Error al iniciar facturación'}
          </div>
        )}
      </div>
    </Modal>
  )
}

export default FacturarModal
