# Tipos de Comprobante
TIPOS_COMPROBANTE = {
    1: 'Factura A',
    2: 'Nota de Débito A',
    3: 'Nota de Crédito A',
    6: 'Factura B',
    7: 'Nota de Débito B',
    8: 'Nota de Crédito B',
    11: 'Factura C',
    12: 'Nota de Débito C',
    13: 'Nota de Crédito C',
    51: 'Factura M',
    52: 'Nota de Débito M',
    53: 'Nota de Crédito M',
}

# Tipos de Concepto
TIPOS_CONCEPTO = {
    1: 'Productos',
    2: 'Servicios',
    3: 'Productos y Servicios',
}

# Tipos de Documento
TIPOS_DOCUMENTO = {
    80: 'CUIT',
    86: 'CUIL',
    87: 'CDI',
    89: 'LE',
    90: 'LC',
    91: 'CI Extranjera',
    92: 'en trámite',
    93: 'Acta Nacimiento',
    95: 'CI Bs. As. RNP',
    96: 'DNI',
    99: 'Doc. (Otro)',
    0: 'CI Policía Federal',
}

# Alícuotas de IVA
ALICUOTAS_IVA = {
    3: {'porcentaje': 0, 'descripcion': '0%'},
    4: {'porcentaje': 10.5, 'descripcion': '10.5%'},
    5: {'porcentaje': 21, 'descripcion': '21%'},
    6: {'porcentaje': 27, 'descripcion': '27%'},
    8: {'porcentaje': 5, 'descripcion': '5%'},
    9: {'porcentaje': 2.5, 'descripcion': '2.5%'},
}

# Condiciones de IVA
CONDICIONES_IVA = {
    1: 'IVA Responsable Inscripto',
    4: 'IVA Sujeto Exento',
    5: 'Consumidor Final',
    6: 'Responsable Monotributo',
    8: 'Proveedor del Exterior',
    9: 'Cliente del Exterior',
    10: 'IVA Liberado – Ley Nº 19.640',
    11: 'IVA Responsable Inscripto – Agente de Percepción',
    13: 'Monotributista Social',
    15: 'IVA No Alcanzado',
}

# Monedas
MONEDAS = {
    'PES': {'codigo': 'PES', 'descripcion': 'Pesos Argentinos'},
    'DOL': {'codigo': 'DOL', 'descripcion': 'Dólar Estadounidense'},
    '012': {'codigo': '012', 'descripcion': 'Real'},
    '014': {'codigo': '014', 'descripcion': 'Corona Danesa'},
    '019': {'codigo': '019', 'descripcion': 'Yenes'},
    '021': {'codigo': '021', 'descripcion': 'Libra Esterlina'},
    '060': {'codigo': '060', 'descripcion': 'Euro'},
}
