import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export function useLogin() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)

  return useMutation({
    mutationFn: (credentials) => api.auth.login(credentials),
    onSuccess: (response) => {
      setAuth(response.data)
      navigate('/dashboard')
    },
  })
}

export function useLogout() {
  const navigate = useNavigate()
  const logout = useAuthStore((state) => state.logout)

  return useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      logout()
      navigate('/login')
    },
    onError: () => {
      // Even if the API call fails, logout locally
      logout()
      navigate('/login')
    },
  })
}

export function useCurrentUser() {
  const { user, tenant } = useAuthStore()

  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const response = await api.auth.me()
      return response.data
    },
    initialData: user && tenant ? { user, tenant } : undefined,
    enabled: !!useAuthStore.getState().accessToken,
  })
}
