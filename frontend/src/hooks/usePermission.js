import { useAuthStore } from '@/stores/authStore'

export function usePermission(permission) {
  return useAuthStore((s) => s.user?.permisos?.includes(permission) ?? false)
}

export function useAnyPermission(...permissions) {
  return useAuthStore((s) => {
    const permisos = s.user?.permisos || []
    return permissions.some((p) => permisos.includes(p))
  })
}

export function useIsAdmin() {
  return useAuthStore((s) => s.user?.rol === 'admin')
}
