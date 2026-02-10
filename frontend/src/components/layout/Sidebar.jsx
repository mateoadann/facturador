import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  Files,
  Building2,
  Users,
  FileX,
  Search,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSidebarStore } from '@/stores/sidebarStore'
import { useAuthStore } from '@/stores/authStore'
import { useLogout } from '@/hooks/useAuth'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  {
    group: 'FACTURACIÓN',
    items: [
      { icon: FileText, label: 'Facturar', href: '/facturar' },
      { icon: Files, label: 'Ver Facturas', href: '/facturas' },
      { icon: FileX, label: 'Notas de Crédito', href: '/notas-credito' },
      { icon: Search, label: 'Consultar Comprobantes', href: '/consultar-comprobantes' },
    ],
  },
  {
    group: 'CONFIGURACIÓN',
    items: [
      { icon: Building2, label: 'Facturadores', href: '/facturadores' },
      { icon: Users, label: 'Receptores', href: '/receptores' },
    ],
  },
]

function NavItem({ icon: Icon, label, href, isCollapsed }) {
  return (
    <NavLink
      to={href}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'text-text-secondary hover:bg-secondary'
        )
      }
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      {!isCollapsed && <span>{label}</span>}
    </NavLink>
  )
}

function Sidebar() {
  const { isCollapsed, toggle } = useSidebarStore()
  const { user, tenant } = useAuthStore()
  const { mutate: logout } = useLogout()

  return (
    <aside
      className={cn(
        'flex h-screen flex-col justify-between border-r border-border bg-sidebar transition-all duration-300',
        isCollapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      {/* Top */}
      <div className="p-4">
        {/* Logo */}
        <div
          className={cn(
            'flex h-12 items-center gap-3 px-3',
            isCollapsed && 'justify-center px-0'
          )}
        >
          <img
            src="/factura.png"
            alt="Facturador"
            className="h-10 w-10 rounded-lg object-cover"
          />
          {!isCollapsed && (
            <span className="font-semibold text-text-primary">Facturador</span>
          )}
        </div>

        {/* Navigation */}
        <nav className="mt-4 space-y-1">
          {navItems.map((item, index) => {
            if ('group' in item) {
              return (
                <div key={item.group} className="pt-4">
                  {!isCollapsed && (
                    <span className="px-3 text-[11px] font-semibold tracking-wider text-text-muted">
                      {item.group}
                    </span>
                  )}
                  <div className="mt-2 space-y-1">
                    {item.items.map((subItem) => (
                      <NavItem
                        key={subItem.href}
                        {...subItem}
                        isCollapsed={isCollapsed}
                      />
                    ))}
                  </div>
                </div>
              )
            }
            return (
              <NavItem key={item.href} {...item} isCollapsed={isCollapsed} />
            )
          })}
        </nav>
      </div>

      {/* Bottom */}
      <div className="border-t border-border p-4">
        {/* User */}
        {!isCollapsed && (
          <div className="mb-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary font-medium">
              {user?.nombre?.[0] || user?.email?.[0] || 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium text-text-primary">
                {user?.nombre || user?.email}
              </p>
              <p className="truncate text-xs text-text-muted">
                {tenant?.nombre}
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2">
          <button
            onClick={() => logout()}
            className={cn(
              'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-secondary',
              isCollapsed && 'justify-center px-0'
            )}
          >
            <LogOut className="h-5 w-5" />
            {!isCollapsed && <span>Cerrar sesión</span>}
          </button>
          <button
            onClick={toggle}
            className={cn(
              'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-secondary',
              isCollapsed && 'justify-center px-0'
            )}
          >
            {isCollapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <>
                <ChevronLeft className="h-5 w-5" />
                <span>Colapsar</span>
              </>
            )}
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
