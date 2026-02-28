import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileText, Download, ChevronDown } from 'lucide-react'
import { api } from '@/api/client'
import { Button, Input, Modal } from '@/components/ui'
import { toast } from '@/stores/toastStore'

const TEMPLATE_XLSX_URL = '/templates/facturas_template.xlsx'

function ImportModal({ isOpen, onClose, onSuccess }) {
  const [file, setFile] = useState(null)
  const [etiqueta, setEtiqueta] = useState('')
  const [errors, setErrors] = useState([])
  const [isTemplateOpen, setIsTemplateOpen] = useState(false)
  const [isFormatoOpen, setIsFormatoOpen] = useState(false)

  const importMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('etiqueta', etiqueta.trim())
      formData.append('tipo', 'factura')
      return api.facturas.import(formData)
    },
    onSuccess: (response) => {
      const { lote, errores_parseo, errores_creacion } = response.data
      if (errores_parseo?.length > 0 || errores_creacion?.length > 0) {
        setErrors([...errores_parseo, ...errores_creacion])
        toast.warning('Importación con errores', `Se importaron ${lote.total_facturas} facturas con algunos errores`)
      } else {
        toast.success('Importación exitosa', `Se importaron ${lote.total_facturas} facturas`)
        onSuccess(lote.id)
        handleClose()
      }
    },
    onError: (error) => {
      const apiError = error.response?.data?.error || 'No se pudo importar el CSV'
      const apiDetails = error.response?.data?.details
      const detailList = Array.isArray(apiDetails) ? apiDetails : []
      setErrors(detailList.length > 0 ? detailList : [apiError])
      toast.error('Error al importar', apiError)
    },
  })

  const handleClose = () => {
    setFile(null)
    setEtiqueta('')
    setErrors([])
    setIsTemplateOpen(false)
    setIsFormatoOpen(false)
    onClose()
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      if (!etiqueta) {
        setEtiqueta(selectedFile.name.replace('.csv', ''))
      }
    }
  }

  const handleDownloadTemplate = () => {
    const link = document.createElement('a')
    link.href = TEMPLATE_XLSX_URL
    link.download = 'facturas_template.xlsx'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Importar Facturas"
      className="max-w-lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => importMutation.mutate()}
            disabled={!file || !etiqueta.trim() || importMutation.isPending}
          >
            {importMutation.isPending ? 'Importando...' : 'Importar'}
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Step 0: Download template */}
        <div>
          <button
            type="button"
            onClick={() => setIsTemplateOpen((prev) => !prev)}
            className="flex w-full items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-left text-sm font-medium text-text-primary hover:bg-secondary/50"
          >
            <span>0. Descargar template XLSX</span>
            <ChevronDown
              className={`h-4 w-4 text-text-secondary transition-transform ${isTemplateOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {isTemplateOpen && (
            <div className="mt-3 rounded-md bg-secondary/50 p-4">
              <p className="mb-3 text-sm text-text-secondary">
                Descargá el archivo base con todas las columnas disponibles para completar tus facturas.
              </p>
              <Button variant="secondary" icon={Download} onClick={handleDownloadTemplate}>
                Descargar template .xlsx
              </Button>
            </div>
          )}
        </div>

        {/* Step 1: Select file */}
        <div>
          <h3 className="mb-3 text-sm font-medium text-text-primary">
            1. Seleccionar archivo CSV
          </h3>
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
                  <p className="text-sm text-text-muted">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
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

        {/* Step 2: Format info */}
        <div>
          <button
            type="button"
            onClick={() => setIsFormatoOpen((prev) => !prev)}
            className="flex w-full items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-left text-sm font-medium text-text-primary hover:bg-secondary/50"
          >
            <span>2. Formato esperado</span>
            <ChevronDown
              className={`h-4 w-4 text-text-secondary transition-transform ${isFormatoOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {isFormatoOpen && (
            <div className="mt-3 rounded-md bg-secondary/50 p-3 text-xs text-text-secondary">
              <p className="mb-2">
                Podés completar el template .xlsx y luego exportarlo como CSV (UTF-8) para importarlo.
              </p>
              <p className="mb-2">Columnas requeridas:</p>
              <code className="block text-text-muted">
                facturador_cuit, receptor_cuit, tipo_comprobante, concepto,
                fecha_emision, importe_total, importe_neto
              </code>
              <p className="mt-2">
                La condición IVA del receptor se determina automáticamente desde el receptor/padrón.
              </p>
            </div>
          )}
        </div>

        {/* Step 3: Label */}
        <div>
          <Input
            label="Etiqueta del lote (requerido, unico)"
            placeholder="Ej: Import-Enero-2026"
            value={etiqueta}
            onChange={(e) => setEtiqueta(e.target.value)}
          />
          <p className="mt-1 text-xs text-text-muted">
            No se permiten etiquetas duplicadas dentro del tenant.
          </p>
        </div>

        {/* Errors */}
        {errors.length > 0 && (
          <div className="rounded-md bg-error-light p-3">
            <p className="mb-2 font-medium text-error-foreground">
              Errores encontrados:
            </p>
            <div className="max-h-56 overflow-y-auto pr-1">
              <ul className="list-inside list-disc space-y-1 text-sm text-error-foreground">
                {errors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default ImportModal
