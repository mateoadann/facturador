import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

const API_URL = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
client.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = useAuthStore.getState().refreshToken

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, null, {
            headers: {
              Authorization: `Bearer ${refreshToken}`,
            },
          })

          const { access_token } = response.data
          useAuthStore.getState().setAccessToken(access_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return client(originalRequest)
        } catch (refreshError) {
          useAuthStore.getState().logout()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      } else {
        useAuthStore.getState().logout()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default client

// API functions
export const api = {
  // Auth
  auth: {
    login: (data) => client.post('/auth/login', data),
    refresh: () => client.post('/auth/refresh'),
    me: () => client.get('/auth/me'),
    logout: () => client.post('/auth/logout'),
    changePassword: (data) => client.post('/auth/change-password', data),
  },

  // Dashboard
  dashboard: {
    getStats: () => client.get('/dashboard/stats'),
  },

  // Facturadores
  facturadores: {
    list: (params) => client.get('/facturadores', { params }),
    get: (id) => client.get(`/facturadores/${id}`),
    create: (data) => client.post('/facturadores', data),
    update: (id, data) => client.put(`/facturadores/${id}`, data),
    delete: (id) => client.delete(`/facturadores/${id}`),
    uploadCerts: (id, formData) =>
      client.post(`/facturadores/${id}/certificados`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    testConnection: (id) => client.post(`/facturadores/${id}/test-conexion`),
    consultarCuit: (cuit) => client.post('/facturadores/consultar-cuit', { cuit }),
  },

  // Receptores
  receptores: {
    list: (params) => client.get('/receptores', { params }),
    get: (id) => client.get(`/receptores/${id}`),
    create: (data) => client.post('/receptores', data),
    update: (id, data) => client.put(`/receptores/${id}`, data),
    delete: (id) => client.delete(`/receptores/${id}`),
    import: (formData) =>
      client.post('/receptores/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    consultarCuit: (cuit) => client.post('/receptores/consultar-cuit', { cuit }),
  },

  // Facturas
  facturas: {
    list: (params) => client.get('/facturas', { params }),
    get: (id) => client.get(`/facturas/${id}`),
    update: (id, data) => client.put(`/facturas/${id}`, data),
    getItems: (id) => client.get(`/facturas/${id}/items`),
    getComprobanteHtml: (id, params) => client.get(`/facturas/${id}/comprobante-html`, { params }),
    getComprobantePdf: (id, params) =>
      client.get(`/facturas/${id}/comprobante-pdf`, {
        responseType: 'blob',
        params,
      }),
    import: (formData) =>
      client.post('/facturas/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    bulkDelete: (ids) => client.delete('/facturas', { data: { ids } }),
    sendEmail: (id) => client.post(`/facturas/${id}/enviar-email`),
  },

  // Lotes
  lotes: {
    list: (params) => client.get('/lotes', { params }),
    get: (id) => client.get(`/lotes/${id}`),
    facturar: (id, data) => client.post(`/lotes/${id}/facturar`, data),
    sendEmails: (id, data) => client.post(`/lotes/${id}/enviar-emails`, data),
    emailPreview: (id) => client.get(`/lotes/${id}/email-preview`),
    comprobantesZipPreview: (id) => client.get(`/lotes/${id}/comprobantes-zip-preview`),
    generarComprobantesZip: (id) => client.post(`/lotes/${id}/comprobantes-zip`),
    delete: (id) => client.delete(`/lotes/${id}`),
  },

  downloads: {
    getByTask: (taskId) => client.get(`/downloads/${taskId}`, { responseType: 'blob' }),
  },

  // Jobs
  jobs: {
    getStatus: (taskId) => client.get(`/jobs/${taskId}/status`),
  },

  // Comprobantes
  comprobantes: {
    consultar: (data) => client.post('/comprobantes/consultar', data),
    ultimoAutorizado: (data) => client.post('/comprobantes/ultimo-autorizado', data),
  },

  // Usuarios
  usuarios: {
    list: (params) => client.get('/usuarios', { params }),
    create: (data) => client.post('/usuarios', data),
    update: (id, data) => client.put(`/usuarios/${id}`, data),
    toggleActive: (id) => client.post(`/usuarios/${id}/toggle-active`),
    roles: () => client.get('/usuarios/roles'),
  },

  // Auditoría
  audit: {
    list: (params) => client.get('/audit', { params }),
  },

  // Email
  email: {
    getConfig: () => client.get('/email/config'),
    updateConfig: (data) => client.put('/email/config', data),
    testConnection: () => client.post('/email/test'),
    testSend: (data) => client.post('/email/test-send', data),
    preview: (data) => client.post('/email/preview', data),
  },

  // Ayuda
  help: {
    getImportCsvGuide: () => client.get('/help/guia-importacion-csv', { responseType: 'text' }),
  },
}
