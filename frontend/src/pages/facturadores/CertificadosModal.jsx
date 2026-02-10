import { useState, useRef } from 'react'
import { Upload, FileCheck, AlertCircle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Button, Modal, Badge } from '@/components/ui'
import { toast } from '@/stores/toastStore'
import { formatCUIT } from '@/lib/utils'

function CertificadosModal({ facturador, isOpen, onClose }) {
  const queryClient = useQueryClient()
  const certRef = useRef(null)
  const keyRef = useRef(null)
  const [certFile, setCertFile] = useState(null)
  const [keyFile, setKeyFile] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: async ({ id, cert, key }) => {
      const formData = new FormData()
      formData.append('cert', cert)
      formData.append('key', key)
      return api.facturadores.uploadCerts(id, formData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['facturadores'])
      toast.success('Certificados cargados', 'Los certificados se cargaron correctamente')
      handleClose()
    },
    onError: (error) => {
      toast.error(
        'Error al cargar certificados',
        error.response?.data?.error || 'No se pudieron cargar los certificados'
      )
    },
  })

  const handleClose = () => {
    setCertFile(null)
    setKeyFile(null)
    onClose()
  }

  const handleUpload = () => {
    if (!certFile || !keyFile) {
      toast.warning('Archivos requeridos', 'Seleccioná ambos archivos (certificado y clave)')
      return
    }
    uploadMutation.mutate({
      id: facturador.id,
      cert: certFile,
      key: keyFile,
    })
  }

  if (!facturador) return null

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Cargar Certificados"
      className="max-w-lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            icon={Upload}
            onClick={handleUpload}
            disabled={!certFile || !keyFile || uploadMutation.isPending}
          >
            {uploadMutation.isPending ? 'Cargando...' : 'Cargar Certificados'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Info del facturador */}
        <div className="rounded-md bg-secondary p-3">
          <p className="text-sm font-medium text-text-primary">
            {facturador.razon_social}
          </p>
          <p className="text-xs text-text-muted">
            CUIT: {formatCUIT(facturador.cuit)} — PV: {facturador.punto_venta}
          </p>
        </div>

        {/* Estado actual */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-text-secondary">Estado actual:</span>
          {facturador.tiene_certificados ? (
            <Badge variant="success">Certificados cargados</Badge>
          ) : (
            <Badge variant="error">Sin certificados</Badge>
          )}
        </div>

        {facturador.tiene_certificados && (
          <div className="flex items-center gap-2 rounded-md bg-warning-light p-3 text-sm text-warning-foreground">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>Cargar nuevos certificados reemplazará los existentes.</span>
          </div>
        )}

        {/* Certificado (.crt/.pem) */}
        <div>
          <label className="mb-2 block text-sm font-medium text-text-primary">
            Certificado (.crt / .pem)
          </label>
          <input
            ref={certRef}
            type="file"
            accept=".crt,.pem,.cer"
            onChange={(e) => setCertFile(e.target.files[0] || null)}
            className="hidden"
          />
          <button
            onClick={() => certRef.current?.click()}
            className="flex w-full items-center gap-3 rounded-lg border-2 border-dashed border-border p-4 text-left transition-colors hover:border-primary hover:bg-primary/5"
          >
            {certFile ? (
              <FileCheck className="h-5 w-5 text-success" />
            ) : (
              <Upload className="h-5 w-5 text-text-muted" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium text-text-primary">
                {certFile ? certFile.name : 'Seleccionar certificado'}
              </p>
              <p className="text-xs text-text-muted">
                {certFile
                  ? `${(certFile.size / 1024).toFixed(1)} KB`
                  : 'Archivo .crt, .pem o .cer'}
              </p>
            </div>
          </button>
        </div>

        {/* Clave privada (.key) */}
        <div>
          <label className="mb-2 block text-sm font-medium text-text-primary">
            Clave Privada (.key)
          </label>
          <input
            ref={keyRef}
            type="file"
            accept=".key,.pem"
            onChange={(e) => setKeyFile(e.target.files[0] || null)}
            className="hidden"
          />
          <button
            onClick={() => keyRef.current?.click()}
            className="flex w-full items-center gap-3 rounded-lg border-2 border-dashed border-border p-4 text-left transition-colors hover:border-primary hover:bg-primary/5"
          >
            {keyFile ? (
              <FileCheck className="h-5 w-5 text-success" />
            ) : (
              <Upload className="h-5 w-5 text-text-muted" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium text-text-primary">
                {keyFile ? keyFile.name : 'Seleccionar clave privada'}
              </p>
              <p className="text-xs text-text-muted">
                {keyFile
                  ? `${(keyFile.size / 1024).toFixed(1)} KB`
                  : 'Archivo .key o .pem'}
              </p>
            </div>
          </button>
        </div>

        {uploadMutation.error && (
          <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
            {uploadMutation.error.response?.data?.error || 'Error al cargar certificados'}
          </div>
        )}
      </div>
    </Modal>
  )
}

export default CertificadosModal
