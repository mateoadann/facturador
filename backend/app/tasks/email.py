import logging
import smtplib
from datetime import datetime
from celery import shared_task
from ..extensions import db
from ..models import Factura, EmailConfig

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def enviar_factura_email(self, factura_id: str, tenant_id: str):
    """Envía el comprobante PDF por email al receptor de forma async."""
    factura = Factura.query.filter_by(id=factura_id, tenant_id=tenant_id).first()
    if not factura:
        logger.error(f'Factura {factura_id} no encontrada para envío de email')
        return {'error': 'Factura no encontrada'}

    if factura.estado != 'autorizado':
        logger.info(f'Factura {factura_id} no autorizada, omitiendo email')
        return {'skipped': True, 'reason': 'No autorizada'}

    try:
        return _enviar_factura_email_sync(factura, allow_resend=False, raise_on_error=True)

    except (
        smtplib.SMTPException,
        ConnectionError,
        ConnectionRefusedError,
        TimeoutError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        error_data = _normalize_email_error(exc)
        logger.error(f'Error enviando email para factura {factura_id}: {error_data["message"]}')
        factura.email_error = error_data['message']
        db.session.commit()

        # Retry en errores de conexión SMTP
        if error_data['retryable']:
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                logger.error(f'Max retries alcanzados para factura {factura_id}')
                return {
                    'error': error_data['message'],
                    'error_code': error_data['code'],
                    'retries_exhausted': True,
                }

        return {
            'error': error_data['message'],
            'error_code': error_data['code'],
        }


@shared_task(bind=True)
def enviar_emails_lote(self, lote_id: str, tenant_id: str, mode: str = 'no_enviados'):
    """Envía emails de un lote completo con progreso y resumen."""
    if mode not in ['todos', 'no_enviados']:
        return {'error': 'Modo de envio invalido'}

    query = Factura.query.filter(
        Factura.tenant_id == tenant_id,
        Factura.lote_id == lote_id,
        Factura.estado == 'autorizado',
    )

    if mode == 'no_enviados':
        query = query.filter(Factura.email_enviado.is_(False))

    facturas = query.all()
    total = len(facturas)
    processed = 0
    sent = 0
    skipped = 0
    errors = 0

    if total == 0:
        return {
            'status': 'completed',
            'processed': 0,
            'total': 0,
            'sent': 0,
            'skipped': 0,
            'errors': 0,
        }

    for factura in facturas:
        result = _enviar_factura_email_sync(
            factura,
            allow_resend=(mode == 'todos'),
            raise_on_error=False,
        )

        if result.get('success'):
            sent += 1
        elif result.get('skipped'):
            skipped += 1
        else:
            errors += 1

        processed += 1
        self.update_state(state='PROGRESS', meta={
            'current': processed,
            'total': total,
            'percent': int((processed / total) * 100),
        })

    return {
        'status': 'completed',
        'processed': processed,
        'total': total,
        'sent': sent,
        'skipped': skipped,
        'errors': errors,
        'mode': mode,
    }


def _enviar_factura_email_sync(factura, allow_resend=False, raise_on_error=False):
    if factura.email_enviado and not allow_resend:
        logger.info(f'Factura {factura.id} ya tiene email enviado, omitiendo')
        return {'skipped': True, 'reason': 'Ya enviado'}

    if not factura.receptor or not factura.receptor.email:
        logger.info(f'Factura {factura.id} sin email de receptor, omitiendo')
        return {'skipped': True, 'reason': 'Sin email de receptor'}

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

        logger.info(f'Email enviado para factura {factura.id} a {factura.receptor.email}')
        return {'success': True, 'email': factura.receptor.email}
    except (
        smtplib.SMTPException,
        ConnectionError,
        ConnectionRefusedError,
        TimeoutError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        error_data = _normalize_email_error(exc)
        logger.error(f'Error enviando email para factura {factura.id}: {error_data["message"]}')
        factura.email_error = error_data['message']
        db.session.commit()
        if raise_on_error:
            raise
        return {
            'error': error_data['message'],
            'error_code': error_data['code'],
        }


def _is_retryable(exc):
    """Determina si un error SMTP es retryable."""
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


def _normalize_email_error(exc):
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return {
            'code': 'smtp_auth_error',
            'message': 'Error de autenticacion SMTP. Revisa usuario, password y servidor.',
            'retryable': False,
        }

    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return {
            'code': 'smtp_recipient_refused',
            'message': 'El servidor SMTP rechazo el destinatario del email.',
            'retryable': False,
        }

    if isinstance(exc, smtplib.SMTPSenderRefused):
        return {
            'code': 'smtp_sender_refused',
            'message': 'El servidor SMTP rechazo el remitente configurado.',
            'retryable': False,
        }

    if isinstance(exc, smtplib.SMTPDataError):
        return {
            'code': 'smtp_data_error',
            'message': 'El servidor SMTP rechazo el contenido del mensaje.',
            'retryable': False,
        }

    if _is_retryable(exc):
        return {
            'code': 'smtp_connection_error',
            'message': 'No se pudo conectar al servidor SMTP. Reintentando.',
            'retryable': True,
        }

    if isinstance(exc, (RuntimeError, ValueError)):
        return {
            'code': 'email_service_error',
            'message': 'Error al preparar o enviar el comprobante por email.',
            'retryable': False,
        }

    return {
        'code': 'email_unknown_error',
        'message': 'Error inesperado al enviar email.',
        'retryable': False,
    }
