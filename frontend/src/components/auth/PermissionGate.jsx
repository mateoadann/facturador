import { usePermission, useAnyPermission } from '@/hooks/usePermission'

export function PermissionGate({ permission, anyOf, children, fallback = null }) {
  const hasSingle = usePermission(permission || '')
  const hasAny = useAnyPermission(...(anyOf || []))

  const hasAccess = permission ? hasSingle : hasAny

  if (!hasAccess) return fallback
  return children
}
