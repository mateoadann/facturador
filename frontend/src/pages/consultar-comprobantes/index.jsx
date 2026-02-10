import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Search, FileText, AlertCircle } from 'lucide-react'
import { api } from '@/api/client'
import { Button, Input, Select, Badge } from '@/components/ui'
import { formatCurrency, formatCUIT, formatDate } from '@/lib/utils'
import { toast } from '@/stores/toastStore'

const TIPOS_COMPROBANTE = [
  { value: '1', label: 'Factura A' },
  { value: '6', label: 'Factura B' },
  { value: '11', label: 'Factura C' },
  { value: '3', label: 'Nota de Crédito A' },
  { value: '8', label: 'Nota de Crédito B' },
  { value: '13', label: 'Nota de Crédito C' },
  { value: '2', label: 'Nota de Débito A' },
  { value: '7', label: 'Nota de Débito B' },
  { value: '12', label: 'Nota de Débito C' },
]

function ConsultarComprobantes() {
  const [formData, setFormData] = useState({
    facturador_id: '',
    tipo_comprobante: '',
    punto_venta: '',
    numero: '',
  })
  const [resultado, setResultado] = useState(null)

  const { data: facturadoresData } = useQuery({
    queryKey: ['facturadores'],
    queryFn: async () => {
      const response = await api.facturadores.list({ per_page: 100 })
      return response.data
    },
  })

  const facturadores = facturadoresData?.items || []

  const consultarMutation = useMutation({
    mutationFn: (data) => api.comprobantes.consultar(data),
    onSuccess: (response) => {
      setResultado(response.data.data)
      toast.success('Comprobante encontrado')
    },
    onError: (error) => {
      setResultado(null)
      toast.error(
        'Error al consultar',
        error.response?.data?.error || 'No se pudo consultar el comprobante'
      )
    },
  })

  const ultimoMutation = useMutation({
    mutationFn: (data) => api.comprobantes.ultimoAutorizado(data),
    onSuccess: (response) => {
      const data = response.data
      toast.info(
        'Último autorizado',
        `Nº ${data.ultimo_autorizado} — Próximo: ${data.proximo}`
      )
    },
    onError: (error) => {
      toast.error(
        'Error',
        error.response?.data?.error || 'No se pudo consultar'
      )
    },
  })

  const handleConsultar = () => {
    if (!formData.facturador_id || !formData.tipo_comprobante || !formData.punto_venta || !formData.numero) {
      toast.warning('Campos incompletos', 'Completá todos los campos para consultar')
      return
    }
    consultarMutation.mutate({
      facturador_id: formData.facturador_id,
      tipo_comprobante: parseInt(formData.tipo_comprobante, 10),
      punto_venta: parseInt(formData.punto_venta, 10),
      numero: parseInt(formData.numero, 10),
    })
  }

  const handleUltimoAutorizado = () => {
    if (!formData.facturador_id || !formData.tipo_comprobante) {
      toast.warning('Campos incompletos', 'Seleccioná facturador y tipo de comprobante')
      return
    }
    ultimoMutation.mutate({
      facturador_id: formData.facturador_id,
      tipo_comprobante: parseInt(formData.tipo_comprobante, 10),
    })
  }

  const selectedFacturador = facturadores.find((f) => f.id === formData.facturador_id)

  return (
    <div className="space-y-6">
      {/* Formulario */}
      <div className="rounded-lg border border-border bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">
          Consultar Comprobante en ARCA
        </h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Select
            label="Facturador"
            value={formData.facturador_id}
            onChange={(e) => setFormData({ ...formData, facturador_id: e.target.value })}
          >
            <option value="">Seleccionar...</option>
            {facturadores.map((f) => (
              <option key={f.id} value={f.id}>
                {f.razon_social} ({formatCUIT(f.cuit)})
              </option>
            ))}
          </Select>

          <Select
            label="Tipo de Comprobante"
            value={formData.tipo_comprobante}
            onChange={(e) => setFormData({ ...formData, tipo_comprobante: e.target.value })}
          >
            <option value="">Seleccionar...</option>
            {TIPOS_COMPROBANTE.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>

          <Input
            label="Punto de Venta"
            type="number"
            placeholder="1"
            value={formData.punto_venta}
            onChange={(e) => setFormData({ ...formData, punto_venta: e.target.value })}
          />

          <Input
            label="Número"
            type="number"
            placeholder="1"
            value={formData.numero}
            onChange={(e) => setFormData({ ...formData, numero: e.target.value })}
          />
        </div>

        {selectedFacturador && !selectedFacturador.tiene_certificados && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-warning-light p-3 text-sm text-warning-foreground">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>Este facturador no tiene certificados cargados. Cargalos desde la sección Facturadores.</span>
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <Button
            icon={Search}
            onClick={handleConsultar}
            disabled={consultarMutation.isPending}
          >
            {consultarMutation.isPending ? 'Consultando...' : 'Consultar Comprobante'}
          </Button>
          <Button
            variant="secondary"
            icon={FileText}
            onClick={handleUltimoAutorizado}
            disabled={ultimoMutation.isPending}
          >
            {ultimoMutation.isPending ? 'Consultando...' : 'Último Autorizado'}
          </Button>
        </div>
      </div>

      {/* Resultado */}
      {resultado && (
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-lg font-semibold text-text-primary">
            Resultado de la Consulta
          </h3>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="space-y-3">
              <DetailRow label="CAE" value={resultado.cae || '-'} />
              <DetailRow label="Vencimiento CAE" value={resultado.cae_vto ? formatDate(resultado.cae_vto) : '-'} />
              <DetailRow label="Fecha Emisión" value={resultado.fecha_cbte ? formatDate(resultado.fecha_cbte) : '-'} />
              <DetailRow label="Punto de Venta" value={resultado.punto_venta} />
              <DetailRow label="Número" value={resultado.cbte_desde} />
              <DetailRow
                label="Resultado"
                value={
                  <Badge variant={resultado.resultado === 'A' ? 'success' : 'error'}>
                    {resultado.resultado === 'A' ? 'Aprobado' : 'Rechazado'}
                  </Badge>
                }
              />
            </div>

            <div className="space-y-3">
              <DetailRow label="Tipo Comprobante" value={resultado.tipo_cbte} />
              <DetailRow label="Concepto" value={resultado.concepto} />
              <DetailRow label="Doc. Tipo" value={resultado.doc_tipo} />
              <DetailRow label="Doc. Nro" value={resultado.doc_nro} />
              <DetailRow label="Importe Total" value={formatCurrency(resultado.imp_total)} />
              <DetailRow label="Importe Neto" value={formatCurrency(resultado.imp_neto)} />
            </div>
          </div>

          {resultado.imp_iva != null && (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <DetailRow label="IVA" value={formatCurrency(resultado.imp_iva)} />
                <DetailRow label="Tributos" value={formatCurrency(resultado.imp_trib || 0)} />
              </div>
              <div className="space-y-3">
                <DetailRow label="Op. Exentas" value={formatCurrency(resultado.imp_op_ex || 0)} />
                <DetailRow label="Moneda" value={resultado.mon_id || 'PES'} />
              </div>
            </div>
          )}

          {resultado.observaciones && resultado.observaciones.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium text-text-secondary">Observaciones:</p>
              <div className="space-y-1">
                {resultado.observaciones.map((obs, i) => (
                  <p key={i} className="text-sm text-text-muted">
                    {obs.code}: {obs.msg}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 pb-2">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-medium text-text-primary">
        {typeof value === 'string' || typeof value === 'number' ? value : value}
      </span>
    </div>
  )
}

export default ConsultarComprobantes
