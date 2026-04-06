import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { Button, CurrencyInput, DatePicker, Input, Modal, Select } from '@/components/ui'
import { formatCUIT } from '@/lib/utils'
import { toast } from '@/stores/toastStore'
import { TIPOS_NOTA, TIPO_COMPROBANTE_OPTIONS, CONCEPTO_OPTIONS, ALICUOTA_OPTIONS, ALICUOTA_PORCENTAJE, EMPTY_ITEM } from './constants'

const INITIAL_FORM = {
  facturador_id: '',
  receptor_id: '',
  tipo_comprobante: '11',
  concepto: '2',
  fecha_emision: new Date().toISOString().slice(0, 10),
  fecha_desde: '',
  fecha_hasta: '',
  fecha_vto_pago: '',
  cbte_asoc_tipo: '',
  cbte_asoc_pto_vta: '',
  cbte_asoc_nro: '',
  etiqueta: '',
  items: [{ ...EMPTY_ITEM }],
}

function NuevaFacturaModal({ isOpen, onClose, onSuccess }) {
  const [formData, setFormData] = useState({ ...INITIAL_FORM, items: [{ ...EMPTY_ITEM }] })
  const [formError, setFormError] = useState('')
  const [loteMode, setLoteMode] = useState('new')
  const [selectedLoteId, setSelectedLoteId] = useState('')

  const { data: receptoresData } = useQuery({
    queryKey: ['receptores', 'nueva-factura'],
    queryFn: async () => {
      const response = await api.receptores.list({ per_page: 200, activo: true })
      return response.data.items || []
    },
    enabled: isOpen,
  })

  const { data: facturadoresData } = useQuery({
    queryKey: ['facturadores', 'nueva-factura'],
    queryFn: async () => {
      const response = await api.facturadores.list({ activo: true, per_page: 200 })
      return response.data.items || []
    },
    enabled: isOpen,
  })

  const { data: lotesData } = useQuery({
    queryKey: ['lotes', { para_facturar: true }],
    queryFn: async () => {
      const response = await api.lotes.list({ para_facturar: true })
      return response.data
    },
    enabled: isOpen,
  })

  const createMutation = useMutation({
    mutationFn: (payload) => api.facturas.create(payload),
    onSuccess: (response) => {
      toast.success('Factura creada correctamente')
      onSuccess?.(response.data.lote.id)
    },
    onError: (error) => {
      setFormError(error.response?.data?.error || 'No se pudo crear la factura')
    },
  })

  const resetForm = () => {
    setFormData({
      ...INITIAL_FORM,
      fecha_emision: new Date().toISOString().slice(0, 10),
      items: [{ ...EMPTY_ITEM }],
    })
    setFormError('')
    setLoteMode('new')
    setSelectedLoteId('')
  }

  useEffect(() => {
    if (!isOpen) {
      resetForm()
    }
  }, [isOpen])

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
    if (!formData.facturador_id) return 'Seleccioná un facturador'
    if (!formData.receptor_id) return 'Seleccioná un receptor'
    if (!formData.tipo_comprobante) return 'Tipo de comprobante requerido'
    if (!formData.concepto) return 'Concepto requerido'
    if (!formData.fecha_emision) return 'Fecha de emisión requerida'
    if (loteMode === 'new' && !formData.etiqueta?.trim()) return 'La etiqueta del lote es requerida'
    if (loteMode === 'existing' && !selectedLoteId) return 'Seleccioná un lote existente'

    const tipoComprobante = Number(formData.tipo_comprobante)
    if (TIPOS_NOTA.has(tipoComprobante)) {
      if (!formData.cbte_asoc_tipo || !formData.cbte_asoc_pto_vta || !formData.cbte_asoc_nro) {
        return 'Para notas se requiere comprobante asociado completo'
      }
    }

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

  const calculatedTotals = useMemo(() => {
    const tipoC = [11, 12, 13].includes(Number(formData.tipo_comprobante))
    let importeNeto = 0
    let importeIva = 0
    for (const item of formData.items) {
      const cantidad = parseFloat(item.cantidad) || 0
      const precio = parseFloat(item.precio_unitario) || 0
      const subtotal = cantidad * precio
      const porcentaje = ALICUOTA_PORCENTAJE[item.alicuota_iva_id] ?? 21
      importeIva += subtotal * porcentaje / 100
      importeNeto += subtotal
    }
    if (tipoC) importeIva = 0
    return {
      importe_neto: importeNeto.toFixed(2),
      importe_iva: importeIva.toFixed(2),
      importe_total: (importeNeto + importeIva).toFixed(2),
    }
  }, [formData.items, formData.tipo_comprobante])

  const handleCreate = () => {
    const validationError = validate()
    if (validationError) {
      setFormError(validationError)
      return
    }
    setFormError('')

    const payload = {
      facturador_id: formData.facturador_id,
      receptor_id: formData.receptor_id,
      tipo_comprobante: Number(formData.tipo_comprobante),
      concepto: Number(formData.concepto),
      fecha_emision: formData.fecha_emision,
      fecha_desde: formData.fecha_desde || null,
      fecha_hasta: formData.fecha_hasta || null,
      fecha_vto_pago: formData.fecha_vto_pago || null,
      cbte_asoc_tipo: formData.cbte_asoc_tipo ? Number(formData.cbte_asoc_tipo) : null,
      cbte_asoc_pto_vta: formData.cbte_asoc_pto_vta ? Number(formData.cbte_asoc_pto_vta) : null,
      cbte_asoc_nro: formData.cbte_asoc_nro ? Number(formData.cbte_asoc_nro) : null,
      ...(loteMode === 'new'
        ? { etiqueta: formData.etiqueta.trim() }
        : { lote_id: selectedLoteId }
      ),
      items: formData.items.map((item) => ({
        descripcion: item.descripcion.trim(),
        cantidad: Number(item.cantidad),
        precio_unitario: Number(item.precio_unitario),
        alicuota_iva_id: Number(item.alicuota_iva_id || 5),
      })),
    }

    createMutation.mutate(payload)
  }

  const facturadores = facturadoresData || []
  const tipoComprobante = Number(formData.tipo_comprobante)
  const isNota = TIPOS_NOTA.has(tipoComprobante)
  const isTipoC = [11, 12, 13].includes(tipoComprobante)

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Nueva Factura"
      className="max-w-4xl"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creando...' : 'Crear Factura'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {/* Lote */}
        <div className="space-y-3 rounded-md border border-border p-3">
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="radio"
                name="loteMode"
                value="new"
                checked={loteMode === 'new'}
                onChange={() => { setLoteMode('new'); setSelectedLoteId('') }}
                className="accent-primary"
              />
              Nuevo lote
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="radio"
                name="loteMode"
                value="existing"
                checked={loteMode === 'existing'}
                onChange={() => { setLoteMode('existing'); updateField('etiqueta', '') }}
                className="accent-primary"
              />
              Lote existente
            </label>
          </div>

          {loteMode === 'new' ? (
            <div>
              <Input
                label="Etiqueta del lote"
                placeholder="Ej: Factura-Enero-2026"
                value={formData.etiqueta}
                onChange={(e) => updateField('etiqueta', e.target.value)}
              />
              <p className="mt-1 text-xs text-text-muted">
                No se permiten etiquetas duplicadas dentro del tenant.
              </p>
            </div>
          ) : (
            <Select
              label="Seleccionar lote"
              value={selectedLoteId}
              onChange={(e) => setSelectedLoteId(e.target.value)}
            >
              <option value="">Seleccionar...</option>
              {(lotesData?.items || []).map((lote) => (
                <option key={lote.id} value={lote.id}>
                  {lote.etiqueta} ({lote.total_facturas} facturas)
                </option>
              ))}
            </Select>
          )}
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Select label="Facturador" value={formData.facturador_id} onChange={(e) => updateField('facturador_id', e.target.value)}>
            <option value="">Seleccionar...</option>
            {facturadores.filter((f) => f.activo && f.tiene_certificados).map((f) => (
              <option key={f.id} value={f.id}>
                {f.razon_social} ({formatCUIT(f.cuit)}) - PV {f.punto_venta} - {f.ambiente}
              </option>
            ))}
          </Select>
          <Select label="Receptor" value={formData.receptor_id} onChange={(e) => updateField('receptor_id', e.target.value)}>
            <option value="">Seleccionar...</option>
            {(receptoresData || []).map((receptor) => (
              <option key={receptor.id} value={receptor.id}>
                {receptor.razon_social} ({formatCUIT(receptor.doc_nro)})
              </option>
            ))}
          </Select>
          <Select label="Tipo comprobante" value={String(formData.tipo_comprobante)} onChange={(e) => updateField('tipo_comprobante', e.target.value)}>
            {TIPO_COMPROBANTE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-1">
          <Select label="Concepto" value={String(formData.concepto)} onChange={(e) => updateField('concepto', e.target.value)}>
            {CONCEPTO_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <DatePicker label="Fecha emisión" value={formData.fecha_emision} onChange={(v) => updateField('fecha_emision', v)} />
          <DatePicker label="Fecha desde" value={formData.fecha_desde} onChange={(v) => updateField('fecha_desde', v)} />
          <DatePicker label="Fecha hasta" value={formData.fecha_hasta} onChange={(v) => updateField('fecha_hasta', v)} />
          <DatePicker label="Vto pago" value={formData.fecha_vto_pago} onChange={(v) => updateField('fecha_vto_pago', v)} />
        </div>

        <div className={`grid grid-cols-1 gap-3 ${isTipoC ? 'md:grid-cols-2' : 'md:grid-cols-3'}`}>
          <CurrencyInput label="Importe total" decimalScale={2} value={calculatedTotals.importe_total} disabled />
          <CurrencyInput label="Importe neto" decimalScale={2} value={calculatedTotals.importe_neto} disabled />
          {!isTipoC && <CurrencyInput label="IVA" decimalScale={2} value={calculatedTotals.importe_iva} disabled />}
        </div>

        {isNota && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Input label="Cbte asoc tipo" type="number" value={formData.cbte_asoc_tipo} onChange={(e) => updateField('cbte_asoc_tipo', e.target.value)} />
            <Input label="Cbte asoc pto vta" type="number" value={formData.cbte_asoc_pto_vta} onChange={(e) => updateField('cbte_asoc_pto_vta', e.target.value)} />
            <Input label="Cbte asoc nro" type="number" value={formData.cbte_asoc_nro} onChange={(e) => updateField('cbte_asoc_nro', e.target.value)} />
          </div>
        )}

        <div className="rounded-md border border-border">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <p className="text-sm font-medium text-text-primary">Items</p>
            <Button size="sm" variant="secondary" icon={Plus} onClick={addItem}>
              Agregar
            </Button>
          </div>
          <div className="space-y-3 p-3">
            {formData.items.map((item, idx) => (
              <div key={idx} className="grid grid-cols-1 gap-2 rounded-md border border-border p-2 md:grid-cols-12">
                <div className={isTipoC ? 'md:col-span-5' : 'md:col-span-4'}>
                  <Input
                    label={`Descripción #${idx + 1}`}
                    value={item.descripcion}
                    onChange={(e) => updateItemField(idx, 'descripcion', e.target.value)}
                  />
                </div>
                <div className={isTipoC ? 'md:col-span-3' : 'md:col-span-2'}>
                  <Input
                    label="Cantidad"
                    type="number"
                    step="0.0001"
                    value={item.cantidad}
                    onChange={(e) => updateItemField(idx, 'cantidad', e.target.value)}
                  />
                </div>
                <div className={isTipoC ? 'md:col-span-3' : 'md:col-span-2'}>
                  <CurrencyInput
                    label="Precio unit."
                    decimalScale={4}
                    value={item.precio_unitario}
                    onValueChange={(vals) => updateItemField(idx, 'precio_unitario', vals.value)}
                  />
                </div>
                {!isTipoC && (
                  <div className="md:col-span-2">
                    <Select
                      label="IVA"
                      value={String(item.alicuota_iva_id)}
                      onChange={(e) => updateItemField(idx, 'alicuota_iva_id', Number(e.target.value))}
                    >
                      {ALICUOTA_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </Select>
                  </div>
                )}
                {!isTipoC && (
                  <div className="md:col-span-1 flex flex-col">
                    <label className="text-sm font-medium text-text-primary">IVA $</label>
                    <span className="flex h-10 items-center text-sm text-text-secondary">
                      {(() => {
                        const subtotal = (parseFloat(item.cantidad) || 0) * (parseFloat(item.precio_unitario) || 0)
                        const porcentaje = ALICUOTA_PORCENTAJE[item.alicuota_iva_id] ?? 21
                        return (subtotal * porcentaje / 100).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      })()}
                    </span>
                  </div>
                )}
                <div className="md:col-span-1 flex items-end justify-end">
                  <button
                    type="button"
                    className="mb-1 flex h-9 w-9 items-center justify-center rounded-md hover:bg-error-light"
                    onClick={() => removeItem(idx)}
                    title="Eliminar item"
                  >
                    <Trash2 className="h-4 w-4 text-error" />
                  </button>
                </div>
              </div>
            ))}
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

export default NuevaFacturaModal
