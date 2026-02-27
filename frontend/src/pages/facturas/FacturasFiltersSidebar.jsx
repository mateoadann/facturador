import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { Button, Checkbox, Input, Select } from '@/components/ui'

const TIPOS_COMPROBANTE_OPTIONS = [
  { value: 1, label: 'Factura A (1)' },
  { value: 2, label: 'Nota de Débito A (2)' },
  { value: 3, label: 'Nota de Crédito A (3)' },
  { value: 6, label: 'Factura B (6)' },
  { value: 7, label: 'Nota de Débito B (7)' },
  { value: 8, label: 'Nota de Crédito B (8)' },
  { value: 11, label: 'Factura C (11)' },
  { value: 12, label: 'Nota de Débito C (12)' },
  { value: 13, label: 'Nota de Crédito C (13)' },
]

function normalizeText(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
}

function FacturasFiltersSidebar({
  isOpen,
  onClose,
  filters,
  onApply,
  facturadores,
  lotes,
  receptores,
}) {
  const [draft, setDraft] = useState(filters)
  const [loteSearch, setLoteSearch] = useState('')
  const [receptorSearch, setReceptorSearch] = useState('')

  useEffect(() => {
    if (isOpen) {
      setDraft(filters)
      setLoteSearch('')
      setReceptorSearch('')
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, filters])

  const filteredLotes = useMemo(() => {
    const term = normalizeText(loteSearch)
    return [...lotes]
      .sort((a, b) => (a.etiqueta || '').localeCompare(b.etiqueta || ''))
      .filter((lote) => !term || normalizeText(lote.etiqueta).includes(term))
  }, [lotes, loteSearch])

  const filteredReceptores = useMemo(() => {
    const term = normalizeText(receptorSearch)
    return [...receptores]
      .sort((a, b) => (a.razon_social || '').localeCompare(b.razon_social || ''))
      .filter((receptor) => !term || normalizeText(receptor.razon_social).includes(term))
  }, [receptores, receptorSearch])

  const toggleArrayValue = (field, value) => {
    const next = draft[field].includes(value)
      ? draft[field].filter((item) => item !== value)
      : [...draft[field], value]
    setDraft({ ...draft, [field]: next })
  }

  const clearAll = () => {
    setDraft({
      estadoVista: 'finalizados',
      facturador_id: '',
      lote_ids: [],
      receptor_ids: [],
      tipo_comprobantes: [],
      fecha_desde: '',
      fecha_hasta: '',
      page: 1,
    })
  }

  const handleApply = () => {
    onApply({ ...draft, page: 1 })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      <button className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Cerrar filtros" />

      <aside className="absolute right-0 top-0 h-full w-full max-w-lg border-l border-border bg-card shadow-xl">
        <div className="flex h-14 items-center justify-between border-b border-border px-5">
          <h2 className="text-base font-semibold text-text-primary">Filtros de facturas</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary"
          >
            <X className="h-5 w-5 text-text-secondary" />
          </button>
        </div>

        <div className="h-[calc(100%-7rem)] space-y-5 overflow-y-auto px-5 py-4">
          <Select
            label="Estado"
            value={draft.estadoVista}
            onChange={(e) => setDraft({ ...draft, estadoVista: e.target.value })}
          >
            <option value="finalizados">Todos finalizados</option>
            <option value="autorizado">Autorizado</option>
            <option value="error">Error</option>
            <option value="pendiente">Pendiente</option>
            <option value="borrador">Borrador</option>
          </Select>

          <Select
            label="Facturador"
            value={draft.facturador_id}
            onChange={(e) => setDraft({ ...draft, facturador_id: e.target.value })}
          >
            <option value="">Todos</option>
            {facturadores.map((f) => (
              <option key={f.id} value={f.id}>
                {f.razon_social}
              </option>
            ))}
          </Select>

          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Lote</p>
            <Input
              placeholder="Buscar lote..."
              value={loteSearch}
              onChange={(e) => setLoteSearch(e.target.value)}
              className="mb-2"
            />
            <div className="max-h-40 space-y-2 overflow-y-auto rounded-md border border-border p-3">
              {filteredLotes.length === 0 ? (
                <p className="text-sm text-text-muted">No se encontraron lotes</p>
              ) : (
                filteredLotes.map((lote) => (
                  <Checkbox
                    key={lote.id}
                    checked={draft.lote_ids.includes(lote.id)}
                    onChange={() => toggleArrayValue('lote_ids', lote.id)}
                    label={lote.etiqueta}
                  />
                ))
              )}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Receptor</p>
            <Input
              placeholder="Buscar receptor..."
              value={receptorSearch}
              onChange={(e) => setReceptorSearch(e.target.value)}
              className="mb-2"
            />
            <div className="max-h-44 space-y-2 overflow-y-auto rounded-md border border-border p-3">
              {filteredReceptores.length === 0 ? (
                <p className="text-sm text-text-muted">No se encontraron receptores</p>
              ) : (
                filteredReceptores.map((receptor) => (
                  <Checkbox
                    key={receptor.id}
                    checked={draft.receptor_ids.includes(receptor.id)}
                    onChange={() => toggleArrayValue('receptor_ids', receptor.id)}
                    label={receptor.razon_social}
                  />
                ))
              )}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-text-primary">Tipo de comprobante</p>
            <div className="max-h-44 space-y-2 overflow-y-auto rounded-md border border-border p-3">
              {TIPOS_COMPROBANTE_OPTIONS.map((tipo) => (
                <Checkbox
                  key={tipo.value}
                  checked={draft.tipo_comprobantes.includes(tipo.value)}
                  onChange={() => toggleArrayValue('tipo_comprobantes', tipo.value)}
                  label={tipo.label}
                />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Fecha desde"
              type="date"
              value={draft.fecha_desde}
              onChange={(e) => setDraft({ ...draft, fecha_desde: e.target.value })}
            />
            <Input
              label="Fecha hasta"
              type="date"
              value={draft.fecha_hasta}
              onChange={(e) => setDraft({ ...draft, fecha_hasta: e.target.value })}
            />
          </div>
        </div>

        <div className="flex h-14 items-center justify-between border-t border-border px-5">
          <Button variant="secondary" onClick={clearAll}>Limpiar</Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onClose}>Cancelar</Button>
            <Button onClick={handleApply}>Aplicar filtros</Button>
          </div>
        </div>
      </aside>
    </div>
  )
}

export default FacturasFiltersSidebar
