import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Button, Modal } from '@/components/ui'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import { useThemeStore } from '@/stores/themeStore'

function injectDarkStyles(html) {
  if (!html) return ''
  const darkCss = `
    <style>
      body { background-color: #1e293b !important; color: #e2e8f0 !important; }
      body p, body strong, body span, body div, body td, body th, body li {
        color: #e2e8f0 !important;
      }
      body h1, body h2, body h3, body h4, body h5, body h6 {
        color: #60a5fa !important;
      }
      body hr { border-color: #334155 !important; }
    </style>
  `
  // Inject before </head> if present, otherwise before </body> or at start
  if (html.includes('</head>')) {
    return html.replace('</head>', `${darkCss}</head>`)
  }
  if (html.includes('<body')) {
    return html.replace('<body', `${darkCss}<body`)
  }
  return darkCss + html
}

function EmailPreviewModal({ isOpen, onClose, previewPayload }) {
  const darkMode = useThemeStore((s) => !!s.darkMode)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['email-preview', previewPayload],
    queryFn: async () => {
      const response = await api.email.preview(previewPayload)
      return response.data
    },
    enabled: isOpen && !!previewPayload,
    staleTime: Infinity,
    retry: false,
  })

  useEffect(() => {
    if (isError) {
      toast.error('Error al generar vista previa', 'No se pudo obtener la vista previa del email')
    }
  }, [isError])

  const iframeHtml = useMemo(() => {
    if (!data?.html) return ''
    return darkMode ? injectDarkStyles(data.html) : data.html
  }, [data?.html, darkMode])

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
      {isLoading || !data ? (
        <div className="flex h-[420px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-md border border-border bg-card p-3">
            <p className="mb-1 text-xs uppercase tracking-wide text-text-muted">Asunto</p>
            <p className="text-sm font-medium text-text-primary">{data?.subject || '-'}</p>
          </div>

          <div className="overflow-hidden rounded-md border border-border bg-card">
            <iframe
              title="Vista previa de email"
              srcDoc={iframeHtml}
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
