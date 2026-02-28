import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
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
  return (
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
  )
}

export default App
