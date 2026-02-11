import logging
from datetime import datetime
from celery import shared_task
from ..extensions import db
from ..models import Factura, EmailConfig

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def enviar_factura_email(self, factura_id: str):
    """Envía el comprobante PDF por email al receptor de forma async."""
    factura = Factura.query.get(factura_id)
    if not factura:
        logger.error(f'Factura {factura_id} no encontrada para envío de email')
        return {'error': 'Factura no encontrada'}

    if factura.estado != 'autorizado':
        logger.info(f'Factura {factura_id} no autorizada, omitiendo email')
        return {'skipped': True, 'reason': 'No autorizada'}

    # Evitar reenvíos duplicados por retries en cola
    if factura.email_enviado:
        logger.info(f'Factura {factura_id} ya tiene email enviado, omitiendo')
        return {'skipped': True, 'reason': 'Ya enviado'}

    if not factura.receptor or not factura.receptor.email:
        logger.info(f'Factura {factura_id} sin email de receptor, omitiendo')
        return {'skipped': True, 'reason': 'Sin email de receptor'}

    # Verificar que el tenant tiene email configurado y habilitado
    config = EmailConfig.query.filter_by(
        tenant_id=factura.tenant_id,
        email_habilitado=True,
    ).first()

    if not config:
        logger.info(f'Tenant {factura.tenant_id} sin config de email habilitada')
        return {'skipped': True, 'reason': 'Sin config de email'}

    try:
        from ..services.email_service import send_comprobante_email
        send_comprobante_email(factura)

        factura.email_enviado = True
        factura.email_enviado_at = datetime.utcnow()
        factura.email_error = None
        db.session.commit()

        logger.info(f'Email enviado para factura {factura_id} a {factura.receptor.email}')
        return {'success': True, 'email': factura.receptor.email}

    except Exception as e:
        logger.error(f'Error enviando email para factura {factura_id}: {str(e)}')
        factura.email_error = str(e)[:500]
        db.session.commit()

        # Retry en errores de conexión SMTP
        if _is_retryable(e):
            try:
                self.retry(exc=e)
            except self.MaxRetriesExceededError:
                logger.error(f'Max retries alcanzados para factura {factura_id}')
                return {'error': str(e), 'retries_exhausted': True}

        return {'error': str(e)}


def _is_retryable(exc):
    """Determina si un error SMTP es retryable."""
    import smtplib
    # Errores permanentes que NO deben reintentarse
    permanent_types = (
        smtplib.SMTPRecipientsRefused,
        smtplib.SMTPSenderRefused,
        smtplib.SMTPDataError,
        smtplib.SMTPAuthenticationError,
    )
    if isinstance(exc, permanent_types):
        return False
    # Errores transitorios de conexión
    retryable_types = (
        smtplib.SMTPConnectError,
        smtplib.SMTPServerDisconnected,
        ConnectionRefusedError,
        TimeoutError,
    )
    return isinstance(exc, retryable_types)
