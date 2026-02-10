from datetime import datetime, timedelta
from flask import Blueprint, g, jsonify
from sqlalchemy import func
from ..extensions import db
from ..models import Factura
from ..utils import tenant_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@tenant_required
def get_stats():
    """Obtener estadísticas del dashboard."""

    # Inicio del mes actual
    today = datetime.utcnow().date()
    first_day_of_month = today.replace(day=1)

    # Total de facturas del mes
    facturas_mes = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.fecha_emision >= first_day_of_month
    ).count()

    # Facturas autorizadas
    facturas_autorizadas = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.fecha_emision >= first_day_of_month,
        Factura.estado == 'autorizado'
    ).count()

    # Facturas con error
    facturas_error = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.fecha_emision >= first_day_of_month,
        Factura.estado == 'error'
    ).count()

    # Facturas pendientes
    facturas_pendientes = Factura.query.filter(
        Factura.tenant_id == g.tenant_id,
        Factura.estado.in_(['borrador', 'pendiente'])
    ).count()

    # Total facturado del mes
    total_mes = db.session.query(func.sum(Factura.importe_total)).filter(
        Factura.tenant_id == g.tenant_id,
        Factura.fecha_emision >= first_day_of_month,
        Factura.estado == 'autorizado'
    ).scalar() or 0

    return jsonify({
        'facturas_mes': facturas_mes,
        'autorizadas': facturas_autorizadas,
        'errores': facturas_error,
        'pendientes': facturas_pendientes,
        'total_mes': float(total_mes)
    }), 200
