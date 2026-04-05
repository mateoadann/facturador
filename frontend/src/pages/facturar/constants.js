export const TIPOS_NOTA = new Set([2, 3, 7, 8, 12, 13])

export const TIPO_COMPROBANTE_OPTIONS = [
  { value: 1, label: 'Factura A' },
  { value: 6, label: 'Factura B' },
  { value: 11, label: 'Factura C' },
  { value: 2, label: 'Nota Débito A' },
  { value: 3, label: 'Nota Crédito A' },
  { value: 7, label: 'Nota Débito B' },
  { value: 8, label: 'Nota Crédito B' },
  { value: 12, label: 'Nota Débito C' },
  { value: 13, label: 'Nota Crédito C' },
]

export const CONCEPTO_OPTIONS = [
  { value: 1, label: 'Productos' },
  { value: 2, label: 'Servicios' },
  { value: 3, label: 'Productos y Servicios' },
]

export const ALICUOTA_OPTIONS = [
  { value: 3, label: '0%' },
  { value: 4, label: '10.5%' },
  { value: 5, label: '21%' },
  { value: 6, label: '27%' },
  { value: 8, label: '5%' },
  { value: 9, label: '2.5%' },
]

export const ALICUOTA_PORCENTAJE = {
  3: 0,
  4: 10.5,
  5: 21,
  6: 27,
  8: 5,
  9: 2.5,
}

export const EMPTY_ITEM = {
  descripcion: '',
  cantidad: '1',
  precio_unitario: '0',
  alicuota_iva_id: 5,
}
