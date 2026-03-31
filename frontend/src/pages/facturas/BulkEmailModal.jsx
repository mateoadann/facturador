import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Modal, Select } from '@/components/ui'
import { api } from '@/api/client'

function BulkEmailModal({ isOpen, onClose, lotes, onConfirm, isSubmitting }) {
  const [loteId, setLoteId] = useState('')
  const [mode, setMode] = useState('no_enviados')

  useEffect(() => {
    if (!isOpen) return
    setMode('no_enviados')
    setLoteId((prev) => prev || lotes[0]?.id || '')
  }, [isOpen, lotes])

  const { data: previewData } = useQuery({
    queryKey: ['lotes', 'email-preview', loteId],
    queryFn: async () => {
      const response = await api.lotes.emailPreview(loteId)
      return response.data
    },
    enabled: isOpen && !!loteId,
  })

  const autorizadosCount = previewData?.autorizados || 0
  const emailsToSend = mode === 'todos'
    ? (previewData?.enviar_todos || 0)
    : (previewData?.enviar_no_enviados || 0)

  const handleConfirm = () => {
    if (!loteId || isSubmitting) return
    onConfirm({ loteId, mode })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Enviar emails del lote"
      className="max-w-lg"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={!loteId || isSubmitting || emailsToSend === 0}>
            {isSubmitting ? 'Iniciando...' : 'Ejecutar envio'}
          </Button>
        </>
      )}
    >
      <div className="space-y-4">
        <p className="text-sm text-text-secondary">
          Solo se enviaran facturas autorizadas. Se omiten automaticamente receptores sin email.
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

        <Select
          label="Modo de envio"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          disabled={isSubmitting}
        >
          <option value="no_enviados">Enviar solo a no enviados</option>
          <option value="todos">Enviar a todos (incluye reenvios)</option>
        </Select>

        <div className="space-y-1 rounded-md border border-border bg-secondary/30 p-3">
          <p className="text-sm text-text-primary">
            Comprobantes autorizados del lote: <span className="font-semibold">{autorizadosCount}</span>
          </p>
          <p className="text-sm text-text-primary">
            Emails a enviar con este modo: <span className="font-semibold">{emailsToSend}</span>
          </p>
        </div>
      </div>
    </Modal>
  )
}

export default BulkEmailModal
