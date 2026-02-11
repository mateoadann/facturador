import { useState } from 'react'
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
  UserCog,
  ClipboardList,
  KeyRound,
  Mail,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useSidebarStore } from '@/stores/sidebarStore'
import { useAuthStore } from '@/stores/authStore'
import { useLogout } from '@/hooks/useAuth'
import ChangePasswordModal from '@/components/auth/ChangePasswordModal'

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard', permission: 'dashboard:ver' },
  {
    group: 'FACTURACIÓN',
    items: [
      { icon: FileText, label: 'Facturar', href: '/facturar', permission: 'facturar:importar' },
      { icon: Files, label: 'Ver Facturas', href: '/facturas', permission: 'facturas:ver' },
      { icon: FileX, label: 'Notas de Crédito', href: '/notas-credito', permission: 'facturar:importar' },
      { icon: Search, label: 'Consultar Comprobantes', href: '/consultar-comprobantes', permission: 'comprobantes:consultar' },
    ],
  },
  {
    group: 'CONFIGURACIÓN',
    items: [
      { icon: Building2, label: 'Facturadores', href: '/facturadores', permission: 'facturadores:ver' },
      { icon: Users, label: 'Receptores', href: '/receptores', permission: 'receptores:ver' },
      { icon: Mail, label: 'Email', href: '/email', permission: 'email:configurar' },
    ],
  },
  {
    group: 'ADMINISTRACIÓN',
    items: [
      { icon: UserCog, label: 'Usuarios', href: '/usuarios', permission: 'usuarios:ver' },
      { icon: ClipboardList, label: 'Auditoría', href: '/auditoria', permission: 'auditoria:ver' },
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
  const permisos = user?.permisos || []
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false)

  const filteredNavItems = navItems
    .map((item) => {
      if ('group' in item) {
        const filteredItems = item.items.filter(
          (sub) => !sub.permission || permisos.includes(sub.permission)
        )
        return filteredItems.length > 0 ? { ...item, items: filteredItems } : null
      }
      return !item.permission || permisos.includes(item.permission) ? item : null
    })
    .filter(Boolean)

  return (
    <aside
      className={cn(
        'relative flex h-screen flex-col border-r border-border bg-sidebar transition-all duration-300',
        isCollapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      {/* Top */}
      <div className="flex-1 overflow-y-auto p-4">
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
            <>
              <span className="flex-1 font-semibold text-text-primary">Facturador</span>
              <button
                onClick={toggle}
                className="rounded-md p-1 text-text-secondary hover:bg-secondary"
                title="Colapsar sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
            </>
          )}
          {isCollapsed && (
            <button
              onClick={toggle}
              className="absolute right-0 top-5 translate-x-1/2 rounded-full border border-border bg-sidebar p-1 text-text-secondary hover:bg-secondary"
              title="Expandir sidebar"
            >
              <ChevronRight className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="mt-4 space-y-1">
          {filteredNavItems.map((item) => {
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
      <div className="flex-shrink-0 border-t border-border p-4">
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
            onClick={() => setIsPasswordModalOpen(true)}
            className={cn(
              'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-secondary hover:bg-secondary',
              isCollapsed && 'justify-center px-0'
            )}
            title="Cambiar contraseña"
          >
            <KeyRound className="h-5 w-5" />
            {!isCollapsed && <span>Cambiar contraseña</span>}
          </button>
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
        </div>
      </div>
      <ChangePasswordModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </aside>
  )
}

export default Sidebar
