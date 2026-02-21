import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/ui'
import { formatCUIT, formatComprobante } from '@/lib/utils'
import { usePermission } from '@/hooks/usePermission'
import { toast } from '@/stores/toastStore'

const TIPOS_NOTA = new Set([2, 3, 7, 8, 12, 13, 52, 53])

const TIPO_COMPROBANTE_OPTIONS = [
  { value: 1, label: 'Factura A' },
  { value: 6, label: 'Factura B' },
  { value: 11, label: 'Factura C' },
  { value: 51, label: 'Factura M' },
  { value: 2, label: 'Nota Débito A' },
  { value: 3, label: 'Nota Crédito A' },
  { value: 7, label: 'Nota Débito B' },
  { value: 8, label: 'Nota Crédito B' },
  { value: 12, label: 'Nota Débito C' },
  { value: 13, label: 'Nota Crédito C' },
  { value: 52, label: 'Nota Débito M' },
  { value: 53, label: 'Nota Crédito M' },
]

const CONCEPTO_OPTIONS = [
  { value: 1, label: 'Productos' },
  { value: 2, label: 'Servicios' },
  { value: 3, label: 'Productos y Servicios' },
]

const ALICUOTA_OPTIONS = [
  { value: 3, label: '0%' },
  { value: 4, label: '10.5%' },
  { value: 5, label: '21%' },
  { value: 6, label: '27%' },
  { value: 8, label: '5%' },
  { value: 9, label: '2.5%' },
]

const EMPTY_ITEM = {
  descripcion: '',
  cantidad: '1',
  precio_unitario: '0',
  alicuota_iva_id: 5,
}

