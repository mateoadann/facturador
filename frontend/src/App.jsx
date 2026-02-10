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

function PrivateRoute({ children }) {
  const accessToken = useAuthStore((s) => s.accessToken)

  if (!accessToken) {
    return <Navigate to="/login" replace />
  }

  return children
}

function App() {
  return (
    <BrowserRouter>
      <ToastContainer />
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
          <Route path="facturar" element={<Facturar />} />
          <Route path="facturas" element={<Facturas />} />
          <Route path="facturadores" element={<Facturadores />} />
          <Route path="receptores" element={<Receptores />} />
          <Route path="notas-credito" element={<NotasCredito />} />
          <Route path="consultar-comprobantes" element={<ConsultarComprobantes />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
