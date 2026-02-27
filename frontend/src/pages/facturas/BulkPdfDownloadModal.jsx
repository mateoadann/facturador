import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Modal, Select } from '@/components/ui'
import { api } from '@/api/client'

function BulkPdfDownloadModal({ isOpen, onClose, lotes, onConfirm, isSubmitting }) {
  const [loteId, setLoteId] = useState('')

  useEffect(() => {
    if (!isOpen) return
    setLoteId((prev) => prev || lotes[0]?.id || '')
  }, [isOpen, lotes])

  const { data: previewData } = useQuery({
    queryKey: ['lotes', 'comprobantes-zip-preview', loteId],
    queryFn: async () => {
      const response = await api.lotes.comprobantesZipPreview(loteId)
      return response.data
    },
    enabled: isOpen && !!loteId,
  })

  const autorizadosCount = previewData?.autorizados || 0

  const handleConfirm = () => {
    if (!loteId || isSubmitting || autorizadosCount === 0) return
    onConfirm({ loteId })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Descarga PDF de Lotes"
      className="max-w-lg"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={!loteId || isSubmitting || autorizadosCount === 0}>
            {isSubmitting ? 'Encolando...' : 'Confirmar'}
          </Button>
        </>
      )}
    >
      <div className="space-y-4">
        <p className="text-sm text-text-secondary">
          Se generara un ZIP con todos los comprobantes autorizados del lote seleccionado.
        </p>

        <Select
          label="Lote"
          value={loteId}
          onChange={(e) => setLoteId(e.target.value)}
          disabled={isSubmitting || lotes.length === 0}
        >
          <option value="">Seleccionar lote...</option>
          {lotes.map((lote) => (
            <option key={lote.id} value={lote.id}>
              {lote.etiqueta}
              {lote.facturador ? ` - ${lote.facturador.razon_social}` : ''}
              {` (${lote.total_facturas} facturas)`}
            </option>
          ))}
        </Select>

        <div className="space-y-1 rounded-md border border-border bg-secondary/30 p-3">
          <p className="text-sm text-text-primary">
            Comprobantes autorizados del lote: <span className="font-semibold">{autorizadosCount}</span>
          </p>
        </div>
      </div>
    </Modal>
  )
}

export default BulkPdfDownloadModal