function ItemsModal({ factura, onClose, onSaved }) {
  const canEdit = usePermission('facturas:editar')
  const canImport = usePermission('facturar:importar')
  const normalizedEstado = (factura?.estado || '').trim().toLowerCase()
  const isEditableEstado = ['pendiente', 'borrador', 'error'].includes(normalizedEstado)
  const canSave = !!factura && isEditableEstado && (canEdit || canImport)

  const [formData, setFormData] = useState(null)
  const [formError, setFormError] = useState('')

  const { data: items, isLoading: isLoadingItems } = useQuery({
    queryKey: ['factura-items', factura?.id],
    queryFn: async () => {
      const response = await api.facturas.getItems(factura.id)
      return response.data.items
    },
    enabled: !!factura?.id,
  })

  const { data: receptoresData } = useQuery({
    queryKey: ['receptores', 'edit-factura'],
    queryFn: async () => {
      const response = await api.receptores.list({ per_page: 200, activo: true })
      return response.data.items || []
    },
    enabled: !!factura,
  })

  useEffect(() => {
    if (!factura) {
      setFormData(null)
      setFormError('')
      return
    }

    setFormData({
      receptor_id: factura.receptor_id || '',
      tipo_comprobante: factura.tipo_comprobante,
      concepto: factura.concepto,
      fecha_emision: factura.fecha_emision || '',
      fecha_desde: factura.fecha_desde || '',
      fecha_hasta: factura.fecha_hasta || '',
      fecha_vto_pago: factura.fecha_vto_pago || '',
      importe_total: String(factura.importe_total ?? 0),
      importe_neto: String(factura.importe_neto ?? 0),
      importe_iva: String(factura.importe_iva ?? 0),
      moneda: factura.moneda || 'PES',
      cotizacion: String(factura.cotizacion ?? 1),
      cbte_asoc_tipo: factura.cbte_asoc_tipo ? String(factura.cbte_asoc_tipo) : '',
      cbte_asoc_pto_vta: factura.cbte_asoc_pto_vta ? String(factura.cbte_asoc_pto_vta) : '',
      cbte_asoc_nro: factura.cbte_asoc_nro ? String(factura.cbte_asoc_nro) : '',
      items: [],
    })
    setFormError('')
  }, [factura])

  useEffect(() => {
    if (isLoadingItems) return
    const mappedItems = (items || []).map((item) => ({
      descripcion: item.descripcion || '',
      cantidad: String(item.cantidad ?? 0),
      precio_unitario: String(item.precio_unitario ?? 0),
      alicuota_iva_id: Number(item.alicuota_iva_id || 5),
    }))
    setFormData((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        items: mappedItems.length > 0 ? mappedItems : [{ ...EMPTY_ITEM }],
      }
    })
  }, [items, isLoadingItems])

  const saveMutation = useMutation({
    mutationFn: (payload) => api.facturas.update(factura.id, payload),
    onSuccess: (response) => {
      toast.success('Factura actualizada correctamente')
      onSaved?.(response.data)
    },
    onError: (error) => {
      setFormError(error.response?.data?.error || 'No se pudo actualizar la factura')
    },
  })

  const selectedReceptor = useMemo(() => {
    const receptores = receptoresData || []
    return receptores.find((r) => r.id === formData?.receptor_id)
  }, [receptoresData, formData?.receptor_id])

  if (!factura || !formData) return null

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const updateItemField = (index, field, value) => {
    setFormData((prev) => {
      const nextItems = [...prev.items]
      nextItems[index] = { ...nextItems[index], [field]: value }
      return { ...prev, items: nextItems }
    })
  }

  const addItem = () => {
    setFormData((prev) => ({ ...prev, items: [...prev.items, { ...EMPTY_ITEM }] }))
  }

  const removeItem = (index) => {
    setFormData((prev) => {
      const nextItems = prev.items.filter((_, idx) => idx !== index)
      return { ...prev, items: nextItems.length > 0 ? nextItems : [{ ...EMPTY_ITEM }] }
    })
  }

  const validate = () => {
    if (!formData.receptor_id) return 'Seleccioná un receptor'
    if (!formData.tipo_comprobante) return 'Tipo de comprobante requerido'
    if (!formData.concepto) return 'Concepto requerido'
    if (!formData.fecha_emision) return 'Fecha de emisión requerida'
    if (!formData.moneda) return 'Moneda requerida'

    const concepto = Number(formData.concepto)
    if (concepto === 2 || concepto === 3) {
      if (!formData.fecha_desde || !formData.fecha_hasta || !formData.fecha_vto_pago) {
        return 'Para concepto 2 o 3 se requieren fecha_desde, fecha_hasta y fecha_vto_pago'
      }
    }

    const tipoComprobante = Number(formData.tipo_comprobante)
    if (TIPOS_NOTA.has(tipoComprobante)) {
      if (!formData.cbte_asoc_tipo || !formData.cbte_asoc_pto_vta || !formData.cbte_asoc_nro) {
        return 'Para notas se requiere comprobante asociado completo'
      }
    }

    const total = Number(formData.importe_total)
    const neto = Number(formData.importe_neto)
    const iva = Number(formData.importe_iva)
    const cotizacion = Number(formData.cotizacion)
    if ([total, neto, iva, cotizacion].some((v) => Number.isNaN(v))) return 'Importes inválidos'
    if (total < 0 || neto < 0 || iva < 0 || cotizacion < 0) return 'Los importes deben ser mayores o iguales a 0'
    if (total < neto) return 'importe_total debe ser mayor o igual a importe_neto'

    for (let i = 0; i < formData.items.length; i += 1) {
      const item = formData.items[i]
      if (!item.descripcion?.trim()) return `Item ${i + 1}: descripción requerida`
      const cantidad = Number(item.cantidad)
      const precio = Number(item.precio_unitario)
      if (Number.isNaN(cantidad) || Number.isNaN(precio)) return `Item ${i + 1}: cantidad/precio inválidos`
      if (cantidad <= 0) return `Item ${i + 1}: cantidad debe ser mayor a 0`
      if (precio < 0) return `Item ${i + 1}: precio unitario debe ser mayor o igual a 0`
    }

    return ''
  }

  const handleSave = () => {
    const validationError = validate()
    if (validationError) {
      setFormError(validationError)
      return
    }

    setFormError('')

    const payload = {
      receptor_id: formData.receptor_id,
      tipo_comprobante: Number(formData.tipo_comprobante),
      concepto: Number(formData.concepto),
      fecha_emision: formData.fecha_emision,
      fecha_desde: formData.fecha_desde || null,
      fecha_hasta: formData.fecha_hasta || null,
      fecha_vto_pago: formData.fecha_vto_pago || null,
      importe_total: Number(formData.importe_total),
      importe_neto: Number(formData.importe_neto),
      importe_iva: Number(formData.importe_iva || 0),
      moneda: formData.moneda,
      cotizacion: Number(formData.cotizacion || 1),
      cbte_asoc_tipo: formData.cbte_asoc_tipo ? Number(formData.cbte_asoc_tipo) : null,
      cbte_asoc_pto_vta: formData.cbte_asoc_pto_vta ? Number(formData.cbte_asoc_pto_vta) : null,
      cbte_asoc_nro: formData.cbte_asoc_nro ? Number(formData.cbte_asoc_nro) : null,
      items: formData.items.map((item) => ({
        descripcion: item.descripcion.trim(),
        cantidad: Number(item.cantidad),
        precio_unitario: Number(item.precio_unitario),
        alicuota_iva_id: Number(item.alicuota_iva_id || 5),
      })),
    }

    saveMutation.mutate(payload)
  }

  return (
    <Modal
      isOpen={!!factura}
      onClose={onClose}
      title="Detalle de Factura"
      className="max-w-4xl"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          {canSave && (
            <Button onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Guardando...' : 'Guardar cambios'}
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-4">
        <div className="rounded-md bg-secondary/50 p-4">
          <p className="font-medium text-text-primary">
            Factura: {formatComprobante(factura.tipo_comprobante, factura.punto_venta, factura.numero_comprobante || 0)}
          </p>
          <p className="text-sm text-text-secondary">
            Estado actual: {factura.estado}
          </p>
          {selectedReceptor && (
            <p className="text-sm text-text-secondary">
              Receptor seleccionado: {selectedReceptor.razon_social} ({formatCUIT(selectedReceptor.doc_nro)})
            </p>
          )}
        </div>

        {!canSave && (
          <div className="rounded-md bg-warning-light p-3 text-sm text-warning-foreground">
            Esta factura está en modo solo lectura (sin permiso o estado no editable).
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Select label="Receptor" value={formData.receptor_id} onChange={(e) => updateField('receptor_id', e.target.value)} disabled={!canSave}>
            <option value="">Seleccionar...</option>
            {(receptoresData || []).map((receptor) => (
              <option key={receptor.id} value={receptor.id}>
                {receptor.razon_social} ({formatCUIT(receptor.doc_nro)})
              </option>
            ))}
          </Select>
          <Select label="Tipo comprobante" value={String(formData.tipo_comprobante)} onChange={(e) => updateField('tipo_comprobante', e.target.value)} disabled={!canSave}>
            {TIPO_COMPROBANTE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
          <Select label="Concepto" value={String(formData.concepto)} onChange={(e) => updateField('concepto', e.target.value)} disabled={!canSave}>
            {CONCEPTO_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <Input label="Fecha emisión" type="date" value={formData.fecha_emision} onChange={(e) => updateField('fecha_emision', e.target.value)} disabled={!canSave} />
          <Input label="Fecha desde" type="date" value={formData.fecha_desde} onChange={(e) => updateField('fecha_desde', e.target.value)} disabled={!canSave} />
          <Input label="Fecha hasta" type="date" value={formData.fecha_hasta} onChange={(e) => updateField('fecha_hasta', e.target.value)} disabled={!canSave} />
          <Input label="Vto pago" type="date" value={formData.fecha_vto_pago} onChange={(e) => updateField('fecha_vto_pago', e.target.value)} disabled={!canSave} />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <Input label="Importe total" type="number" step="0.01" value={formData.importe_total} onChange={(e) => updateField('importe_total', e.target.value)} disabled={!canSave} />
          <Input label="Importe neto" type="number" step="0.01" value={formData.importe_neto} onChange={(e) => updateField('importe_neto', e.target.value)} disabled={!canSave} />
          <Input label="IVA" type="number" step="0.01" value={formData.importe_iva} onChange={(e) => updateField('importe_iva', e.target.value)} disabled={!canSave} />
          <Input label="Cotización" type="number" step="0.000001" value={formData.cotizacion} onChange={(e) => updateField('cotizacion', e.target.value)} disabled={!canSave} />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <Input label="Moneda" value={formData.moneda} onChange={(e) => updateField('moneda', e.target.value)} disabled={!canSave} />
          <Input label="Cbte asoc tipo" type="number" value={formData.cbte_asoc_tipo} onChange={(e) => updateField('cbte_asoc_tipo', e.target.value)} disabled={!canSave} />
          <Input label="Cbte asoc pto vta" type="number" value={formData.cbte_asoc_pto_vta} onChange={(e) => updateField('cbte_asoc_pto_vta', e.target.value)} disabled={!canSave} />
          <Input label="Cbte asoc nro" type="number" value={formData.cbte_asoc_nro} onChange={(e) => updateField('cbte_asoc_nro', e.target.value)} disabled={!canSave} />
        </div>

        <div className="rounded-md border border-border">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <p className="text-sm font-medium text-text-primary">Items</p>
            {canSave && (
              <Button size="sm" variant="secondary" icon={Plus} onClick={addItem}>
                Agregar
              </Button>
            )}
          </div>
          <div className="space-y-3 p-3">
            {isLoadingItems ? (
              <p className="text-sm text-text-muted">Cargando items...</p>
            ) : (
              formData.items.map((item, idx) => (
                <div key={`${idx}-${item.descripcion}`} className="grid grid-cols-1 gap-2 rounded-md border border-border p-2 md:grid-cols-12">
                  <div className="md:col-span-5">
                    <Input
                      label={`Descripción #${idx + 1}`}
                      value={item.descripcion}
                      onChange={(e) => updateItemField(idx, 'descripcion', e.target.value)}
                      disabled={!canSave}
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Input
                      label="Cantidad"
                      type="number"
                      step="0.0001"
                      value={item.cantidad}
                      onChange={(e) => updateItemField(idx, 'cantidad', e.target.value)}
                      disabled={!canSave}
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Input
                      label="Precio unit."
                      type="number"
                      step="0.0001"
                      value={item.precio_unitario}
                      onChange={(e) => updateItemField(idx, 'precio_unitario', e.target.value)}
                      disabled={!canSave}
                    />
                  </div>
                  <div className="md:col-span-2">
                    <Select
                      label="IVA"
                      value={String(item.alicuota_iva_id)}
                      onChange={(e) => updateItemField(idx, 'alicuota_iva_id', Number(e.target.value))}
                      disabled={!canSave}
                    >
                      {ALICUOTA_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </Select>
                  </div>
                  <div className="md:col-span-1 flex items-end justify-end">
                    {canSave && (
                      <button
                        type="button"
                        className="mb-1 flex h-9 w-9 items-center justify-center rounded-md hover:bg-error-light"
                        onClick={() => removeItem(idx)}
                        title="Eliminar item"
                      >
                        <Trash2 className="h-4 w-4 text-error" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {formError && (
          <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
            {formError}
          </div>
        )}
      </div>
    </Modal>
  )
}

export default ItemsModal
