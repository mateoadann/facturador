import { useLocation } from 'react-router-dom'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/facturar': 'Facturar',
  '/facturas': 'Ver Facturas',
  '/facturadores': 'Facturadores',
  '/receptores': 'Receptores',
  '/notas-credito': 'Notas de Crédito',
  '/consultar-comprobantes': 'Consultar Comprobantes',
}

function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'Facturador'

  return (
    <header className="flex h-16 items-center border-b border-border bg-card px-6">
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
    </header>
  )
}

export default Header
