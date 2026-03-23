import { useEffect, Component } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useThemeStore } from './stores/themeStore'
import Layout from './components/layout/Layout'
import ToastContainer from './components/ui/Toast'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Facturar from './pages/facturar'
import Facturas from './pages/facturas'
import Facturadores from './pages/facturadores'
import Receptores from './pages/receptores'
import NotasCredito from './pages/notas-credito'
import ConsultarComprobantes from './pages/consultar-comprobantes'
import Usuarios from './pages/usuarios'
import Auditoria from './pages/auditoria'
import Email from './pages/email'
import Ayuda from './pages/ayuda'
import ZipDownloadsWatcher from './components/downloads/ZipDownloadsWatcher'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-secondary/40">
          <div className="text-center">
            <h1 className="text-xl font-semibold text-text-primary">
              Algo salió mal
            </h1>
            <p className="mt-2 text-text-secondary">
              {this.state.error?.message || 'Error inesperado'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-md bg-primary px-4 py-2 text-sm text-white"
            >
              Recargar página
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function PrivateRoute({ children }) {
  const accessToken = useAuthStore((s) => s.accessToken)

  if (!accessToken) {
    return <Navigate to="/login" replace />
  }

  return children
}

function ProtectedRoute({ permission, children }) {
  const hasAccess = useAuthStore((s) =>
    s.user?.permisos?.includes(permission) ?? false
  )

  if (!hasAccess) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

function App() {
  const darkMode = useThemeStore((s) => s.darkMode)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastContainer />
        <ZipDownloadsWatcher />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="facturar" element={
              <ProtectedRoute permission="facturar:importar"><Facturar /></ProtectedRoute>
            } />
            <Route path="facturas" element={
              <ProtectedRoute permission="facturas:ver"><Facturas /></ProtectedRoute>
            } />
            <Route path="facturadores" element={
              <ProtectedRoute permission="facturadores:ver"><Facturadores /></ProtectedRoute>
            } />
            <Route path="receptores" element={
              <ProtectedRoute permission="receptores:ver"><Receptores /></ProtectedRoute>
            } />
            <Route path="notas-credito" element={
              <ProtectedRoute permission="facturar:importar"><NotasCredito /></ProtectedRoute>
            } />
            <Route path="consultar-comprobantes" element={
              <ProtectedRoute permission="comprobantes:consultar"><ConsultarComprobantes /></ProtectedRoute>
            } />
            <Route path="usuarios" element={
              <ProtectedRoute permission="usuarios:ver"><Usuarios /></ProtectedRoute>
            } />
            <Route path="auditoria" element={
              <ProtectedRoute permission="auditoria:ver"><Auditoria /></ProtectedRoute>
            } />
            <Route path="email" element={
              <ProtectedRoute permission="email:configurar"><Email /></ProtectedRoute>
            } />
            <Route path="ayuda" element={
              <ProtectedRoute permission="dashboard:ver"><Ayuda /></ProtectedRoute>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
