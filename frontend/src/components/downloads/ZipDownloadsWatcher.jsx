import { useEffect, useRef } from 'react'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import { useDownloadsStore } from '@/stores/downloadsStore'
import { useAuthStore } from '@/stores/authStore'

function ZipDownloadsWatcher() {
  const zipTasks = useDownloadsStore((s) => s.zipTasks)
  const removeZipTask = useDownloadsStore((s) => s.removeZipTask)
  const accessToken = useAuthStore((s) => s.accessToken)
  const canDownloadComprobante = useAuthStore((s) =>
    s.user?.permisos?.includes('facturas:comprobante') ?? false
  )
  const processingRef = useRef(false)

  useEffect(() => {
    if (!accessToken || !canDownloadComprobante || zipTasks.length === 0) return

    const checkNextTask = async () => {
      if (processingRef.current) return
      const current = zipTasks[0]
      if (!current) return

      processingRef.current = true
      try {
        const statusResponse = await api.jobs.getStatus(current.taskId)
        const status = statusResponse.data?.status

        if (status === 'SUCCESS') {
          const zipResponse = await api.downloads.getByTask(current.taskId)
          const blob = new Blob([zipResponse.data], { type: 'application/zip' })
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          const contentDisposition = zipResponse.headers?.['content-disposition'] || ''
          const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
          const fallbackName = `${current.loteEtiqueta || 'comprobantes-lote'}`
            .replace(/[\\/:*?"<>|]/g, ' ')
            .trim() || 'comprobantes-lote'

          a.href = url
          a.download = fileNameMatch?.[1] || `${fallbackName}.zip`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          window.URL.revokeObjectURL(url)

          toast.success('Descarga lista', `ZIP generado para lote ${current.loteEtiqueta || ''}`.trim())
          removeZipTask(current.taskId)
        } else if (status === 'FAILURE') {
          const error = statusResponse.data?.error || 'Fallo la generacion del ZIP'
          toast.error('Error', error)
          removeZipTask(current.taskId)
        }
      } catch (error) {
        if (error.response?.status === 404) {
          return
        }
        toast.error('Error', 'No se pudo consultar el estado de la descarga')
      } finally {
        processingRef.current = false
      }
    }

    checkNextTask()
    const interval = setInterval(checkNextTask, 2500)

    return () => {
      clearInterval(interval)
    }
  }, [zipTasks, accessToken, canDownloadComprobante, removeZipTask])

  return null
}

export default ZipDownloadsWatcher
