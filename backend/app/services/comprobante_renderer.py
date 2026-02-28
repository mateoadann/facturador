import base64
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote_plus

from flask import render_template_string

from arca_integration.constants import ALICUOTAS_IVA


COMPROBANTE_TEMPLATE = """
<!DOCTYPE html>
<html lang="es" data-template-version="comprobante-v2">
<head>
  <meta charset="utf-8" />
  <title>{{ titulo }} {{ punto_venta_largo }}-{{ numero_comprobante_largo }}</title>
  <style type="text/css">
    html,
    body {
      margin: 0;
      padding: 0;
    }

    @page {
      size: A4;
      margin: 0;
    }

    * {
      box-sizing: border-box;
      -webkit-user-select: none;
      -moz-user-select: none;
      -ms-user-select: none;
      user-select: none;
    }

    body {
      font-family: Arial, sans-serif;
      color: #111;
      font-size: 12px;
    }

    .page {
      width: 7.65in;
      margin: 0 auto;
      min-height: 11.29in;
      display: flex;
      flex-direction: column;
    }

    .page-break {
      page-break-after: always;
    }

    .copy-header {
      text-align: center;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 1px;
      margin: 3px 0 0;
      padding: 6px 0;
      border: 1px solid #000;
    }

    .bill-container {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      font-size: 12px;
    }

    .bill-emitter-row {
      border: 1px solid #000;
      border-top: 0;
      position: relative;
    }

    .bill-emitter-row td {
      width: 50%;
      border: 1px solid #000;
      border-top: 0;
      padding-top: 3px;
      padding-left: 5px;
      vertical-align: top;
    }

    .bill-emitter-row td:nth-child(1) {
      padding-right: 60px;
      padding-top: 6px;
    }

    .bill-emitter-row td:nth-child(1) p {
      margin: 2px 0;
      line-height: 1.2;
    }

    .bill-emitter-row td:nth-child(2) p {
      padding-left: 0;
      margin: 3px 0;
      line-height: 1.35;
    }

    .bill-emitter-row td:nth-child(2) .text-lg {
      display: block;
      margin-left: 0;
    }

    .bill-type {
      border: 1px solid #000;
      background: #fff;
      width: 60px;
      height: 50px;
      position: absolute;
      left: 0;
      right: 0;
      top: -1px;
      margin: auto;
      text-align: center;
      font-size: 36px;
      font-weight: 600;
      line-height: 50px;
    }

    .cod-line {
      font-size: 12px;
      font-weight: 700;
      margin-left: 60px;
      margin-top: 2px;
      margin-bottom: 4px;
    }

    .text-lg {
      font-size: 28px;
      font-weight: 700;
    }

    .text-md {
      font-size: 16px;
      font-weight: 700;
      text-align: center;
      margin-top: 2px;
      margin-bottom: 12px;
    }

    .text-center {
      text-align: center;
    }

    .text-right {
      text-align: right;
    }

    .col-2 { width: 16.6667%; float: left; }
    .col-3 { width: 25%; float: left; }
    .col-4 { width: 33.3333%; float: left; }
    .col-5 { width: 41.6667%; float: left; }
    .col-6 { width: 50%; float: left; }
    .col-8 { width: 66.6667%; float: left; }
    .col-10 { width: 83.3333%; float: left; }

    .row {
      overflow: hidden;
    }

    .margin-b-0 {
      margin-bottom: 1px;
    }

    .margin-b-10 {
      margin-bottom: 10px;
    }

    .fac-datos {
      margin-left: 0;
      padding: 0 10px 0 56px;
      max-width: 100%;
    }

    .comp-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      margin-top: 10px;
      margin-bottom: 4px;
      gap: 16px;
      align-items: baseline;
      width: 100%;
      padding: 0;
    }

    .content {
      flex: 1;
    }

    .comp-row p {
      margin: 0;
      font-size: 12px;
      line-height: 1.15;
      padding-left: 0;
      white-space: nowrap;
      min-width: 0;
      overflow: hidden;
      text-overflow: clip;
    }

    .comp-row p:last-child {
      text-align: right;
    }

    .receptor-block p {
      line-height: 1.35;
      margin-bottom: 3px;
    }

    .bill-row td {
      padding-top: 2px;
    }

    .bill-row td > div {
      border: 1px solid #000;
      margin: 0;
      padding: 16px 16px 10px 16px;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .bill-row.compact td > div,
    .bill-row.compact td > .row {
      padding: 10px 10px;
    }

    .bill-row.compact p {
      margin: 0;
      line-height: 1.2;
    }

    .items-table {
      border-collapse: collapse;
      width: 100%;
      table-layout: fixed;
    }

    .row-details td > div {
      border: 0;
      margin: 0;
      padding: 0;
    }

    .items-table thead {
      display: table-header-group;
    }

    .items-table tfoot {
      display: table-footer-group;
    }

    .items-table tbody tr {
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .items-table th,
    .items-table td {
      padding: 5px 6px;
      font-size: 11px;
      vertical-align: top;
    }

    .items-table thead tr {
      border-top: 1px solid;
      border-bottom: 1px solid;
      background: #b1b1b1;
      font-weight: 700;
      font-size: 11px;
    }

    .items-table tbody tr + tr {
      border-top: 1px solid #c0c0c0;
    }

    .items-table th.code,
    .items-table td.code {
      text-align: center;
    }

    .items-table th.desc,
    .items-table td.desc {
      text-align: left;
    }

    .items-table th.qty,
    .items-table td.qty,
    .items-table th.price,
    .items-table td.price,
    .items-table th.bonif,
    .items-table td.bonif,
    .items-table th.subtotal,
    .items-table td.subtotal,
    .items-table th.iva,
    .items-table td.iva,
    .items-table th.subtotaliva,
    .items-table td.subtotaliva {
      text-align: right;
    }

    .items-table th.unit,
    .items-table td.unit {
      text-align: left;
    }

    .item-descripcion {
      word-break: break-word;
    }

    .total-row td > div {
      border-width: 2px;
      font-size: 12px;
    }

    .total-row .row p {
      line-height: 1.5;
      margin: 0;
      padding: 0;
    }

    .total-row .row {
      margin: 0;
      padding: 0 8px;
    }

    .footer-block {
      margin-top: auto;
      width: 100%;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .footer-legal {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      padding-top: 4px;
    }

    .footer-legal .left {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      width: 62%;
    }

    #qrcode {
      width: 96px;
      max-width: 96px;
      height: 96px;
    }

    .marca {
      min-height: 96px;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
    }

    .marca svg {
      display: block;
      margin-bottom: 2px;
      margin-left: 0;
      width: 145px;
      height: auto;
    }

    .marca text {
      font-family: Arial, sans-serif;
    }

    .legal-title {
      font-weight: 700;
      font-size: 10px;
      letter-spacing: 0.2px;
      line-height: 1.1;
      margin-top: 0;
      margin-bottom: 2px;
      color: #000;
    }

    .legal-note {
      font-style: italic;
      font-size: 8px;
      color: #000;
      letter-spacing: 0;
      line-height: 1.1;
      text-align: left;
      margin-top: 0;
      margin-bottom: 0;
      max-width: 255px;
    }

    .footer-legal .right {
      width: 38%;
      text-align: right;
      font-size: 11px;
      line-height: 1.3;
      white-space: nowrap;
      padding-top: 2px;
    }

    .transparencia-row td > div {
      border: 1px solid #000;
      padding: 8px 12px 14px;
      margin: 0;
      font-size: 11px;
      line-height: 1.25;
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .transparencia-box .title {
      display: inline-block;
      font-weight: 700;
      font-style: italic;
      padding-bottom: 3px;
      border-bottom: 2px solid #000;
      margin: 2px 0 10px 0;
    }

    .transparencia-box .iva-line {
      display: flex;
      justify-content: start;
      align-items: baseline;
      gap: 30px;
      font-size: 11px;
      margin-bottom: 10px;
    }

    .transparencia-box .iva-line .label,
    .transparencia-box .iva-line .amount {
      font-weight: 700;
    }

    .transparencia-box .iva-line .label {
      margin-left: 140px;
    }

    .value-nowrap {
      white-space: nowrap;
    }

    p {
      margin-top: 0;
      margin-bottom: 2px;
    }
  </style>
</head>

<body>
{% for copia in copias %}
  <div class="page">
    <div class="copy-header">{{ copia }}</div>

    <div class="content">
      <table class="bill-container">
        <tr class="bill-emitter-row">
          <td>
            <div class="bill-type">{{ letra }}</div>
            <div class="text-md text-center">{{ emisor_razon_social_upper }}</div>
            <p><strong>Razón social:</strong> {{ emisor_razon_social_upper }}</p>
            <p><strong>Domicilio Comercial:</strong> {{ emisor_direccion }}</p>
            <p><strong>Condición Frente al IVA:</strong> {{ emisor_condicion_iva }}</p>
          </td>
          <td>
            <div class="fac-datos">
              {% if mostrar_cod_tipo %}
              <div class="cod-line">COD. {{ codigo_tipo }}</div>
              {% endif %}
              <div class="text-lg">{{ titulo }}</div>
              <div class="comp-row">
                <p><strong>Punto de Venta: {{ punto_venta_largo }}</strong></p>
                <p><strong>Comp. Nro: {{ numero_comprobante_largo }}</strong></p>
              </div>
              <p><strong>Fecha de Emisión:</strong> {{ fecha_emision }}</p>
              <p><strong>CUIT:</strong> {{ emisor_cuit }}</p>
              <p><strong>Ingresos Brutos:</strong> {{ emisor_ingresos_brutos }}</p>
              <p><strong>Fecha de Inicio de Actividades:</strong> {{ emisor_inicio_actividades }}</p>
            </div>
          </td>
        </tr>

        <tr class="bill-row compact">
          <td colspan="2">
            <div class="row">
              <p class="col-4 margin-b-0"><strong>Período Facturado Desde: {{ periodo_desde }}</strong></p>
              <p class="col-3 margin-b-0"><strong>Hasta: {{ periodo_hasta }}</strong></p>
              <p class="col-5 margin-b-0"><strong>Fecha de Vto. para el pago: {{ periodo_vto }}</strong></p>
            </div>
          </td>
        </tr>

        <tr class="bill-row compact">
          <td colspan="2">
            <div class="receptor-block">
              <div class="row">
                <p class="col-4 margin-b-0"><strong>CUIL/CUIT:</strong> {{ receptor_doc_nro }}</p>
                <p class="col-8 margin-b-0"><strong>Apellido y Nombre/Razón social:</strong> {{ receptor_razon_social }}</p>
              </div>
              <div class="row">
                <p class="col-6 margin-b-0"><strong>Condición Frente al IVA:</strong> {{ receptor_condicion_iva }}</p>
                <p class="col-6 margin-b-0"><strong>Domicilio:</strong> {{ receptor_direccion }}</p>
              </div>
              <p><strong>Condicion de venta:</strong> {{ condicion_venta }}</p>
              {% if comprobante_asociado %}
              <p><strong>Factura Asoc:</strong> {{ comprobante_asociado }}</p>
              {% endif %}
            </div>
          </td>
        </tr>

        <tr class="bill-row row-details">
          <td colspan="2">
            <div>
              <table class="items-table">
                {% if discrimina_iva %}
                <colgroup>
                  <col style="width:7%;">
                  <col style="width:29%;">
                  <col style="width:8%;">
                  <col style="width:9%;">
                  <col style="width:11%;">
                  <col style="width:8%;">
                  <col style="width:10%;">
                  <col style="width:8%;">
                  <col style="width:10%;">
                </colgroup>
                <thead>
                  <tr>
                    <th class="code">Código</th>
                    <th class="desc">Producto / Servicio</th>
                    <th class="qty">Cantidad</th>
                    <th class="unit">U. Medida</th>
                    <th class="price">Precio Unit.</th>
                    <th class="bonif">% Bonif.</th>
                    <th class="subtotal">SubTotal</th>
                    <th class="iva">Alícuota IVA</th>
                    <th class="subtotaliva">Subtotal c/IVA</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                  <tr>
                    <td class="code"></td>
                    <td class="item-descripcion desc">{{ it.descripcion }}</td>
                    <td class="qty">{{ it.cantidad }}</td>
                    <td class="unit">{{ it.unidad }}</td>
                    <td class="price">{{ it.precio_unitario }}</td>
                    <td class="bonif">{{ it.bonif_pct }}</td>
                    <td class="subtotal">{{ it.subtotal }}</td>
                    <td class="iva">{{ it.alicuota }}</td>
                    <td class="subtotaliva">{{ it.subtotal_con_iva }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
                {% else %}
                <colgroup>
                  <col style="width:8%;">
                  <col style="width:30%;">
                  <col style="width:10%;">
                  <col style="width:12%;">
                  <col style="width:14%;">
                  <col style="width:8%;">
                  <col style="width:8%;">
                  <col style="width:10%;">
                </colgroup>
                <thead>
                  <tr>
                    <th class="code">Código</th>
                    <th class="desc">Producto / Servicio</th>
                    <th class="qty">Cantidad</th>
                    <th class="unit">U. Medida</th>
                    <th class="price">Precio Unit.</th>
                    <th class="bonif">% Bonif.</th>
                    <th class="subtotal">Imp. Bonif.</th>
                    <th class="subtotaliva">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {% for it in items %}
                  <tr>
                    <td class="code"></td>
                    <td class="item-descripcion desc">{{ it.descripcion }}</td>
                    <td class="qty">{{ it.cantidad }}</td>
                    <td class="unit">{{ it.unidad }}</td>
                    <td class="price">{{ it.precio_unitario }}</td>
                    <td class="bonif">{{ it.bonif_pct }}</td>
                    <td class="subtotal">{{ it.imp_bonif }}</td>
                    <td class="subtotaliva">{{ it.subtotal }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
                {% endif %}
              </table>
            </div>
          </td>
        </tr>
      </table>
    </div>

    <div class="footer-block">
      <table class="bill-container">
        <tr class="bill-row total-row">
          <td colspan="2">
            <div>
              {% if discrimina_iva %}
                {% for row in totales_a %}
                <div class="row text-right">
                  <p class="col-10 margin-b-0"><strong>{{ row.label }}: $</strong></p>
                  <p class="col-2 margin-b-0 value-nowrap"><strong>{{ row.value }}</strong></p>
                </div>
                {% endfor %}
              {% else %}
                <div class="row text-right">
                  <p class="col-10 margin-b-0"><strong>Subtotal: $</strong></p>
                  <p class="col-2 margin-b-0 value-nowrap"><strong>{{ subtotal }}</strong></p>
                </div>
                <div class="row text-right">
                  <p class="col-10 margin-b-0"><strong>Importe Otros Tributos: $</strong></p>
                  <p class="col-2 margin-b-0 value-nowrap"><strong>{{ importe_otros_tributos }}</strong></p>
                </div>
                <div class="row text-right">
                  <p class="col-10 margin-b-0"><strong>Importe total: $</strong></p>
                  <p class="col-2 margin-b-0 value-nowrap"><strong>{{ importe_total }}</strong></p>
                </div>
              {% endif %}
            </div>
          </td>
        </tr>

        {% if mostrar_transparencia_fiscal %}
        <tr class="bill-row transparencia-row">
          <td colspan="2">
            <div class="transparencia-box">
              <div class="title">Régimen de Transparencia Fiscal al Consumidor (Ley 27.743)</div>
              <div class="iva-line">
                <span class="label">IVA Contenido: $</span>
                <span class="amount">{{ iva_contenido }}</span>
              </div>
            </div>
          </td>
        </tr>
        {% endif %}

        <tr class="bill-row row-details">
          <td colspan="2">
            <div class="footer-legal">
              <div class="left">
                {% if qr_image_url %}
                <img id="qrcode" src="{{ qr_image_url }}" alt="QR ARCA" />
                {% endif %}

                <div class="marca">
                  <svg width="200" height="80" viewBox="0 0 400 100" xmlns="http://www.w3.org/2000/svg">
                    <text x="0" y="55" font-weight="700" font-size="60" letter-spacing="3" fill="#3a3a3a">ARCA</text>
                    <text font-weight="400" font-size="14" letter-spacing="2.5" fill="#555">
                      <tspan x="0" y="75">AGENCIA DE RECAUDACIÓN</tspan>
                      <tspan x="0" y="90">Y CONTROL ADUANERO</tspan>
                    </text>
                  </svg>
                  <div class="legal-title">Comprobante Autorizado</div>
                  <div class="legal-note">Esta Agencia no se responsabiliza por los datos ingresados en el detalle de la operación</div>
                </div>
              </div>

              <div class="right">
                <div class="row text-right"><strong>CAE Nº:&nbsp;</strong>{{ cae }}</div>
                <div class="row text-right"><strong>Fecha de Vto. de CAE:&nbsp;</strong>{{ cae_vencimiento }}</div>
              </div>
            </div>
          </td>
        </tr>
      </table>
    </div>
  </div>

  {% if not loop.last %}
    <div class="page-break"></div>
  {% endif %}
{% endfor %}

</body>
</html>
"""


