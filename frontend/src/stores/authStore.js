import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      tenant: null,
      accessToken: null,
      refreshToken: null,

      setAuth: ({ user, tenant, access_token, refresh_token }) => {
        set({
          user,
          tenant,
          accessToken: access_token,
          refreshToken: refresh_token,
        })
      },

      setAccessToken: (token) => {
        set({ accessToken: token })
      },

      hasPermission: (permission) => {
        const user = get().user
        if (!user || !user.permisos) return false
        return user.permisos.includes(permission)
      },

      hasAnyPermission: (...permissions) => {
        const user = get().user
        if (!user || !user.permisos) return false
        return permissions.some((p) => user.permisos.includes(p))
      },

      logout: () => {
        set({
          user: null,
          tenant: null,
          accessToken: null,
          refreshToken: null,
        })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        tenant: state.tenant,
      }),
    }
  )
)
