import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'

const TIPOS_COMPROBANTE = [
  { id: 1, nombre: 'Factura A' },
  { id: 2, nombre: 'Nota de Debito A' },
  { id: 3, nombre: 'Nota de Credito A' },
  { id: 6, nombre: 'Factura B' },
  { id: 7, nombre: 'Nota de Debito B' },
  { id: 8, nombre: 'Nota de Credito B' },
  { id: 11, nombre: 'Factura C' },
  { id: 12, nombre: 'Nota de Debito C' },
  { id: 13, nombre: 'Nota de Credito C' },
  { id: 51, nombre: 'Factura M' },
  { id: 52, nombre: 'Nota de Debito M' },
  { id: 53, nombre: 'Nota de Credito M' },
]

function Ayuda() {
  const openGuide = async () => {
    const popup = window.open('', '_blank')
    if (!popup) {
      toast.error('No se pudo abrir la guia', 'Habilita ventanas emergentes e intenta nuevamente')
      return
    }

    popup.document.title = 'Cargando guia...'
    popup.document.body.innerHTML = '<p style="font-family: sans-serif; padding: 16px;">Cargando guia...</p>'

    try {
      const response = await api.help.getImportCsvGuide()
      const blob = new Blob([response.data], { type: 'text/html;charset=utf-8' })
      const blobUrl = URL.createObjectURL(blob)
      popup.location.replace(blobUrl)
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
    } catch (error) {
      popup.close()
      toast.error('Error al cargar ayuda', error.response?.data?.error || 'No se pudo cargar la guía')
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-lg font-semibold text-text-primary">Guia de importacion CSV</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Abri la guia completa en otra pestana para seguir el paso a paso.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button variant="secondary" icon={ExternalLink} onClick={openGuide}>
            Abrir guia completa
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-5">
        <h3 className="text-base font-semibold text-text-primary">Cheatsheet rapido: IDs de comprobantes</h3>
        <p className="mt-1 text-sm text-text-secondary">
          Usa estos IDs en importacion CSV y filtros para encontrar comprobantes mas rapido.
        </p>

        <div className="mt-4 overflow-hidden rounded-md border border-border">
          <table className="w-full text-sm">
            <thead className="bg-secondary/60 text-left">
              <tr>
                <th className="w-24 px-4 py-2 text-text-primary">ID</th>
                <th className="px-4 py-2 text-text-primary">Tipo de comprobante</th>
              </tr>
            </thead>
            <tbody>
              {TIPOS_COMPROBANTE.map((tipo) => (
                <tr key={tipo.id} className="border-t border-border">
                  <td className="px-4 py-2 font-mono text-text-primary">{tipo.id}</td>
                  <td className="px-4 py-2 text-text-secondary">{tipo.nombre}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Ayuda