LETTER_BY_TIPO = {
    1: 'A', 2: 'A', 3: 'A',
    6: 'B', 7: 'B', 8: 'B',
    11: 'C', 12: 'C', 13: 'C',
    51: 'M', 52: 'M', 53: 'M',
}


def render_comprobante_html(factura):
    context = _build_context(factura)
    return render_template_string(COMPROBANTE_TEMPLATE, **context)


def _build_context(factura):
    tipo = int(factura.tipo_comprobante)
    letra = LETTER_BY_TIPO.get(tipo, '')
    discrimina_iva = tipo in {1, 2, 3, 51, 52, 53}
    is_nota_credito = tipo in {3, 8, 13, 53}

    numero = int(factura.numero_comprobante or 0)
    punto_venta = int(factura.punto_venta or 0)

    title_base = 'FACTURA'
    if is_nota_credito:
        title_base = 'NOTA DE CREDITO'
    elif tipo in {2, 7, 12, 52}:
        title_base = 'NOTA DE DEBITO'

    items = _build_items_rows(factura)
    iva_totals = _build_iva_totals(factura)
    totales_a = [
        {'label': 'Importe Neto Gravado', 'value': _money(factura.importe_neto)},
        {'label': 'IVA 27%', 'value': _money(iva_totals[27])},
        {'label': 'IVA 21%', 'value': _money(iva_totals[21])},
        {'label': 'IVA 10.5%', 'value': _money(iva_totals[10.5])},
        {'label': 'IVA 5%', 'value': _money(iva_totals[5])},
        {'label': 'IVA 2.5%', 'value': _money(iva_totals[2.5])},
        {'label': 'IVA 0%', 'value': _money(iva_totals[0])},
        {'label': 'Importe Otros Tributos', 'value': _money(Decimal('0'))},
        {'label': 'Importe total', 'value': _money(factura.importe_total)},
    ]

    qr_image_url = _build_qr_image_url(factura)

    comprobante_asociado = None
    if factura.cbte_asoc_tipo and factura.cbte_asoc_pto_vta and factura.cbte_asoc_nro:
        comprobante_asociado = _format_comp(
            factura.cbte_asoc_pto_vta,
            factura.cbte_asoc_nro,
            factura.cbte_asoc_tipo,
        )

    emisor_razon_social = (factura.facturador.razon_social if factura.facturador else '')
    emisor_razon_social_upper = emisor_razon_social.upper() if emisor_razon_social else ''

    condicion_venta = 'Cuenta Corriente'
    if tipo in {6, 8, 11, 12, 13}:
        condicion_venta = 'Otros medios de pago electrónico'

    iva_contenido = Decimal(str(factura.importe_iva or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'copias': ['ORIGINAL', 'DUPLICADO', 'TRIPLICADO'],
        'titulo': title_base,
        'letra': letra,
        'discrimina_iva': discrimina_iva,
        'is_nota_credito': is_nota_credito,
        'mostrar_cod_tipo': False,
        'codigo_tipo': f'{tipo:03d}',
        'punto_venta_largo': f'{punto_venta:05d}',
        'numero_comprobante_largo': f'{numero:08d}',
        'fecha_emision': _date(factura.fecha_emision),
        'periodo_desde': _date(factura.fecha_desde or factura.fecha_emision),
        'periodo_hasta': _date(factura.fecha_hasta or factura.fecha_emision),
        'periodo_vto': _date(factura.fecha_vto_pago or factura.fecha_emision),
        'emisor_razon_social': emisor_razon_social,
        'emisor_razon_social_upper': emisor_razon_social_upper,
        'emisor_direccion': (factura.facturador.direccion if factura.facturador and factura.facturador.direccion else '-'),
        'emisor_condicion_iva': (factura.facturador.condicion_iva if factura.facturador and factura.facturador.condicion_iva else '-'),
        'emisor_cuit': (factura.facturador.cuit if factura.facturador else ''),
        'emisor_ingresos_brutos': 'NO OBLIGADO A INSCRIBIRSE',
        'emisor_inicio_actividades': '-',
        'receptor_doc_nro': (factura.receptor.doc_nro if factura.receptor else ''),
        'receptor_razon_social': (factura.receptor.razon_social if factura.receptor else ''),
        'receptor_condicion_iva': (factura.receptor.condicion_iva if factura.receptor and factura.receptor.condicion_iva else '-'),
        'receptor_direccion': (factura.receptor.direccion if factura.receptor and factura.receptor.direccion else '-'),
        'condicion_venta': condicion_venta,
        'comprobante_asociado': comprobante_asociado,
        'items': items,
        'totales_a': totales_a,
        'mostrar_transparencia_fiscal': (not discrimina_iva) and iva_contenido > 0,
        'subtotal': _money(factura.importe_neto),
        'importe_otros_tributos': _money(Decimal('0')),
        'importe_total': _money(factura.importe_total),
        'iva_contenido': _money(iva_contenido),
        'cae': factura.cae or '-',
        'cae_vencimiento': _date(factura.cae_vencimiento),
        'qr_image_url': qr_image_url,
    }


def _build_items_rows(factura):
    rows = []
    if factura.items:
        for item in factura.items:
            subtotal = Decimal(str(item.subtotal or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            alicuota = _alicuota_from_id(item.alicuota_iva_id)
            iva_item = Decimal(str(item.importe_iva or 0))
            if iva_item == 0 and alicuota > 0:
                iva_item = (subtotal * Decimal(str(alicuota)) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            row = {
                'descripcion': item.descripcion or '',
                'cantidad': _qty(item.cantidad),
                'unidad': 'Unidad',
                'precio_unitario': _money(item.precio_unitario),
                'bonif_pct': _qty(Decimal('0')),
                'imp_bonif': _money(Decimal('0')),
                'subtotal': _money(subtotal),
                'alicuota': _percent(alicuota),
                'subtotal_con_iva': _money(subtotal + iva_item),
            }
            rows.append(row)

    if not rows:
        subtotal = Decimal(str(factura.importe_neto or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        iva_total = Decimal(str(factura.importe_iva or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        alicuota = Decimal('21') if iva_total > 0 else Decimal('0')
        rows.append({
            'descripcion': 'Concepto',
            'cantidad': _qty(Decimal('1')),
            'unidad': 'Unidad',
            'precio_unitario': _money(subtotal),
            'bonif_pct': _qty(Decimal('0')),
            'imp_bonif': _money(Decimal('0')),
            'subtotal': _money(subtotal),
            'alicuota': _percent(alicuota),
            'subtotal_con_iva': _money(subtotal + iva_total),
        })

    return rows


def _build_iva_totals(factura):
    buckets = {27: Decimal('0'), 21: Decimal('0'), 10.5: Decimal('0'), 5: Decimal('0'), 2.5: Decimal('0'), 0: Decimal('0')}
    from_items = False

    for item in factura.items:
        from_items = True
        alicuota = float(_alicuota_from_id(item.alicuota_iva_id))
        subtotal = Decimal(str(item.subtotal or 0))
        iva_item = Decimal(str(item.importe_iva or 0))
        if iva_item == 0 and alicuota > 0:
            iva_item = (subtotal * Decimal(str(alicuota)) / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        key = _normalize_aliq_key(alicuota)
        if key in buckets:
            buckets[key] += iva_item

    if not from_items:
        iva_total = Decimal(str(factura.importe_iva or 0))
        if iva_total > 0:
            buckets[21] = iva_total

    return buckets


def _build_qr_image_url(factura):
    try:
        if not factura.facturador:
            return None

        cod_aut = int(factura.cae) if factura.cae and str(factura.cae).isdigit() else 0
        receptor_doc = ''.join(ch for ch in str(factura.receptor.doc_nro if factura.receptor else '') if ch.isdigit())
        receptor_doc_nro = int(receptor_doc) if receptor_doc else 0

        payload = {
            'ver': 1,
            'fecha': (factura.fecha_emision or date.today()).isoformat(),
            'cuit': int(factura.facturador.cuit),
            'ptoVta': int(factura.punto_venta or 0),
            'tipoCmp': int(factura.tipo_comprobante or 0),
            'nroCmp': int(factura.numero_comprobante or 0),
            'importe': float(Decimal(str(factura.importe_total or 0)).quantize(Decimal('0.01'))),
            'moneda': factura.moneda or 'PES',
            'ctz': float(Decimal(str(factura.cotizacion or 1)).quantize(Decimal('0.000001'))),
            'tipoDocRec': int(factura.receptor.doc_tipo if factura.receptor else 99),
            'nroDocRec': receptor_doc_nro,
            'tipoCodAut': 'E',
            'codAut': cod_aut,
        }

        raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        b64 = base64.b64encode(raw).decode('ascii')
        qr_url = f'https://www.arca.gob.ar/fe/qr/?p={b64}'
        return f'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote_plus(qr_url)}'
    except Exception:
        return None


def _alicuota_from_id(alicuota_id):
    if alicuota_id in ALICUOTAS_IVA:
        return Decimal(str(ALICUOTAS_IVA[alicuota_id]['porcentaje']))
    return Decimal('21')


def _normalize_aliq_key(value):
    if abs(value - 10.5) < 0.0001:
        return 10.5
    if abs(value - 2.5) < 0.0001:
        return 2.5
    if value in (0, 5, 21, 27):
        return int(value)
    return int(round(value))


def _money(value):
    dec = Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{dec:.2f}'.replace('.', ',')


def _qty(value):
    dec = Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{dec:.2f}'.replace('.', ',')


def _percent(value):
    dec = Decimal(str(value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'{dec:.2f}'.replace('.', ',') + '%'


def _date(value):
    if not value:
        return '-'
    if isinstance(value, str):
        return value
    return value.strftime('%d/%m/%Y')


def _format_comp(punto_venta, numero, tipo):
    return str(int(numero))
