from datetime import datetime, date
from decimal import Decimal

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models import Factura, Receptor
from ..utils import permission_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@permission_required('dashboard:ver')
def get_stats():
    month_param = (request.args.get('month') or '').strip()
    historico = (request.args.get('historico', 'false') or '').lower() == 'true'

    today = datetime.utcnow().date()
    selected_month = _parse_month(month_param) if month_param else today.replace(day=1)

    period_start = None if historico else selected_month
    period_end = None if historico else _next_month(selected_month)

    base_query = Factura.query.filter(Factura.tenant_id == g.tenant_id)
    period_query = _apply_period_filter(base_query, period_start, period_end)

    facturas_mes = period_query.count()
    facturas_autorizadas = period_query.filter(Factura.estado == 'autorizado').count()
    facturas_error = period_query.filter(Factura.estado == 'error').count()
    facturas_pendientes = period_query.filter(Factura.estado.in_(['borrador', 'pendiente'])).count()

    total_mes = period_query.with_entities(func.sum(Factura.importe_total)).filter(
        Factura.estado == 'autorizado'
    ).scalar() or Decimal('0')

    ticket_promedio = _build_ticket_promedio(
        tenant_id=g.tenant_id,
        period_start=period_start,
        period_end=period_end,
        historico=historico,
    )

    return jsonify({
        'facturas_mes': facturas_mes,
        'autorizadas': facturas_autorizadas,
        'errores': facturas_error,
        'pendientes': facturas_pendientes,
        'total_mes': float(total_mes),
        'facturacion_12_meses': _build_facturacion_12_meses(g.tenant_id, selected_month),
        'top_clientes': _build_top_clientes(g.tenant_id, period_start, period_end),
        'ticket_promedio': ticket_promedio,
        'filtros_aplicados': {
            'historico': historico,
            'month': selected_month.strftime('%Y-%m'),
        },
    }), 200


def _parse_month(value: str) -> date:
    try:
        return datetime.strptime(value, '%Y-%m').date().replace(day=1)
    except ValueError:
        return datetime.utcnow().date().replace(day=1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _apply_period_filter(query, period_start: date | None, period_end: date | None):
    if period_start is not None:
        query = query.filter(Factura.fecha_emision >= period_start)
    if period_end is not None:
        query = query.filter(Factura.fecha_emision < period_end)
    return query


def _month_key(year: int, month: int) -> str:
    return f'{year:04d}-{month:02d}'


def _month_label(value: date) -> str:
    months = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    return f'{months[value.month - 1]} {value.year}'


def _sub_months(value: date, count: int) -> date:
    idx = (value.year * 12 + (value.month - 1)) - count
    year = idx // 12
    month = idx % 12 + 1
    return date(year, month, 1)


def _build_facturacion_12_meses(tenant_id, selected_month: date):
    start_month = _sub_months(selected_month, 11)
    end_month = _next_month(selected_month)

    rows = db.session.query(
        func.extract('year', Factura.fecha_emision).label('year'),
        func.extract('month', Factura.fecha_emision).label('month'),
        func.count(Factura.id).label('cantidad'),
        func.coalesce(func.sum(Factura.importe_total), 0).label('total'),
    ).filter(
        Factura.tenant_id == tenant_id,
        Factura.estado == 'autorizado',
        Factura.fecha_emision >= start_month,
        Factura.fecha_emision < end_month,
    ).group_by('year', 'month').all()

    by_month = {
        _month_key(int(row.year), int(row.month)): {
            'cantidad': int(row.cantidad or 0),
            'total': float(row.total or 0),
        }
        for row in rows
    }

    serie = []
    for idx in range(12):
        month_date = _sub_months(selected_month, 11 - idx)
        key = month_date.strftime('%Y-%m')
        values = by_month.get(key, {'cantidad': 0, 'total': 0.0})
        serie.append({
            'month': key,
            'label': _month_label(month_date),
            'cantidad': values['cantidad'],
            'total': values['total'],
        })

    return serie


def _build_top_clientes(tenant_id, period_start: date | None, period_end: date | None):
    top_query = db.session.query(
        Factura.receptor_id,
        Receptor.razon_social,
        Receptor.doc_nro,
        func.count(Factura.id).label('cantidad'),
        func.coalesce(func.sum(Factura.importe_total), 0).label('total'),
    ).join(
        Receptor,
        Receptor.id == Factura.receptor_id,
    ).filter(
        Factura.tenant_id == tenant_id,
        Factura.estado == 'autorizado',
    )

    top_query = _apply_period_filter(top_query, period_start, period_end)

    rows = top_query.group_by(
        Factura.receptor_id,
        Receptor.razon_social,
        Receptor.doc_nro,
    ).order_by(
        func.sum(Factura.importe_total).desc(),
        func.count(Factura.id).desc(),
    ).limit(10).all()

    total_periodo = db.session.query(
        func.coalesce(func.sum(Factura.importe_total), 0)
    ).filter(
        Factura.tenant_id == tenant_id,
        Factura.estado == 'autorizado',
    )
    total_periodo = _apply_period_filter(total_periodo, period_start, period_end).scalar() or Decimal('0')

    result = []
    for row in rows:
        total_cliente = row.total or Decimal('0')
        porcentaje = float((total_cliente / total_periodo) * Decimal('100')) if total_periodo > 0 else 0.0
        result.append({
            'receptor_id': str(row.receptor_id),
            'razon_social': row.razon_social,
            'doc_nro': row.doc_nro,
            'cantidad': int(row.cantidad or 0),
            'total': float(total_cliente),
            'porcentaje': round(porcentaje, 2),
        })

    return result


def _ticket_value(tenant_id, period_start: date | None, period_end: date | None):
    query = db.session.query(
        func.coalesce(func.sum(Factura.importe_total), 0).label('total'),
        func.count(Factura.id).label('cantidad'),
    ).filter(
        Factura.tenant_id == tenant_id,
        Factura.estado == 'autorizado',
    )

    row = _apply_period_filter(query, period_start, period_end).first()
    total = row.total or Decimal('0')
    cantidad = int(row.cantidad or 0)
    valor = (total / cantidad) if cantidad else Decimal('0')
    return valor, total, cantidad


def _build_ticket_promedio(tenant_id, period_start: date | None, period_end: date | None, historico: bool):
    actual, actual_total, actual_cantidad = _ticket_value(tenant_id, period_start, period_end)
    variacion_pct = None
    anterior_valor = None

    if not historico and period_start is not None:
        previous_start = _sub_months(period_start, 1)
        previous_end = period_start
        anterior, _, _ = _ticket_value(tenant_id, previous_start, previous_end)
        anterior_valor = float(anterior)
        if anterior > 0:
            variacion_pct = float(((actual - anterior) / anterior) * Decimal('100'))

    return {
        'valor': float(actual),
        'total': float(actual_total),
        'cantidad': actual_cantidad,
        'variacion_pct': round(variacion_pct, 2) if variacion_pct is not None else None,
        'valor_periodo_anterior': anterior_valor,
    }
