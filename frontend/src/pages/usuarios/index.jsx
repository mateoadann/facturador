import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Power } from 'lucide-react'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import { useAuthStore } from '@/stores/authStore'
import {
  Button,
  Badge,
  Checkbox,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Modal,
  Input,
  Select,
} from '@/components/ui'

const rolLabels = {
  admin: 'Administrador',
  operator: 'Operador',
  viewer: 'Solo lectura',
}

const rolVariants = {
  admin: 'primary',
  operator: 'warning',
  viewer: 'default',
}

function Usuarios() {
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((s) => s.user)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    rol: 'operator',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['usuarios'],
    queryFn: async () => {
      const response = await api.usuarios.list({ per_page: 100 })
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data) => api.usuarios.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['usuarios'])
      handleCloseModal()
      toast.success('Usuario creado correctamente')
    },
    onError: (error) => {
      toast.error('Error al crear', error.response?.data?.error || 'No se pudo crear el usuario')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.usuarios.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['usuarios'])
      handleCloseModal()
      toast.success('Usuario actualizado correctamente')
    },
    onError: (error) => {
      toast.error('Error al actualizar', error.response?.data?.error || 'No se pudo actualizar')
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: (id) => api.usuarios.toggleActive(id),
    onSuccess: (response) => {
      queryClient.invalidateQueries(['usuarios'])
      const user = response.data
      toast.success(user.activo ? 'Usuario activado' : 'Usuario desactivado')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo cambiar el estado')
    },
  })

  const toggleDashboardRestrictionMutation = useMutation({
    mutationFn: ({ id, restringir_dashboard_sensible }) =>
      api.usuarios.update(id, { restringir_dashboard_sensible }),
    onSuccess: (response) => {
      queryClient.invalidateQueries(['usuarios'])
      queryClient.invalidateQueries(['dashboard-stats'])
      toast.success(
        response.data?.restringir_dashboard_sensible
          ? 'Restricción individual activada'
          : 'Restricción individual desactivada'
      )
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo actualizar la restricción')
    },
  })

  const usuarios = data?.items || []

  const handleOpenModal = (user = null) => {
    if (user) {
      setEditingUser(user)
      setFormData({
        nombre: user.nombre || '',
        email: user.email,
        password: '',
        rol: user.rol,
      })
    } else {
      setEditingUser(null)
      setFormData({
        nombre: '',
        email: '',
        password: '',
        rol: 'operator',
      })
    }
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingUser(null)
  }

  const handleSubmit = () => {
    const payload = { ...formData }

    if (editingUser) {
      if (!payload.password) delete payload.password
      updateMutation.mutate({ id: editingUser.id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button icon={Plus} onClick={() => handleOpenModal()}>
          Nuevo Usuario
        </Button>
      </div>

      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Rol</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Dashboard sensible</TableHead>
              <TableHead>Último Login</TableHead>
              <TableHead className="w-24">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : usuarios.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-text-muted">
                  No hay usuarios
                </TableCell>
              </TableRow>
            ) : (
              usuarios.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">
                    {user.nombre || '-'}
                    {user.id === currentUser?.id && (
                      <span className="ml-2 text-xs text-text-muted">(vos)</span>
                    )}
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Badge variant={rolVariants[user.rol] || 'default'}>
                      {rolLabels[user.rol] || user.rol}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.activo ? 'success' : 'default'}>
                      {user.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {user.rol === 'admin' ? (
                      <span className="text-sm text-text-muted">No aplica</span>
                    ) : (
                      <Checkbox
                        checked={!!user.restringir_dashboard_sensible}
                        disabled={toggleDashboardRestrictionMutation.isPending}
                        onChange={(checked) => {
                          toggleDashboardRestrictionMutation.mutate({
                            id: user.id,
                            restringir_dashboard_sensible: checked,
                          })
                        }}
                        label="Restringir"
                      />
                    )}
                  </TableCell>
                  <TableCell className="text-text-muted text-sm">
                    {formatDate(user.ultimo_login)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                        onClick={() => handleOpenModal(user)}
                        title="Editar"
                      >
                        <Edit className="h-4 w-4 text-text-secondary" />
                      </button>
                      {user.id !== currentUser?.id && (
                        <button
                          className={`flex h-8 w-8 items-center justify-center rounded-md ${
                            user.activo ? 'hover:bg-error-light' : 'hover:bg-success/10'
                          }`}
                          onClick={() => {
                            const action = user.activo ? 'desactivar' : 'activar'
                            if (confirm(`¿Estás seguro de ${action} a ${user.nombre || user.email}?`)) {
                              toggleActiveMutation.mutate(user.id)
                            }
                          }}
                          title={user.activo ? 'Desactivar' : 'Activar'}
                        >
                          <Power className={`h-4 w-4 ${user.activo ? 'text-error' : 'text-success'}`} />
                        </button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
        className="max-w-md"
        footer={
          <>
            <Button variant="secondary" onClick={handleCloseModal}>
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending
                ? 'Guardando...'
                : 'Guardar'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Nombre"
            placeholder="Nombre completo"
            value={formData.nombre}
            onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
          />

          <Input
            label="Email"
            type="email"
            placeholder="usuario@ejemplo.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            disabled={!!editingUser}
          />

          <Input
            label={editingUser ? 'Nueva Contraseña (dejar vacío para no cambiar)' : 'Contraseña'}
            type="password"
            placeholder={editingUser ? '••••••••' : 'Mínimo 8 caracteres'}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          />

          <Select
            label="Rol"
            value={formData.rol}
            onChange={(e) => setFormData({ ...formData, rol: e.target.value })}
            disabled={editingUser?.id === currentUser?.id}
          >
            <option value="admin">Administrador</option>
            <option value="operator">Operador</option>
            <option value="viewer">Solo lectura</option>
          </Select>

          {editingUser?.id === currentUser?.id && (
            <p className="text-xs text-text-muted">
              No podés cambiar tu propio rol
            </p>
          )}

          {(createMutation.error || updateMutation.error) && (
            <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
              {(createMutation.error || updateMutation.error).response?.data?.error ||
                'Error al guardar'}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default Usuarios
