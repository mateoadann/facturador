import html
import smtplib
import logging
from types import SimpleNamespace
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from .encryption import decrypt_certificate
from .comprobante_filename import build_comprobante_pdf_filename

logger = logging.getLogger(__name__)

DEFAULT_PREVIEW_SAMPLE_DATA = {
    'facturador': 'Empresa Demo SRL',
    'receptor': 'Cliente Ejemplo SA',
    'comprobante': 'Factura A 00001-00001234',
}


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


def send_comprobante_email(factura, custom_asunto=None, custom_body=None,
                           destinatarios=None,
                           factura_asunto=None, factura_mensaje=None,
                           factura_firma=None):
    """Envía el comprobante PDF de una factura autorizada al receptor.

    Args:
        factura: Factura con estado 'autorizado' y receptor con email
        custom_asunto: Asunto personalizado (opcional, para reenvíos manuales)
        custom_body: Cuerpo en texto plano personalizado (opcional, para reenvíos manuales)
        destinatarios: Lista de emails destino (opcional, si no se usa receptor.email)
        factura_asunto: Override de asunto desde CSV (opcional)
        factura_mensaje: Override de mensaje desde CSV (opcional)
        factura_firma: Override de firma desde CSV (opcional)

    Raises:
        ValueError: Si la factura no está autorizada o no hay destinatario
        Exception: Si falla la generación de PDF o el envío SMTP
    """
    from ..models import EmailConfig

    if factura.estado != 'autorizado':
        raise ValueError('Solo se pueden enviar comprobantes de facturas autorizadas')

    receptor = factura.receptor
    if not destinatarios and (not receptor or not receptor.email):
        raise ValueError('El receptor no tiene email configurado')

    # Cuando hay destinatarios explícitos, buscar config sin filtrar por email_habilitado
    if destinatarios:
        config = EmailConfig.query.filter_by(tenant_id=factura.tenant_id).first()
    else:
        config = EmailConfig.query.filter_by(
            tenant_id=factura.tenant_id,
            email_habilitado=True,
        ).first()

    if not config:
        raise ValueError('No hay configuración de email para este tenant')

    # Generar HTML y PDF del comprobante
    from .comprobante_renderer import render_comprobante_html
    from .comprobante_pdf import html_to_pdf_bytes

    comprobante_html = render_comprobante_html(factura)
    pdf_bytes = html_to_pdf_bytes(comprobante_html)

    # Construir nombre del archivo
    punto_venta = int(factura.punto_venta or 0)
    numero = int(factura.numero_comprobante or 0)
    filename = build_comprobante_pdf_filename(factura)

    # Construir asunto y body
    from arca_integration.constants import TIPOS_COMPROBANTE

    facturador_nombre = factura.facturador.razon_social if factura.facturador else 'Facturador'
    tipo_nombre = TIPOS_COMPROBANTE.get(factura.tipo_comprobante, 'Comprobante')
    comprobante_str = f'{tipo_nombre} {punto_venta:05d}-{numero:08d}'

    # Resolución de asunto (3 niveles de prioridad)
    if custom_asunto:
        subject = custom_asunto
    elif factura_asunto:
        subject = _apply_placeholders(factura_asunto, factura, facturador_nombre, comprobante_str)
    else:
        subject = _build_subject(config, comprobante_str, facturador_nombre)

    # Resolución de body (3 niveles de prioridad)
    if custom_body:
        body_html = _build_custom_body_html(custom_body)
    elif factura_asunto:
        # email_asunto is the override switch — use override body (may be empty)
        body_html = _build_override_email_body(
            factura, facturador_nombre, config, comprobante_str,
            mensaje=factura_mensaje,
            firma=factura_firma,
        )
    else:
        body_html = _build_comprobante_email_body(factura, facturador_nombre, config, comprobante_str)

    target_emails = destinatarios or [receptor.email]
    for to_email in target_emails:
        send_email(
            config=config,
            to_email=to_email,
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


def build_email_preview(email_asunto=None, email_mensaje=None, email_saludo=None,
                        email_despedida=None, email_firma=None,
                        from_name=None, sample_data=None):
    """Construye una vista previa del email usando la misma logica de produccion."""
    normalized_sample_data = dict(DEFAULT_PREVIEW_SAMPLE_DATA)
    if sample_data:
        normalized_sample_data.update(sample_data)

    config = SimpleNamespace(
        email_asunto=(email_asunto or '').strip() or None,
        email_mensaje=(email_mensaje or '').strip() or None,
        email_saludo=(email_saludo or '').strip() or None,
        email_despedida=(email_despedida or '').strip() or None,
        email_firma=(email_firma or '').strip() or None,
    )

    subject = _build_subject(
        config,
        normalized_sample_data['comprobante'],
        normalized_sample_data['facturador'],
    )
    html = _build_comprobante_email_body_from_data(
        receptor_nombre=normalized_sample_data['receptor'],
        facturador_nombre=normalized_sample_data['facturador'],
        comprobante_str=normalized_sample_data['comprobante'],
        config=config,
    )

    return {
        'subject': subject,
        'html': html,
        'sample_data': {
            **normalized_sample_data,
            'from_name': (from_name or '').strip() or None,
        },
    }


def _apply_placeholders(text, factura, facturador_nombre, comprobante_str):
    """Sustituye placeholders {receptor}, {facturador}, {comprobante} en texto."""
    receptor_nombre = factura.receptor.razon_social if factura.receptor else ''
    return (
        text
        .replace('{receptor}', receptor_nombre)
        .replace('{facturador}', facturador_nombre)
        .replace('{comprobante}', comprobante_str)
    )


def _build_override_email_body(factura, facturador_nombre, config, comprobante_str,
                                mensaje=None, firma=None):
    """Body con overrides del CSV. Usa SOLO mensaje y firma del CSV, sin config saludo/despedida."""
    sections = []
    if mensaje:
        mensaje_html = _apply_placeholders(mensaje, factura, facturador_nombre, comprobante_str)
        sections.append(f'<p>{mensaje_html.replace(chr(10), "<br>")}</p>')
    if firma:
        firma_html = _apply_placeholders(firma, factura, facturador_nombre, comprobante_str)
        sections.append(f'<p style="color: #475569;">{firma_html.replace(chr(10), "<br>")}</p>')

    body_content = '\n        '.join(sections)

    return f"""
    <html>
    <body style="font-family: Inter, sans-serif; color: #1e293b; padding: 20px; max-width: 600px; margin: 0;">
        {body_content}

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 11px;">
            Enviado automáticamente por <a href="https://adain.dev" style="color: #94a3b8; text-decoration: underline;">AD&#923;IN AI Solutions</a>
        </p>
    </body>
    </html>
    """


def _build_custom_body_html(custom_body):
    """Construye HTML del email a partir de texto plano custom (para reenvíos)."""
    escaped = html.escape(custom_body)
    body_content = escaped.replace('\n', '<br>')

    return f"""
    <html>
    <body style="font-family: Inter, sans-serif; color: #1e293b; padding: 20px; max-width: 600px; margin: 0;">
        <p>{body_content}</p>

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 11px;">
            Enviado automáticamente por <a href="https://adain.dev" style="color: #94a3b8; text-decoration: underline;">AD&#923;IN AI Solutions</a>
        </p>
    </body>
    </html>
    """


def _build_subject(config, comprobante_str, facturador_nombre):
    """Construye el asunto del email usando config o default."""
    if config.email_asunto:
        return config.email_asunto.replace(
            '{comprobante}', comprobante_str
        ).replace(
            '{facturador}', facturador_nombre
        )
    return f'Comprobante {comprobante_str} - {facturador_nombre}'


def _build_comprobante_email_body(factura, facturador_nombre, config, comprobante_str=''):
    """Construye el HTML del cuerpo del email de comprobante."""
    receptor_nombre = factura.receptor.razon_social if factura.receptor else ''

    return _build_comprobante_email_body_from_data(
        receptor_nombre=receptor_nombre,
        facturador_nombre=facturador_nombre,
        comprobante_str=comprobante_str,
        config=config,
    )


def _build_comprobante_email_body_from_data(receptor_nombre, facturador_nombre, config,
                                             comprobante_str=''):
    """Construye el HTML del cuerpo del email de comprobante."""

    # Saludo (greeting) with variable interpolation
    saludo_raw = config.email_saludo if config.email_saludo else 'Estimado/a {receptor},'
    saludo = (
        saludo_raw
        .replace('{receptor}', receptor_nombre)
        .replace('{facturador}', facturador_nombre)
        .replace('{comprobante}', comprobante_str)
    )

    # Mensaje principal
    mensaje = config.email_mensaje if config.email_mensaje else (
        'Adjunto encontrará el comprobante electrónico correspondiente.'
    )
    # Convertir saltos de línea a <br> para HTML
    mensaje_html = mensaje.replace('\n', '<br>')

    # Despedida (farewell)
    despedida = config.email_despedida if config.email_despedida else 'Saludos cordiales'
    despedida_html = despedida.replace('\n', '<br>')

    # Firma (signature)
    firma = config.email_firma if config.email_firma else None

    # Build HTML sections
    sections = []
    sections.append(f'<p>{saludo}</p>')
    sections.append(f'<p>{mensaje_html}</p>')
    sections.append(f'<p>{despedida_html}</p>')

    if firma:
        firma_html = firma.replace('\n', '<br>')
        sections.append(f'<p style="color: #475569;">{firma_html}</p>')

    body_content = '\n        '.join(sections)

    return f"""
    <html>
    <body style="font-family: Inter, sans-serif; color: #1e293b; padding: 20px; max-width: 600px; margin: 0;">
        {body_content}

        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <p style="color: #94a3b8; font-size: 11px;">
            Enviado automáticamente por <a href="https://adain.dev" style="color: #94a3b8; text-decoration: underline;">AD&#923;IN AI Solutions</a>
        </p>
    </body>
    </html>
    """
