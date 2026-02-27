import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Button, Modal } from '@/components/ui'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'

function EmailPreviewModal({ isOpen, onClose, previewPayload }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['email-preview', previewPayload],
    queryFn: async () => {
      const response = await api.email.preview(previewPayload)
      return response.data
    },
    enabled: isOpen && !!previewPayload,
    retry: false,
  })

  useEffect(() => {
    if (isError) {
      toast.error('Error al generar vista previa', 'No se pudo obtener la vista previa del email')
    }
  }, [isError])

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Vista previa del email"
      className="max-w-3xl"
      footer={(
        <Button variant="secondary" onClick={onClose}>
          Cerrar
        </Button>
      )}
    >
      {isLoading ? (
        <div className="flex h-[420px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-secondary/30 p-3">
            <p className="mb-1 text-xs uppercase tracking-wide text-text-muted">Asunto</p>
            <p className="text-sm font-medium text-text-primary">{data?.subject || '-'}</p>
          </div>

          <div className="overflow-hidden rounded-md border border-border bg-white">
            <iframe
              title="Vista previa de email"
              srcDoc={data?.html || ''}
              sandbox=""
              className="h-[440px] w-full"
            />
          </div>
        </div>
      )}
    </Modal>
  )
}

export default EmailPreviewModal
