from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from time import sleep
from celery import shared_task
from ..extensions import db
from ..models import Lote, Factura, Facturador
from ..services.comprobante_rules import (
    es_comprobante_tipo_c,
    normalizar_importes_para_tipo_c,
)
from ..services.encryption import decrypt_certificate
from arca_integration.constants import ALICUOTAS_IVA, CONDICIONES_IVA


@shared_task(bind=True)
def procesar_lote(self, lote_id: str):
    """
    Procesa todas las facturas pendientes de un lote.
    Actualiza el progreso en Celery para polling desde el frontend.
    """
    from arca_integration import ArcaClient
    from arca_integration.builders import FacturaBuilder

    lote = Lote.query.get(lote_id)
    if not lote:
        return {'error': 'Lote no encontrado'}

    # Obtener facturas pendientes
    facturas = Factura.query.filter_by(
        lote_id=lote_id,
        estado='pendiente'
    ).all()

    total = len(facturas)
    processed = 0
    ok = 0
    errors = 0

    # Agrupar facturas por facturador para reutilizar conexión
    facturas_por_facturador = {}
    for factura in facturas:
        if factura.facturador_id not in facturas_por_facturador:
            facturas_por_facturador[factura.facturador_id] = []
        facturas_por_facturador[factura.facturador_id].append(factura)

    for facturador_id, facturas_grupo in facturas_por_facturador.items():
        facturador = Facturador.query.get(facturador_id)

        if not facturador or not facturador.cert_encrypted:
            # Marcar todas las facturas de este facturador como error
            for factura in facturas_grupo:
                factura.estado = 'error'
                factura.error_mensaje = 'Facturador sin certificados'
                errors += 1
                processed += 1
                self.update_state(state='PROGRESS', meta={
                    'current': processed,
                    'total': total,
                    'percent': int((processed / total) * 100)
                })
            continue

        try:
            # Desencriptar certificados
            cert = decrypt_certificate(facturador.cert_encrypted)
            key = decrypt_certificate(facturador.key_encrypted)

            # Crear cliente ARCA
            client = ArcaClient(
                cuit=facturador.cuit,
                cert=cert,
                key=key,
                ambiente=facturador.ambiente
            )

            # Procesar cada factura
            for factura in facturas_grupo:
                try:
                    result = procesar_factura(client, factura, facturador)

                    if _is_retryable_wsaa_error(result):
                        sleep(5)
                        result = procesar_factura(client, factura, facturador)

                    if result.get('success'):
                        factura.estado = 'autorizado'
                        factura.cae = result['cae']
                        factura.cae_vencimiento = result['cae_vencimiento']
                        factura.numero_comprobante = result['numero_comprobante']
                        factura.arca_response = result.get('response')
                        ok += 1

                        # Enviar email automáticamente si el receptor tiene email
                        if factura.receptor and factura.receptor.email:
                            from .email import enviar_factura_email
                            enviar_factura_email.delay(str(factura.id))
                    else:
                        factura.estado = 'error'
                        factura.error_codigo = result.get('error_code')
                        factura.error_mensaje = result.get('error_message')
                        factura.arca_response = result.get('response')
                        errors += 1

                except Exception as e:
                    factura.estado = 'error'
                    factura.error_mensaje = str(e)
                    errors += 1

                processed += 1
                db.session.commit()

                # Actualizar progreso
                self.update_state(state='PROGRESS', meta={
                    'current': processed,
                    'total': total,
                    'percent': int((processed / total) * 100)
                })

        except Exception as e:
            # Error de conexión general
            for factura in facturas_grupo:
                factura.estado = 'error'
                factura.error_mensaje = f'Error de conexión: {str(e)}'
                errors += 1
                processed += 1
            db.session.commit()

    # Actualizar lote
    lote.estado = 'completado'
    lote.facturas_ok = ok
    lote.facturas_error = errors
    lote.processed_at = datetime.utcnow()
    db.session.commit()

    return {
        'status': 'completed',
        'processed': processed,
        'total': total,
        'ok': ok,
        'errors': errors
    }


