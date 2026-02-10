import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Modal } from '@/components/ui'
import { formatCUIT, formatCurrency, formatComprobante } from '@/lib/utils'

function ItemsModal({ factura, onClose }) {
  const { data: items, isLoading } = useQuery({
    queryKey: ['factura-items', factura?.id],
    queryFn: async () => {
      const response = await api.facturas.getItems(factura.id)
      return response.data.items
    },
    enabled: !!factura?.id,
  })

  if (!factura) return null

  return (
    <Modal
      isOpen={!!factura}
      onClose={onClose}
      title="Items de Factura"
      className="max-w-2xl"
    >
      {/* Factura Info */}
      <div className="mb-4 rounded-md bg-secondary/50 p-4">
        <p className="font-medium text-text-primary">
          Factura: {formatComprobante(factura.tipo_comprobante, factura.punto_venta, factura.numero_comprobante || 0)}
        </p>
        <p className="text-sm text-text-secondary">
          Receptor: {factura.receptor?.razon_social} ({formatCUIT(factura.receptor?.doc_nro)})
        </p>
      </div>

      {/* Items Table */}
      <div className="overflow-hidden rounded-md border border-border">
        <table className="w-full">
          <thead className="bg-secondary/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary">
                Descripción
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary">
                Cantidad
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary">
                Precio Unit.
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-text-secondary">
                Subtotal
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-text-muted">
                  Cargando...
                </td>
              </tr>
            ) : items?.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-text-muted">
                  Sin items detallados
                </td>
              </tr>
            ) : (
              items?.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="px-4 py-3 text-sm text-text-primary">
                    {item.descripcion}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-text-primary">
                    {item.cantidad}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-text-primary">
                    {formatCurrency(item.precio_unitario)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-text-primary">
                    {formatCurrency(item.subtotal)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Totals */}
        <div className="border-t border-border bg-secondary/50 p-4">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Subtotal Neto</span>
            <span className="text-text-primary">{formatCurrency(factura.importe_neto)}</span>
          </div>
          <div className="mt-1 flex justify-between text-sm">
            <span className="text-text-secondary">IVA</span>
            <span className="text-text-primary">{formatCurrency(factura.importe_iva || 0)}</span>
          </div>
          <div className="mt-2 flex justify-between border-t border-border pt-2">
            <span className="font-semibold text-text-primary">Total</span>
            <span className="font-semibold text-text-primary">
              {formatCurrency(factura.importe_total)}
            </span>
          </div>
        </div>
      </div>
    </Modal>
  )
}

export default ItemsModal
