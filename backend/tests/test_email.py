"""Tests para configuración y envío de email."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from decimal import Decimal
from app.models import EmailConfig, Factura, Lote
from app.services.encryption import encrypt_certificate


@pytest.fixture
def email_config(db, tenant):
    """Crear configuración de email para el tenant."""
    config = EmailConfig(
        tenant_id=tenant.id,
        smtp_host='smtp.test.com',
        smtp_port=587,
        smtp_use_tls=True,
        smtp_user='user@test.com',
        smtp_password_encrypted=encrypt_certificate(b'password123'),
        from_email='noreply@test.com',
        from_name='Test Facturador',
        email_habilitado=True,
    )
    db.session.add(config)
    db.session.commit()
    return config


@pytest.fixture
def receptor_con_email(db, tenant):
    """Receptor con email configurado."""
    from app.models import Receptor
    r = Receptor(
        tenant_id=tenant.id,
        doc_tipo=80,
        doc_nro='30222222222',
        razon_social='Receptor Email SA',
        email='receptor@test.com',
        activo=True,
    )
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def factura_autorizada(db, tenant, facturador, receptor_con_email):
    """Factura autorizada lista para enviar por email."""
    lote = Lote(
        tenant_id=tenant.id,
        etiqueta='test-email',
        tipo='factura',
        estado='completado',
        total_facturas=1,
        facturas_ok=1,
    )
    db.session.add(lote)
    db.session.flush()

    factura = Factura(
        tenant_id=tenant.id,
        lote_id=lote.id,
        facturador_id=facturador.id,
        receptor_id=receptor_con_email.id,
        tipo_comprobante=1,
        concepto=2,
        punto_venta=1,
        numero_comprobante=1,
        fecha_emision=date(2024, 1, 15),
        importe_total=Decimal('1210.00'),
        importe_neto=Decimal('1000.00'),
        importe_iva=Decimal('210.00'),
        cae='12345678901234',
        estado='autorizado',
    )
    db.session.add(factura)
    db.session.commit()
    return factura


class TestEmailConfigEndpoints:
    """Tests para GET/PUT /api/email/config."""

    def test_get_config_sin_configurar(self, client, auth_headers):
        """GET config cuando no hay configuración devuelve configured=False."""
        resp = client.get('/api/email/config', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['configured'] is False

    def test_crear_config(self, client, auth_headers):
        """PUT config crea configuración nueva."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.gmail.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
            'smtp_user': 'test@gmail.com',
            'smtp_password': 'app-password-123',
            'from_email': 'noreply@empresa.com',
            'from_name': 'Mi Empresa',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['configured'] is True
        assert data['smtp_host'] == 'smtp.gmail.com'
        assert data['smtp_user'] == 'test@gmail.com'
        assert data['from_email'] == 'noreply@empresa.com'
        assert data['tiene_password'] is True
        assert 'smtp_password' not in data  # No expone password

    def test_get_config_existente(self, client, auth_headers, email_config):
        """GET config con configuración existente."""
        resp = client.get('/api/email/config', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['configured'] is True
        assert data['smtp_host'] == 'smtp.test.com'
        assert data['tiene_password'] is True

    def test_actualizar_config_sin_cambiar_password(self, client, auth_headers, email_config):
        """PUT config sin smtp_password mantiene la password existente."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.nuevo.com',
            'smtp_user': 'nuevo@test.com',
            'from_email': 'nuevo@empresa.com',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['smtp_host'] == 'smtp.nuevo.com'
        assert data['tiene_password'] is True

    def test_crear_config_sin_password_falla(self, client, auth_headers):
        """PUT config nueva sin password falla."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.test.com',
            'smtp_user': 'user@test.com',
            'from_email': 'noreply@test.com',
        })
        assert resp.status_code == 400
        assert 'contraseña' in resp.get_json()['error'].lower() or 'password' in resp.get_json()['error'].lower()

    def test_crear_config_campos_requeridos(self, client, auth_headers):
        """PUT config sin campos requeridos falla."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.test.com',
        })
        assert resp.status_code == 400

    def test_operator_no_puede_configurar(self, client, operator_headers):
        """Operator no tiene permiso email:configurar."""
        resp = client.get('/api/email/config', headers=operator_headers)
        assert resp.status_code == 403

    def test_viewer_no_puede_configurar(self, client, viewer_headers):
        """Viewer no tiene permiso email:configurar."""
        resp = client.get('/api/email/config', headers=viewer_headers)
        assert resp.status_code == 403


class TestEmailTestConnection:
    """Tests para POST /api/email/test."""

    def test_sin_config_falla(self, client, auth_headers):
        """Test conexión sin config retorna error."""
        resp = client.post('/api/email/test', headers=auth_headers)
        assert resp.status_code == 400

    @patch('app.api.email.test_smtp_connection')
    def test_conexion_exitosa(self, mock_test, client, auth_headers, email_config):
        """Test conexión exitosa."""
        mock_test.return_value = {'success': True}
        resp = client.post('/api/email/test', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    @patch('app.api.email.test_smtp_connection')
    def test_conexion_fallida(self, mock_test, client, auth_headers, email_config):
        """Test conexión fallida."""
        mock_test.return_value = {'success': False, 'error': 'Credenciales inválidas'}
        resp = client.post('/api/email/test', headers=auth_headers)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False


class TestEmailTestSend:
    """Tests para POST /api/email/test-send."""

    def test_sin_to_email_falla(self, client, auth_headers, email_config):
        """Test send sin to_email falla."""
        resp = client.post('/api/email/test-send', headers=auth_headers, json={})
        assert resp.status_code == 400

    @patch('app.api.email.send_test_email')
    def test_envio_prueba_exitoso(self, mock_send, client, auth_headers, email_config):
        """Test send exitoso."""
        mock_send.return_value = None
        resp = client.post('/api/email/test-send', headers=auth_headers, json={
            'to_email': 'destino@test.com'
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
        mock_send.assert_called_once()


class TestEnviarEmailFactura:
    """Tests para POST /api/facturas/:id/enviar-email."""

    @patch('app.tasks.email.enviar_factura_email')
    def test_enviar_email_exitoso(self, mock_task, client, auth_headers,
                                  email_config, factura_autorizada):
        """Enviar email de factura autorizada."""
        mock_task.delay = MagicMock()
        resp = client.post(
            f'/api/facturas/{factura_autorizada.id}/enviar-email',
            headers=auth_headers
        )
        assert resp.status_code == 202
        data = resp.get_json()
        assert 'receptor_email' in data
        mock_task.delay.assert_called_once_with(
            str(factura_autorizada.id),
            str(factura_autorizada.tenant_id),
        )

    def test_factura_no_autorizada_falla(self, client, auth_headers, db,
                                         email_config, tenant, facturador, receptor_con_email):
        """No se puede enviar email de factura no autorizada."""
        factura = Factura(
            tenant_id=tenant.id,
            facturador_id=facturador.id,
            receptor_id=receptor_con_email.id,
            tipo_comprobante=1, concepto=2, punto_venta=1,
            fecha_emision=date(2024, 1, 15),
            importe_total=Decimal('100'), importe_neto=Decimal('82.64'),
            estado='pendiente',
        )
        db.session.add(factura)
        db.session.commit()

        resp = client.post(f'/api/facturas/{factura.id}/enviar-email', headers=auth_headers)
        assert resp.status_code == 400

    def test_sin_config_email_falla(self, client, auth_headers, factura_autorizada):
        """No se puede enviar si no hay config de email."""
        resp = client.post(
            f'/api/facturas/{factura_autorizada.id}/enviar-email',
            headers=auth_headers
        )
        assert resp.status_code == 400
        assert 'configuración' in resp.get_json()['error'].lower() or 'config' in resp.get_json()['error'].lower()

    @patch('app.tasks.email.enviar_factura_email')
    def test_operator_puede_enviar(self, mock_task, client, operator_headers,
                                    email_config, factura_autorizada):
        """Operator tiene permiso email:enviar."""
        mock_task.delay = MagicMock()
        resp = client.post(
            f'/api/facturas/{factura_autorizada.id}/enviar-email',
            headers=operator_headers
        )
        assert resp.status_code == 202

    def test_viewer_no_puede_enviar(self, client, viewer_headers,
                                     email_config, factura_autorizada):
        """Viewer no tiene permiso email:enviar."""
        resp = client.post(
            f'/api/facturas/{factura_autorizada.id}/enviar-email',
            headers=viewer_headers
        )
        assert resp.status_code == 403


class TestEmailPersonalizacion:
    """Tests para campos de personalización del email."""

    def test_guardar_campos_personalizacion(self, client, auth_headers, email_config):
        """PUT config guarda campos de personalización."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.test.com',
            'smtp_user': 'user@test.com',
            'from_email': 'noreply@test.com',
            'email_asunto': 'Factura {comprobante} - {facturador}',
            'email_mensaje': 'Le enviamos su factura.\nDatos bancarios: CBU 123456',
            'email_saludo': 'Atentamente, El equipo',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['email_asunto'] == 'Factura {comprobante} - {facturador}'
        assert data['email_mensaje'] == 'Le enviamos su factura.\nDatos bancarios: CBU 123456'
        assert data['email_saludo'] == 'Atentamente, El equipo'

    def test_get_config_con_personalizacion(self, client, auth_headers, db, email_config):
        """GET config devuelve campos de personalización."""
        email_config.email_asunto = 'Asunto custom'
        email_config.email_mensaje = 'Mensaje custom'
        email_config.email_saludo = 'Saludo custom'
        db.session.commit()

        resp = client.get('/api/email/config', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['email_asunto'] == 'Asunto custom'
        assert data['email_mensaje'] == 'Mensaje custom'
        assert data['email_saludo'] == 'Saludo custom'

    def test_campos_vacios_se_guardan_como_null(self, client, auth_headers, email_config):
        """Campos vacíos se guardan como NULL (usa defaults)."""
        resp = client.put('/api/email/config', headers=auth_headers, json={
            'smtp_host': 'smtp.test.com',
            'smtp_user': 'user@test.com',
            'from_email': 'noreply@test.com',
            'email_asunto': '',
            'email_mensaje': '   ',
            'email_saludo': '',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['email_asunto'] is None
        assert data['email_mensaje'] is None
        assert data['email_saludo'] is None

    def test_build_subject_custom(self, app):
        """Asunto custom reemplaza {comprobante} y {facturador}."""
        with app.app_context():
            from app.services.email_service import _build_subject

            class FakeConfig:
                email_asunto = 'Factura {comprobante} de {facturador}'

            result = _build_subject(FakeConfig(), '00001-00000042', 'Mi Empresa SRL')
            assert result == 'Factura 00001-00000042 de Mi Empresa SRL'

    def test_build_subject_default(self, app):
        """Sin asunto custom usa el default."""
        with app.app_context():
            from app.services.email_service import _build_subject

            class FakeConfig:
                email_asunto = None

            result = _build_subject(FakeConfig(), '00001-00000042', 'Mi Empresa SRL')
            assert result == 'Comprobante 00001-00000042 - Mi Empresa SRL'

    def test_build_body_con_mensaje_custom(self, app, factura_autorizada, db, email_config):
        """Body usa mensaje y saludo custom cuando están configurados."""
        email_config.email_mensaje = 'Mensaje personalizado.\nSegunda línea.'
        email_config.email_saludo = 'Cordialmente'
        db.session.commit()

        with app.app_context():
            from app.services.email_service import _build_comprobante_email_body
            html = _build_comprobante_email_body(factura_autorizada, 'Test SRL', email_config)

        assert 'Mensaje personalizado.' in html
        assert 'Segunda línea.' in html
        assert '<br>' in html  # Saltos de línea convertidos
        assert 'Cordialmente' in html

    def test_build_body_defaults(self, app, factura_autorizada, email_config):
        """Body usa defaults cuando no hay personalización."""
        with app.app_context():
            from app.services.email_service import _build_comprobante_email_body
            html = _build_comprobante_email_body(factura_autorizada, 'Test SRL', email_config)

        assert 'comprobante electrónico' in html
        assert 'Saludos cordiales' in html


class TestEmailServiceUnit:
    """Tests unitarios para el servicio de email."""

    @patch('app.services.email_service.smtplib.SMTP')
    def test_test_smtp_connection_exitoso(self, mock_smtp_class, app, email_config):
        """Test de conexión SMTP exitoso."""
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        with app.app_context():
            from app.services.email_service import test_smtp_connection
            result = test_smtp_connection(email_config)

        assert result['success'] is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch('app.services.email_service.smtplib.SMTP')
    def test_test_smtp_connection_fallido(self, mock_smtp_class, app, email_config):
        """Test de conexión SMTP fallido por credenciales."""
        import smtplib
        mock_smtp_class.return_value.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b'Authentication failed'
        )

        with app.app_context():
            from app.services.email_service import test_smtp_connection
            result = test_smtp_connection(email_config)

        assert result['success'] is False
        assert 'inválidas' in result['error'].lower() or 'invalid' in result['error'].lower()
