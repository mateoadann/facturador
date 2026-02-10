import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Upload, Wifi, Power } from 'lucide-react'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import CertificadosModal from './CertificadosModal'
import {
  Button,
  Badge,
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
import { formatCUIT } from '@/lib/utils'

function Facturadores() {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFacturador, setEditingFacturador] = useState(null)
  const [certFacturador, setCertFacturador] = useState(null)
  const [formData, setFormData] = useState({
    cuit: '',
    razon_social: '',
    direccion: '',
    condicion_iva: '',
    punto_venta: '',
    ambiente: 'testing',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['facturadores'],
    queryFn: async () => {
      const response = await api.facturadores.list({ per_page: 100 })
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data) => api.facturadores.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['facturadores'])
      handleCloseModal()
      toast.success('Facturador creado correctamente')
    },
    onError: (error) => {
      toast.error('Error al crear', error.response?.data?.error || 'No se pudo crear el facturador')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.facturadores.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['facturadores'])
      handleCloseModal()
      toast.success('Facturador actualizado correctamente')
    },
    onError: (error) => {
      toast.error('Error al actualizar', error.response?.data?.error || 'No se pudo actualizar')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.facturadores.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['facturadores'])
      toast.success('Facturador desactivado')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo desactivar')
    },
  })

  const activateMutation = useMutation({
    mutationFn: (id) => api.facturadores.update(id, { activo: true }),
    onSuccess: () => {
      queryClient.invalidateQueries(['facturadores'])
      toast.success('Facturador activado')
    },
    onError: (error) => {
      toast.error('Error', error.response?.data?.error || 'No se pudo activar')
    },
  })

  const testConnectionMutation = useMutation({
    mutationFn: (id) => api.facturadores.testConnection(id),
    onSuccess: () => {
      toast.success('Conexión exitosa', 'El facturador se conectó correctamente a ARCA')
    },
    onError: (error) => {
      toast.error('Error de conexión', error.response?.data?.error || 'No se pudo conectar a ARCA')
    },
  })

  const facturadores = data?.items || []

  const handleOpenModal = (facturador = null) => {
    if (facturador) {
      setEditingFacturador(facturador)
      setFormData({
        cuit: facturador.cuit,
        razon_social: facturador.razon_social,
        direccion: facturador.direccion || '',
        condicion_iva: facturador.condicion_iva || '',
        punto_venta: facturador.punto_venta.toString(),
        ambiente: facturador.ambiente,
      })
    } else {
      setEditingFacturador(null)
      setFormData({
        cuit: '',
        razon_social: '',
        direccion: '',
        condicion_iva: '',
        punto_venta: '',
        ambiente: 'testing',
      })
    }
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setEditingFacturador(null)
  }

  const handleSubmit = () => {
    const data = {
      ...formData,
      punto_venta: parseInt(formData.punto_venta, 10),
    }

    if (editingFacturador) {
      updateMutation.mutate({ id: editingFacturador.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleConsultarCuit = async () => {
    if (!formData.cuit) return

    try {
      const response = await api.facturadores.consultarCuit(formData.cuit)
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
      <div className="flex justify-end">
        <Button icon={Plus} onClick={() => handleOpenModal()}>
          Nuevo Facturador
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>CUIT</TableHead>
              <TableHead>Razón Social</TableHead>
              <TableHead>Punto de Venta</TableHead>
              <TableHead>Ambiente</TableHead>
              <TableHead>Certificados</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="w-32">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center">
                  Cargando...
                </TableCell>
              </TableRow>
            ) : facturadores.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-text-muted">
                  No hay facturadores configurados
                </TableCell>
              </TableRow>
            ) : (
              facturadores.map((facturador) => (
                <TableRow key={facturador.id}>
                  <TableCell className="font-mono">
                    {formatCUIT(facturador.cuit)}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{facturador.razon_social}</p>
                      <p className="text-xs text-text-muted">{facturador.condicion_iva}</p>
                    </div>
                  </TableCell>
                  <TableCell>{facturador.punto_venta}</TableCell>
                  <TableCell>
                    <Badge variant={facturador.ambiente === 'production' ? 'success' : 'warning'}>
                      {facturador.ambiente === 'production' ? 'Producción' : 'Testing'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {facturador.tiene_certificados ? (
                      <Badge variant="success">Cargados</Badge>
                    ) : (
                      <Badge variant="error">Sin certificados</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={facturador.activo ? 'success' : 'default'}>
                      {facturador.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                        onClick={() => handleOpenModal(facturador)}
                        title="Editar"
                      >
                        <Edit className="h-4 w-4 text-text-secondary" />
                      </button>
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                        onClick={() => setCertFacturador(facturador)}
                        title="Cargar certificados"
                      >
                        <Upload className="h-4 w-4 text-text-secondary" />
                      </button>
                      <button
                        className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
                        onClick={() => testConnectionMutation.mutate(facturador.id)}
                        title="Probar conexión"
                        disabled={!facturador.tiene_certificados}
                      >
                        {testConnectionMutation.isPending ? (
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        ) : (
                          <Wifi className="h-4 w-4 text-text-secondary" />
                        )}
                      </button>
                      {facturador.activo ? (
                        <button
                          className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-error-light"
                          onClick={() => {
                            if (confirm('¿Estás seguro de desactivar este facturador?')) {
                              deleteMutation.mutate(facturador.id)
                            }
                          }}
                          title="Desactivar"
                        >
                          <Trash2 className="h-4 w-4 text-error" />
                        </button>
                      ) : (
                        <button
                          className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-success/10"
                          onClick={() => activateMutation.mutate(facturador.id)}
                          title="Activar"
                        >
                          <Power className="h-4 w-4 text-success" />
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

      {/* Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingFacturador ? 'Editar Facturador' : 'Nuevo Facturador'}
        className="max-w-xl"
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
          {/* CUIT with search */}
          <div className="flex items-end gap-3">
            <Input
              label="CUIT"
              placeholder="20-12345678-9"
              value={formData.cuit}
              onChange={(e) => setFormData({ ...formData, cuit: e.target.value })}
              className="flex-1"
              disabled={!!editingFacturador}
            />
            {!editingFacturador && (
              <Button variant="secondary" onClick={handleConsultarCuit}>
                Buscar
              </Button>
            )}
          </div>
          <p className="text-xs text-text-muted">
            El botón busca en ARCA y autocompleta los campos
          </p>

          <Input
            label="Razón Social"
            placeholder="Nombre de la empresa"
            value={formData.razon_social}
            onChange={(e) => setFormData({ ...formData, razon_social: e.target.value })}
          />

          <Input
            label="Dirección"
            placeholder="Calle 123, Ciudad"
            value={formData.direccion}
            onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Condición IVA"
              value={formData.condicion_iva}
              onChange={(e) => setFormData({ ...formData, condicion_iva: e.target.value })}
            >
              <option value="">Seleccionar...</option>
              <option value="IVA Responsable Inscripto">IVA Responsable Inscripto</option>
              <option value="Responsable Monotributo">Responsable Monotributo</option>
              <option value="IVA Exento">IVA Exento</option>
            </Select>

            <Input
              label="Punto de Venta"
              type="number"
              placeholder="1"
              value={formData.punto_venta}
              onChange={(e) => setFormData({ ...formData, punto_venta: e.target.value })}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-text-primary">
              Ambiente
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="ambiente"
                  value="testing"
                  checked={formData.ambiente === 'testing'}
                  onChange={(e) => setFormData({ ...formData, ambiente: e.target.value })}
                  className="h-4 w-4 text-primary"
                />
                <span className="text-sm">Testing (Homologación)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="ambiente"
                  value="production"
                  checked={formData.ambiente === 'production'}
                  onChange={(e) => setFormData({ ...formData, ambiente: e.target.value })}
                  className="h-4 w-4 text-primary"
                />
                <span className="text-sm">Producción</span>
              </label>
            </div>
          </div>

          {(createMutation.error || updateMutation.error) && (
            <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
              {(createMutation.error || updateMutation.error).response?.data?.error ||
                'Error al guardar'}
            </div>
          )}
        </div>
      </Modal>

      {/* Modal Certificados */}
      <CertificadosModal
        facturador={certFacturador}
        isOpen={!!certFacturador}
        onClose={() => setCertFacturador(null)}
      />
    </div>
  )
}

export default Facturadores
