import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
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
