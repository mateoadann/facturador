import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Badge, Button, Modal } from '@/components/ui'
import { formatCUIT, formatCurrency, formatDate } from '@/lib/utils'

const CONCEPTO_LABELS = {
  1: 'Productos',
  2: 'Servicios',
  3: 'Productos y servicios',
}

const TIPO_COMPROBANTE_LABELS = {
  1: 'Factura A',
  2: 'Nota de Debito A',
  3: 'Nota de Credito A',
  6: 'Factura B',
  7: 'Nota de Debito B',
  8: 'Nota de Credito B',
  11: 'Factura C',
  12: 'Nota de Debito C',
  13: 'Nota de Credito C',
}

function formatComprobanteSimple(factura) {
  if (!factura) return '-'
  const tipo = TIPO_COMPROBANTE_LABELS[factura.tipo_comprobante] || `T${factura.tipo_comprobante}`
  if (factura.numero_comprobante == null) {
    return tipo
  }
  return `${tipo} ${Number(factura.numero_comprobante)}`
}

function FacturaViewModal({ isOpen, onClose, facturaId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['factura-detail', facturaId],
    queryFn: async () => {
      const response = await api.facturas.get(facturaId)
      return response.data
    },
    enabled: isOpen && !!facturaId,
  })

  const factura = data || null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Detalle de comprobante"
      className="max-w-3xl"
      footer={(
        <Button variant="secondary" onClick={onClose}>
          Cerrar
        </Button>
      )}
    >
      {isLoading || !factura ? (
        <p className="text-sm text-text-secondary">Cargando detalle...</p>
      ) : (
        <div className="space-y-4">
          <div className="rounded-md bg-secondary/50 p-4">
            <p className="text-base font-semibold text-text-primary">{formatComprobanteSimple(factura)}</p>
            <p className="mt-1 text-sm text-text-secondary">Receptor: {factura.receptor?.razon_social || '-'}</p>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Estado</p>
              <div className="mt-1">
                <Badge variant={factura.estado === 'autorizado' ? 'success' : 'default'}>
                  {factura.estado || '-'}
                </Badge>
              </div>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Concepto</p>
              <p className="mt-1 font-medium text-text-primary">{CONCEPTO_LABELS[factura.concepto] || '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Fecha de emision</p>
              <p className="mt-1 font-medium text-text-primary">{formatDate(factura.fecha_emision) || '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">CAE</p>
              <p className="mt-1 font-medium text-text-primary">{factura.cae || '-'}</p>
              {factura.cae_vencimiento && (
                <p className="text-xs text-text-secondary">Vto: {formatDate(factura.cae_vencimiento)}</p>
              )}
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">CUIT receptor</p>
              <p className="mt-1 font-medium text-text-primary">{formatCUIT(factura.receptor?.doc_nro || '') || '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Email receptor</p>
              <p className="mt-1 font-medium text-text-primary">{factura.receptor?.email || '-'}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Facturador</p>
              <p className="mt-1 font-medium text-text-primary">{factura.facturador?.razon_social || '-'}</p>
              <p className="text-xs text-text-secondary">{formatCUIT(factura.facturador?.cuit || '') || '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Punto de venta</p>
              <p className="mt-1 font-medium text-text-primary">{factura.punto_venta ?? '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Numero comprobante</p>
              <p className="mt-1 font-medium text-text-primary">{factura.numero_comprobante ?? '-'}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Importe neto</p>
              <p className="mt-1 font-medium text-text-primary">{formatCurrency(factura.importe_neto || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Importe IVA</p>
              <p className="mt-1 font-medium text-text-primary">{formatCurrency(factura.importe_iva || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Importe total</p>
              <p className="mt-1 font-medium text-text-primary">{formatCurrency(factura.importe_total || 0)}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Moneda</p>
              <p className="mt-1 font-medium text-text-primary">{factura.moneda || '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Cotizacion</p>
              <p className="mt-1 font-medium text-text-primary">{factura.cotizacion ?? '-'}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Fecha vto pago</p>
              <p className="mt-1 font-medium text-text-primary">{formatDate(factura.fecha_vto_pago) || '-'}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Periodo servicio</p>
              <p className="mt-1 font-medium text-text-primary">
                {formatDate(factura.fecha_desde) || '-'} a {formatDate(factura.fecha_hasta) || '-'}
              </p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Email comprobante</p>
              <p className="mt-1 font-medium text-text-primary">
                {factura.email_enviado ? 'Enviado' : factura.email_error ? 'Error' : 'No enviado'}
              </p>
              <p className="text-xs text-text-secondary">
                {factura.email_enviado_at ? `Fecha: ${formatDate(factura.email_enviado_at)}` : factura.email_error || '-'}
              </p>
            </div>
          </div>

          {(factura.cbte_asoc_tipo || factura.cbte_asoc_nro || factura.cbte_asoc_pto_vta) && (
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase text-text-muted">Comprobante asociado</p>
              <p className="mt-1 font-medium text-text-primary">
                Tipo {factura.cbte_asoc_tipo || '-'} - PV {factura.cbte_asoc_pto_vta || '-'} - Nro {factura.cbte_asoc_nro || '-'}
              </p>
            </div>
          )}

          {factura.error_mensaje && (
            <div className="rounded-md border border-error/30 bg-error-light p-3">
              <p className="text-xs uppercase text-error">Error ARCA</p>
              <p className="mt-1 text-sm text-error-foreground">
                {factura.error_codigo ? `${factura.error_codigo} - ` : ''}
                {factura.error_mensaje}
              </p>
            </div>
          )}

          <div className="rounded-md border border-border p-3">
            <p className="mb-2 text-xs uppercase text-text-muted">Items del comprobante</p>
            {!factura.items || factura.items.length === 0 ? (
              <p className="text-sm text-text-secondary">Sin items registrados</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="border-b border-border text-left text-text-secondary">
                    <tr>
                      <th className="py-2 pr-2">Descripcion</th>
                      <th className="py-2 pr-2">Cantidad</th>
                      <th className="py-2 pr-2">Precio unit.</th>
                      <th className="py-2 pr-2">IVA</th>
                      <th className="py-2">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {factura.items.map((item) => (
                      <tr key={item.id} className="border-b border-border/60 last:border-b-0">
                        <td className="py-2 pr-2 text-text-primary">{item.descripcion}</td>
                        <td className="py-2 pr-2 text-text-secondary">{item.cantidad}</td>
                        <td className="py-2 pr-2 text-text-secondary">{formatCurrency(item.precio_unitario || 0)}</td>
                        <td className="py-2 pr-2 text-text-secondary">{formatCurrency(item.importe_iva || 0)}</td>
                        <td className="py-2 text-text-primary">{formatCurrency(item.subtotal || 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}

export default FacturaViewModal