def procesar_factura(client, factura: Factura, facturador: Facturador) -> dict:
    """Procesa una factura individual con ARCA."""
    from arca_integration.builders import FacturaBuilder
    from arca_integration.services import WSFEService

    try:
        # Obtener último número de comprobante
        ultimo = client.fe_comp_ultimo_autorizado(
            punto_venta=factura.punto_venta,
            tipo_cbte=factura.tipo_comprobante
        )
        numero_comprobante = ultimo + 1

        # Construir request de factura
        builder = FacturaBuilder()
        builder.set_comprobante(
            tipo=factura.tipo_comprobante,
            punto_venta=factura.punto_venta,
            numero=numero_comprobante,
            concepto=factura.concepto
        )
        builder.set_fechas(
            emision=factura.fecha_emision,
            desde=factura.fecha_desde,
            hasta=factura.fecha_hasta,
            vto_pago=factura.fecha_vto_pago
        )
        builder.set_receptor(
            doc_tipo=factura.receptor.doc_tipo,
            doc_nro=factura.receptor.doc_nro
        )

        _autocompletar_condicion_iva_receptor(client, factura)
        condicion_iva_receptor_id = _resolve_condicion_iva_receptor_id(factura)
        if condicion_iva_receptor_id is None:
            raise ValueError(
                f'No se pudo determinar la condicion IVA del receptor {factura.receptor.doc_nro}. '
                'Completa la condicion IVA del receptor desde el modulo Receptores.'
            )

        builder.set_condicion_iva_receptor(condicion_iva_receptor_id)
        importe_neto, importe_iva, importe_total = normalizar_importes_para_tipo_c(
            factura.tipo_comprobante,
            factura.importe_neto,
            factura.importe_iva,
            factura.importe_total,
        )

        factura.importe_neto = importe_neto
        factura.importe_iva = importe_iva
        factura.importe_total = importe_total

        builder.set_importes(
            total=float(importe_total),
            neto=float(importe_neto),
            iva=float(importe_iva),
        )
        builder.set_moneda(
            moneda=factura.moneda,
            cotizacion=float(factura.cotizacion or 1)
        )

        # Agregar comprobante asociado si existe
        if factura.cbte_asoc_tipo:
            builder.set_comprobante_asociado(
                tipo=factura.cbte_asoc_tipo,
                punto_venta=factura.cbte_asoc_pto_vta,
                numero=factura.cbte_asoc_nro
            )

        # Agregar IVA (soporta múltiples alícuotas por item)
        if (
            not es_comprobante_tipo_c(factura.tipo_comprobante)
            and factura.importe_iva
            and float(factura.importe_iva) > 0
        ):
            iva_items = _build_iva_from_items(factura)

            if iva_items:
                for iva_item in iva_items:
                    builder.add_iva(
                        alicuota_id=iva_item['Id'],
                        base_imponible=iva_item['BaseImp'],
                        importe=iva_item['Importe'],
                    )
            else:
                # Fallback para facturas sin items detallados
                builder.add_iva(
                    alicuota_id=5,
                    base_imponible=float(factura.importe_neto),
                    importe=float(factura.importe_iva)
                )

        request_data = builder.build()

        # Guardar request
        factura.arca_request = request_data

        # Enviar a ARCA
        wsfe = WSFEService(client)
        response = wsfe.autorizar(request_data)

        if response.get('cae'):
            return {
                'success': True,
                'cae': response['cae'],
                'cae_vencimiento': response['cae_vencimiento'],
                'numero_comprobante': numero_comprobante,
                'response': response
            }
        else:
            return {
                'success': False,
                'error_code': response.get('error_code'),
                'error_message': response.get('error_message', 'Error desconocido'),
                'response': response
            }

    except Exception as e:
        return {
            'success': False,
            'error_message': str(e)
        }


