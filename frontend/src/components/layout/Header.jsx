import { useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useDownloadsStore } from '@/stores/downloadsStore'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/facturar': 'Facturar',
  '/facturas': 'Ver Facturas',
  '/facturadores': 'Facturadores',
  '/receptores': 'Receptores',
  '/notas-credito': 'Notas de Crédito',
  '/consultar-comprobantes': 'Consultar Comprobantes',
  '/usuarios': 'Usuarios',
  '/auditoria': 'Auditoría',
  '/email': 'Configuración de Email',
}

function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Facturador'
  const zipTasks = useDownloadsStore((s) => s.zipTasks)
  const activeZipTasks = zipTasks.length

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>

      {activeZipTasks > 0 && (
        <div
          className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-3 py-1.5"
          aria-live="polite"
          title={`Descargas en proceso: ${activeZipTasks}`}
        >
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <span className="text-sm font-medium text-text-secondary">Generando ZIP...</span>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
            {activeZipTasks}
          </span>
        </div>
      )}
    </header>
  )
}

export default Header
