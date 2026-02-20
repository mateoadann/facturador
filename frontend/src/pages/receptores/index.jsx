import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Search, Upload } from 'lucide-react'
import { api } from '@/api/client'
import {
  Button,
  Badge,
  Input,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Modal,
  Select,
} from '@/components/ui'
import { formatCUIT } from '@/lib/utils'
import { toast } from '@/stores/toastStore'
import ImportModal from './ImportModal'

function Receptores() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [editingReceptor, setEditingReceptor] = useState(null)
  const [formData, setFormData] = useState({
    doc_tipo: 80,
    doc_nro: '',
    razon_social: '',
    direccion: '',
    condicion_iva: '',
    email: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['receptores', search],
    queryFn: async () => {
      const response = await api.receptores.list({ search, per_page: 100 })
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data) => api.receptores.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['receptores'])
      handleCloseModal()
      toast.success('Receptor creado correctamente')
    },
    onError: (error) => {
      toast.error('Error al crear', error.response?.data?.error || 'No se pudo crear el receptor')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.receptores.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['receptores'])
      handleCloseModal()
      toast.success('Receptor actualizado correctamente')
    },
    onError: (error) => {
      toast.error('Error al actualizar', error.response?.data?.error || 'No se pudo actualizar')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.receptores.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['receptores'])
      toast.success('Receptor desactivado')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo desactivar')
    },
  })

  const receptores = data?.items || []

  const handleOpenModal = (receptor = null) => {
    if (receptor) {
      setEditingReceptor(receptor)
      setFormData({
        doc_tipo: receptor.doc_tipo,
        doc_nro: receptor.doc_nro,
        razon_social: receptor.razon_social,
        direccion: receptor.direccion || '',
        condicion_iva: receptor.condicion_iva || '',
        email: receptor.email || '',
      })
    } else {
      setEditingReceptor(null)
      setFormData({
        doc_tipo: 80,
        doc_nro: '',
        razon_social: '',
        direccion: '',
        condicion_iva: '',
        email: '',
      })
    }
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingReceptor(null)
  }

  const handleSubmit = () => {
    if (editingReceptor) {
      updateMutation.mutate({ id: editingReceptor.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleImportSuccess = () => {
    queryClient.invalidateQueries(['receptores'])
  }

  const handleConsultarCuit = async () => {
    if (!formData.doc_nro) return

    try {
      const response = await api.receptores.consultarCuit(formData.doc_nro)
      if (response.data.success && response.data.data) {
        const data = response.data.data
        setFormData({
          ...formData,
          razon_social: data.razon_social || formData.razon_social,
          direccion: data.direccion || formData.direccion,
          condicion_iva: data.condicion_iva || formData.condicion_iva,
        })
      }
    } catch (error) {
      console.error('Error al consultar CUIT:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Buscar por nombre o CUIT..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-10 w-full rounded-md border border-border bg-card pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" icon={Upload} onClick={() => setIsImportModalOpen(true)}>
            Importar CSV
          </Button>
          <Button icon={Plus} onClick={() => handleOpenModal()}>
            Nuevo Receptor
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>CUIT/CUIL</TableHead>
              <TableHead>Razón Social</TableHead>
              <TableHead>Condición IVA</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="w-24">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : receptores.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-text-muted">
                  {search ? 'No se encontraron receptores' : 'No hay receptores registrados'}
                </TableCell>
              </TableRow>
            ) : (
              receptores.map((receptor) => (
                <TableRow key={receptor.id}>
                  <TableCell className="font-mono">
                    {formatCUIT(receptor.doc_nro)}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{receptor.razon_social}</p>
                      {receptor.direccion && (
                        <p className="text-xs text-text-muted">{receptor.direccion}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{receptor.condicion_iva || '-'}</TableCell>
                  <TableCell>{receptor.email || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={receptor.activo ? 'success' : 'default'}>
                      {receptor.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                        onClick={() => handleOpenModal(receptor)}
                        title="Editar"
                      >
                        <Edit className="h-4 w-4 text-text-secondary" />
                      </button>
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-error-light"
                        onClick={() => {
                          if (confirm('¿Estás seguro de desactivar este receptor?')) {
                            deleteMutation.mutate(receptor.id)
                          }
                        }}
                        title="Desactivar"
                      >
                        <Trash2 className="h-4 w-4 text-error" />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingReceptor ? 'Editar Receptor' : 'Nuevo Receptor'}
        className="max-w-lg"
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
          <div className="flex items-end gap-3">
            <Input
              label="CUIT/CUIL"
              placeholder="20-12345678-9"
              value={formData.doc_nro}
              onChange={(e) => setFormData({ ...formData, doc_nro: e.target.value })}
              className="flex-1"
            />
            <Button variant="secondary" onClick={handleConsultarCuit}>
              Buscar
            </Button>
          </div>

          <Input
            label="Razón Social"
            placeholder="Nombre del cliente"
            value={formData.razon_social}
            onChange={(e) => setFormData({ ...formData, razon_social: e.target.value })}
          />

          <Input
            label="Dirección"
            placeholder="Calle 123, Ciudad"
            value={formData.direccion}
            onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
          />

          <Select
            label="Condición IVA"
            value={formData.condicion_iva}
            onChange={(e) => setFormData({ ...formData, condicion_iva: e.target.value })}
          >
            <option value="">Seleccionar...</option>
            <option value="IVA Responsable Inscripto">IVA Responsable Inscripto</option>
            <option value="Responsable Monotributo">Responsable Monotributo</option>
            <option value="Consumidor Final">Consumidor Final</option>
            <option value="IVA Sujeto Exento">IVA Sujeto Exento</option>
          </Select>

          <Input
            label="Email"
            type="email"
            placeholder="email@ejemplo.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />

          {(createMutation.error || updateMutation.error) && (
            <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
              {(createMutation.error || updateMutation.error).response?.data?.error ||
                'Error al guardar'}
            </div>
          )}
        </div>
      </Modal>

      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onSuccess={handleImportSuccess}
      />
    </div>
  )
}

export default Receptores
