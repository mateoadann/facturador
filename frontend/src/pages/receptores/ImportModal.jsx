import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileText, Download } from 'lucide-react'
import { api } from '@/api/client'
import { Button, Modal } from '@/components/ui'
import { toast } from '@/stores/toastStore'

function ImportModal({ isOpen, onClose, onSuccess }) {
  const [file, setFile] = useState(null)
  const [errors, setErrors] = useState([])

  const importMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('file', file)
      return api.receptores.import(formData)
    },
    onSuccess: (response) => {
      const { procesados, creados, actualizados, omitidos, errores } = response.data
      setErrors(errores || [])

      if (omitidos > 0) {
        toast.warning(
          'Importación parcial',
          `Procesados: ${procesados}. Creados: ${creados}. Actualizados: ${actualizados}. Omitidos: ${omitidos}.`
        )
      } else {
        toast.success(
          'Importación exitosa',
          `Procesados: ${procesados}. Creados: ${creados}. Actualizados: ${actualizados}.`
        )
      }

      onSuccess?.(response.data)
      if (omitidos === 0) {
        handleClose()
      }
    },
    onError: (error) => {
      const rawData = error.response?.data
      const apiMessage =
        (typeof rawData === 'object' && rawData?.error) ||
        (typeof rawData === 'string' ? rawData.slice(0, 240) : null)
      const message = apiMessage || `No se pudo importar el CSV${error.response?.status ? ` (HTTP ${error.response.status})` : ''}`
      const details = (typeof rawData === 'object' && rawData?.errores) || []
      setErrors([message, ...details])
      toast.error('Error al importar', message)
    },
  })

  const handleClose = () => {
    setFile(null)
    setErrors([])
    onClose()
  }

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
    }
  }

  const handleDownloadTemplate = () => {
    const content = 'cuit,razon_social,condicion_iva,email,direccion\n30123456789,Cliente Ejemplo SA,IVA Responsable Inscripto,cliente@ejemplo.com,Calle 123\n'
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'receptores_template.csv'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Importar Receptores"
      className="max-w-lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => importMutation.mutate()}
            disabled={!file || importMutation.isPending}
          >
            {importMutation.isPending ? 'Importando...' : 'Importar'}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <div>
          <h3 className="mb-3 text-sm font-medium text-text-primary">1. Descargar template CSV</h3>
          <div className="rounded-md bg-secondary/50 p-4">
            <p className="mb-3 text-sm text-text-secondary">
              Descargá el archivo base y completalo con tus receptores.
            </p>
            <Button variant="secondary" icon={Download} onClick={handleDownloadTemplate}>
              Descargar template .csv
            </Button>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-medium text-text-primary">2. Seleccionar archivo CSV</h3>
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-6 transition-colors hover:border-primary hover:bg-primary/5">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            {file ? (
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium text-text-primary">{file.name}</p>
                  <p className="text-sm text-text-muted">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="mb-2 h-8 w-8 text-text-muted" />
                <p className="text-sm text-text-secondary">
                  Click para seleccionar o arrastra un archivo CSV
                </p>
              </>
            )}
          </label>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-medium text-text-primary">3. Formato esperado</h3>
          <div className="rounded-md bg-secondary/50 p-3 text-xs text-text-secondary">
            <p className="mb-2">Columnas mínimas (requeridas):</p>
            <code className="block text-text-muted">cuit, razon_social</code>
            <p className="mt-2">Opcionales:</p>
            <code className="block text-text-muted">condicion_iva, email, direccion</code>
            <p className="mt-2">
              También se aceptan aliases como <code>doc_nro</code>, <code>razon social</code>,
              <code> condicion iva</code>, <code>correo</code>, <code>domicilio</code>.
            </p>
          </div>
        </div>

        {errors.length > 0 && (
          <div className="rounded-md bg-error-light p-3">
            <p className="mb-2 font-medium text-error-foreground">Errores encontrados:</p>
            <ul className="list-inside list-disc space-y-1 text-sm text-error-foreground">
              {errors.slice(0, 8).map((error, index) => (
                <li key={index}>{error}</li>
              ))}
              {errors.length > 8 && <li>... y {errors.length - 8} errores más</li>}
            </ul>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default ImportModal
