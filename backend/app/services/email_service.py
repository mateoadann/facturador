import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from .encryption import decrypt_certificate

logger = logging.getLogger(__name__)


def get_smtp_connection(config):
    """Crea conexión SMTP autenticada desde config del tenant."""
    password = decrypt_certificate(config.smtp_password_encrypted).decode('utf-8')

    if config.smtp_use_tls:
        server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
    else:
        server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15)
        server.ehlo()

    server.login(config.smtp_user, password)
    return server


def test_smtp_connection(config):
    """Testea conexión SMTP sin enviar email."""
    try:
        server = get_smtp_connection(config)
        server.quit()
        return {'success': True}
    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'error': 'Credenciales SMTP inválidas'}
    except smtplib.SMTPConnectError:
        return {'success': False, 'error': 'No se pudo conectar al servidor SMTP'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def send_email(config, to_email, subject, html_body, attachments=None):
    """Envía un email con adjuntos opcionales.

    Args:
        config: EmailConfig del tenant
        to_email: Dirección destino
        subject: Asunto del email
        html_body: Contenido HTML del email
        attachments: Lista de tuplas (filename, bytes_data, mime_type)
    """
    msg = MIMEMultipart()

    from_addr = config.from_email
    if config.from_name:
        from_addr = f'{config.from_name} <{config.from_email}>'

    msg['From'] = from_addr
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    if attachments:
        for filename, data, mime_type in attachments:
            maintype, subtype = mime_type.split('/', 1)
            part = MIMEBase(maintype, subtype)
            part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(part)

    server = get_smtp_connection(config)
    try:
        server.sendmail(config.from_email, to_email, msg.as_string())
    finally:
        server.quit()


def send_comprobante_email(factura):
    """Envía el comprobante PDF de una factura autorizada al receptor.

    Args:
        factura: Factura con estado 'autorizado' y receptor con email

    Raises:
        ValueError: Si la factura no está autorizada o el receptor no tiene email
        Exception: Si falla la generación de PDF o el envío SMTP
    """
    from ..models import EmailConfig

    if factura.estado != 'autorizado':
        raise ValueError('Solo se pueden enviar comprobantes de facturas autorizadas')

    receptor = factura.receptor
    if not receptor or not receptor.email:
        raise ValueError('El receptor no tiene email configurado')

    config = EmailConfig.query.filter_by(
        tenant_id=factura.tenant_id,
        email_habilitado=True,
    ).first()

    if not config:
        raise ValueError('No hay configuración de email habilitada para este tenant')

    # Generar HTML y PDF del comprobante
    from .comprobante_renderer import render_comprobante_html
    from .comprobante_pdf import html_to_pdf_bytes

    html = render_comprobante_html(factura)
    pdf_bytes = html_to_pdf_bytes(html)

    # Construir nombre del archivo
    punto_venta = int(factura.punto_venta or 0)
    numero = int(factura.numero_comprobante or 0)
    filename = f'comprobante-{punto_venta:05d}-{numero:08d}.pdf'

    # Construir asunto
    facturador_nombre = factura.facturador.razon_social if factura.facturador else 'Facturador'
    subject = f'Comprobante {punto_venta:05d}-{numero:08d} - {facturador_nombre}'

    # Construir body HTML
    body_html = _build_comprobante_email_body(factura, facturador_nombre)

    send_email(
        config=config,
        to_email=receptor.email,
        subject=subject,
        html_body=body_html,
        attachments=[(filename, pdf_bytes, 'application/pdf')],
    )


def send_test_email(config, to_email):
    """Envía un email de prueba para verificar la configuración."""
    subject = 'Email de prueba - Facturador'
    body = """
    <html>
    <body style="font-family: Inter, sans-serif; color: #1e293b; padding: 20px;">
        <h2 style="color: #2563eb;">Configuración de email verificada</h2>
        <p>Este es un email de prueba enviado desde el sistema Facturador.</p>
        <p>Si recibiste este mensaje, la configuración SMTP está funcionando correctamente.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="color: #64748b; font-size: 12px;">Facturador - Sistema de facturación electrónica</p>
    </body>
    </html>
    """
    send_email(config, to_email, subject, body)


def _build_comprobante_email_body(factura, facturador_nombre):
    """Construye el HTML del cuerpo del email de comprobante."""
    punto_venta = int(factura.punto_venta or 0)
    numero = int(factura.numero_comprobante or 0)
    importe = float(factura.importe_total)
    fecha = factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else ''
    receptor_nombre = factura.receptor.razon_social if factura.receptor else ''

    return f"""
    <html>
    <body style="font-family: Inter, sans-serif; color: #1e293b; padding: 20px; max-width: 600px; margin: 0 auto;">
        <div style="border-bottom: 3px solid #2563eb; padding-bottom: 16px; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2563eb;">{facturador_nombre}</h2>
        </div>

        <p>Estimado/a <strong>{receptor_nombre}</strong>,</p>

        <p>Adjunto encontrará el comprobante electrónico correspondiente a:</p>

        <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
            <tr>
                <td style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; font-weight: 600;">Comprobante</td>
                <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{punto_venta:05d}-{numero:08d}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; font-weight: 600;">Fecha</td>
                <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{fecha}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; font-weight: 600;">Importe Total</td>
                <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">$ {importe:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0; font-weight: 600;">CAE</td>
                <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">{factura.cae or ''}</td>
            </tr>
        </table>

        <p style="color: #64748b; font-size: 13px;">
            Este comprobante fue autorizado por ARCA (ex-AFIP) y es válido como factura electrónica.
        </p>

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 11px;">
            Enviado automáticamente por Facturador - Sistema de facturación electrónica
        </p>
    </body>
    </html>
    """
