export const CONDICIONES_IVA = [
  { id: 1, label: 'IVA Responsable Inscripto' },
  { id: 4, label: 'IVA Sujeto Exento' },
  { id: 5, label: 'Consumidor Final' },
  { id: 6, label: 'Responsable Monotributo' },
]

export const getCondicionIvaLabel = (id) => {
  const found = CONDICIONES_IVA.find(c => c.id === id)
  return found ? found.label : '-'
}