def _is_retryable_wsaa_error(result: dict) -> bool:
    if not isinstance(result, dict) or result.get('success'):
        return False

    message = (result.get('error_message') or '').lower()
    retryable_fragments = [
        'ya posee un ta valido para el acceso al wsn solicitado',
        'ya posee un ta valido',
    ]
    return any(fragment in message for fragment in retryable_fragments)


def _build_iva_from_items(factura: Factura) -> list[dict]:
    """Construye detalle de IVA agrupado por alícuota a partir de items."""
    if not factura.items:
        return []

    bases_por_alicuota: dict[int, Decimal] = {}

    for item in factura.items:
        alicuota_id = item.alicuota_iva_id or 5
        if alicuota_id not in ALICUOTAS_IVA:
            continue

        base = Decimal(str(item.subtotal))
        bases_por_alicuota[alicuota_id] = bases_por_alicuota.get(alicuota_id, Decimal('0')) + base

    if not bases_por_alicuota:
        return []

    iva_result = []
    total_calculado = Decimal('0')

    for alicuota_id in sorted(bases_por_alicuota.keys()):
        base = bases_por_alicuota[alicuota_id].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        porcentaje = Decimal(str(ALICUOTAS_IVA[alicuota_id]['porcentaje']))
        importe = (base * porcentaje / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_calculado += importe

        iva_result.append({
            'Id': alicuota_id,
            'BaseImp': float(base),
            'Importe': float(importe),
        })

    # Ajuste de redondeo para alinear con el total de IVA informado en factura
    total_factura = Decimal(str(factura.importe_iva or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    diff = (total_factura - total_calculado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if diff != Decimal('0') and iva_result:
        iva_result[-1]['Importe'] = float((Decimal(str(iva_result[-1]['Importe'])) + diff).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    return iva_result


def _resolve_condicion_iva_receptor_id(factura: Factura) -> int | None:
    """Resuelve CondicionIVAReceptorId para WSFE (RG 5616)."""
    receptor = factura.receptor
    if not receptor:
        return None

    raw = (receptor.condicion_iva or '').strip()
    if raw:
        if raw.isdigit():
            cond_id = int(raw)
            if cond_id in CONDICIONES_IVA:
                return cond_id

        normalized = _normalize_text(raw)
        for cond_id, desc in CONDICIONES_IVA.items():
            if _normalize_text(desc) == normalized:
                return cond_id

    # Fallback por tipo de documento
    if receptor.doc_tipo in (96, 99):
        return 5  # Consumidor Final

    if receptor.doc_tipo in (80, 86, 87):
        # Para CUIT/CUIL/CDI no inferir por defecto: evitar rechazos por inconsistencia
        return None

    return 5


def _normalize_text(value: str) -> str:
    return ' '.join(value.lower().replace('–', '-').split())


def _autocompletar_condicion_iva_receptor(client, factura: Factura) -> None:
    """Intenta completar condicion_iva del receptor desde padrón ARCA."""
    receptor = factura.receptor
    if not receptor:
        return

    if receptor.condicion_iva and _resolve_condicion_iva_receptor_id(factura) is not None:
        return

    if receptor.doc_tipo not in (80, 86, 87):
        return

    doc = (receptor.doc_nro or '').replace('-', '').replace(' ', '')
    if not doc.isdigit() or len(doc) != 11:
        return

    try:
        result = client.consultar_padron(doc)
        if not result.get('success'):
            return

        data = result.get('data') or {}
        condicion_iva = data.get('condicion_iva')
        if condicion_iva:
            receptor.condicion_iva = condicion_iva

        if data.get('razon_social') and (
            not receptor.razon_social or receptor.razon_social.startswith('CUIT ')
        ):
            receptor.razon_social = data['razon_social']

        if data.get('direccion') and not receptor.direccion:
            receptor.direccion = data['direccion']

        db.session.flush()
    except Exception:
        # Si padrón falla, dejamos que siga y valide con lo que tenga el receptor
        pass
