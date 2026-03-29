"""Tests para email CC override y resolución de destinatarios/contenido."""
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from datetime import date
from decimal import Decimal
from app.models import Factura, Lote, EmailConfig, Receptor
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
        email_asunto='Comprobante {comprobante} - {facturador}',
        email_mensaje='Adjunto su comprobante electronico.',
        email_saludo='Estimado/a {receptor},',
        email_despedida='Saludos cordiales',
        email_firma='Equipo Contable',
    )
    db.session.add(config)
    db.session.commit()
    return config


@pytest.fixture
def email_config_disabled(db, tenant):
    """Config de email con email_habilitado=False."""
    config = EmailConfig(
        tenant_id=tenant.id,
        smtp_host='smtp.test.com',
        smtp_port=587,
        smtp_use_tls=True,
        smtp_user='user@test.com',
        smtp_password_encrypted=encrypt_certificate(b'password123'),
        from_email='noreply@test.com',
        from_name='Test Facturador',
        email_habilitado=False,
    )
    db.session.add(config)
    db.session.commit()
    return config


@pytest.fixture
def receptor_con_email(db, tenant):
    """Receptor con email."""
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
def receptor_sin_email(db, tenant):
    """Receptor sin email."""
    r = Receptor(
        tenant_id=tenant.id,
        doc_tipo=80,
        doc_nro='30333333333',
        razon_social='Receptor Sin Email SA',
        email=None,
        activo=True,
    )
    db.session.add(r)
    db.session.commit()
    return r


def _make_factura(db, tenant, facturador, receptor, emails_cc=None,
                  email_asunto=None, email_mensaje=None, email_firma=None):
    """Helper para crear factura autorizada con overrides opcionales."""
    lote = Lote(
        tenant_id=tenant.id,
        etiqueta='test-override',
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
        receptor_id=receptor.id,
        tipo_comprobante=1,
        concepto=2,
        punto_venta=1,
        numero_comprobante=1,
        fecha_emision=date(2026, 1, 15),
        importe_total=Decimal('1210.00'),
        importe_neto=Decimal('1000.00'),
        importe_iva=Decimal('210.00'),
        cae='12345678901234',
        estado='autorizado',
        emails_cc=emails_cc,
        email_asunto=email_asunto,
        email_mensaje=email_mensaje,
        email_firma=email_firma,
    )
    db.session.add(factura)
    db.session.commit()
    return factura


class TestResolverDestinatariosEmail:
    """Tests para _resolver_destinatarios_email() en facturacion.py."""

    def test_emails_cc_present_receptor_has_email(self, db, tenant, facturador, receptor_con_email):
        """emails_cc + receptor.email -> enviar a ambos."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='cc@test.com',
        )
        result = _resolver_destinatarios_email(factura)
        assert result is not None
        assert 'receptor@test.com' in result
        assert 'cc@test.com' in result
        assert len(result) == 2

    def test_emails_cc_present_receptor_no_email(self, db, tenant, facturador, receptor_sin_email):
        """emails_cc + receptor.email=None -> enviar solo a cc."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_sin_email,
            emails_cc='cc1@test.com,cc2@test.com',
        )
        result = _resolver_destinatarios_email(factura)
        assert result is not None
        assert result == ['cc1@test.com', 'cc2@test.com']

    def test_emails_cc_present_bypasses_email_habilitado(self, db, tenant, facturador, receptor_con_email):
        """emails_cc presente -> ignora email_habilitado (bypass)."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='cc@test.com',
        )
        # _resolver_destinatarios_email no consulta email_habilitado,
        # siempre retorna destinatarios si hay emails_cc
        result = _resolver_destinatarios_email(factura)
        assert result is not None
        assert 'receptor@test.com' in result
        assert 'cc@test.com' in result

    def test_no_emails_cc_receptor_has_email(self, db, tenant, facturador, receptor_con_email):
        """Sin emails_cc + receptor.email -> retorna None (flujo default)."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
        )
        result = _resolver_destinatarios_email(factura)
        assert result is None

    def test_no_emails_cc_receptor_no_email(self, db, tenant, facturador, receptor_sin_email):
        """Sin emails_cc + sin receptor.email -> retorna None."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_sin_email,
        )
        result = _resolver_destinatarios_email(factura)
        assert result is None

    def test_empty_emails_cc_treated_as_absent(self, db, tenant, facturador, receptor_con_email):
        """emails_cc vacio o solo espacios -> igual que ausente."""
        from app.tasks.facturacion import _resolver_destinatarios_email

        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='  ',
        )
        result = _resolver_destinatarios_email(factura)
        assert result is None


class TestEmailContentResolution:
    """Tests para resolución de contenido de email (asunto, mensaje, firma)."""

    def test_full_override_from_csv(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Override completo: asunto + mensaje + firma del CSV."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
            email_mensaje='Mensaje custom',
            email_firma='Firma custom',
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(
                    factura,
                    destinatarios=['receptor@test.com'],
                    factura_asunto='Asunto Custom',
                    factura_mensaje='Mensaje custom',
                    factura_firma='Firma custom',
                )

                call_kwargs = mock_send.call_args.kwargs
                assert call_kwargs['subject'] == 'Asunto Custom'
                assert 'Mensaje custom' in call_kwargs['html_body']
                assert 'Firma custom' in call_kwargs['html_body']

    def test_only_asunto_override(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Solo asunto override -> asunto del CSV, body sin saludo/despedida/mensaje/firma."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(
                    factura,
                    destinatarios=['receptor@test.com'],
                    factura_asunto='Asunto Custom',
                    factura_mensaje=None,
                    factura_firma=None,
                )

                call_kwargs = mock_send.call_args.kwargs
                assert call_kwargs['subject'] == 'Asunto Custom'
                body = call_kwargs['html_body']
                assert 'Adjunto su comprobante electronico' not in body
                assert 'Equipo Contable' not in body
                assert 'Estimado/a' not in body
                assert 'Saludos cordiales' not in body

    def test_no_override_uses_email_config(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Sin override -> usa contenido de EmailConfig (comportamiento actual)."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(factura)

                call_kwargs = mock_send.call_args.kwargs
                # Asunto de EmailConfig
                assert 'Comprobante' in call_kwargs['subject']
                # Mensaje de EmailConfig
                assert 'Adjunto su comprobante electronico' in call_kwargs['html_body']
                # Firma de EmailConfig
                assert 'Equipo Contable' in call_kwargs['html_body']

    def test_override_with_placeholders_substituted(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Override de asunto con placeholders se sustituyen correctamente."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Comprobante {comprobante} de {facturador}',
            email_mensaje='Hola {receptor}, tu factura de {facturador}',
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(
                    factura,
                    destinatarios=['receptor@test.com'],
                    factura_asunto='Comprobante {comprobante} de {facturador}',
                    factura_mensaje='Hola {receptor}, tu factura de {facturador}',
                    factura_firma=None,
                )

                call_kwargs = mock_send.call_args.kwargs
                # Asunto: placeholders sustituidos
                assert 'Test SA' in call_kwargs['subject']
                assert '{facturador}' not in call_kwargs['subject']
                assert '{comprobante}' not in call_kwargs['subject']

                # Body: placeholders sustituidos
                body = call_kwargs['html_body']
                assert 'Receptor Email SA' in body
                assert 'Test SA' in body
                assert '{receptor}' not in body
                assert '{facturador}' not in body

    def test_override_mensaje_triggers_override_body(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """factura_asunto + factura_mensaje triggers _build_override_email_body."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(
                    factura,
                    destinatarios=['receptor@test.com'],
                    factura_asunto='Asunto Custom',
                    factura_mensaje='Mensaje override',
                    factura_firma='Firma override',
                )

                call_kwargs = mock_send.call_args.kwargs
                body = call_kwargs['html_body']
                assert 'Mensaje override' in body
                assert 'Firma override' in body
                # Should NOT contain the default EmailConfig message
                assert 'Adjunto su comprobante electronico' not in body

    def test_mensaje_firma_without_asunto_ignored(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """factura_mensaje/firma sin factura_asunto -> usa body estándar de config."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_mensaje='Mensaje override',
            email_firma='Firma override',
        )
        with app.app_context():
            from app.services.email_service import send_comprobante_email
            with patch('app.services.email_service.send_email') as mock_send, \
                 patch('app.services.comprobante_pdf.html_to_pdf_bytes', return_value=b'%PDF'), \
                 patch('app.services.comprobante_renderer.render_comprobante_html', return_value='<html></html>'):

                send_comprobante_email(
                    factura,
                    destinatarios=['receptor@test.com'],
                    factura_asunto=None,
                    factura_mensaje='Mensaje override',
                    factura_firma='Firma override',
                )

                call_kwargs = mock_send.call_args.kwargs
                body = call_kwargs['html_body']
                # Without factura_asunto, override is not triggered
                assert 'Adjunto su comprobante electronico' in body
                assert 'Mensaje override' not in body


class TestEmailHabilitadoBypass:
    """Tests para el bypass de email_habilitado cuando hay emails_cc."""

    def test_destinatarios_bypass_email_habilitado(self, app, db, tenant, facturador,
                                                     receptor_con_email, email_config_disabled):
        """Con destinatarios explícitos, email_habilitado=false se bypasea."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='cc@test.com',
        )
        with app.app_context():
            from app.tasks.email import _enviar_factura_email_sync

            with patch('app.services.email_service.send_comprobante_email') as mock_send:
                result = _enviar_factura_email_sync(
                    factura,
                    destinatarios=['receptor@test.com', 'cc@test.com'],
                    use_factura_overrides=True,
                )
                assert result.get('success') is True
                mock_send.assert_called_once()

    def test_no_destinatarios_respects_email_habilitado(self, app, db, tenant, facturador,
                                                          receptor_con_email, email_config_disabled):
        """Sin destinatarios explícitos, email_habilitado=false -> no enviar."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
        )
        with app.app_context():
            from app.tasks.email import _enviar_factura_email_sync

            result = _enviar_factura_email_sync(factura)
            assert result.get('skipped') is True
            assert 'config' in result.get('reason', '').lower()

    def test_no_destinatarios_email_habilitado_true_sends(self, app, db, tenant, facturador,
                                                            receptor_con_email, email_config):
        """Sin destinatarios + email_habilitado=true -> envía normalmente."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
        )
        with app.app_context():
            from app.tasks.email import _enviar_factura_email_sync

            with patch('app.services.email_service.send_comprobante_email'):
                result = _enviar_factura_email_sync(factura)
                assert result.get('success') is True


class TestBuildOverrideEmailBody:
    """Tests para _build_override_email_body(): solo mensaje + firma del CSV."""

    def test_override_body_contains_only_mensaje_and_firma(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Override body debe contener SOLO mensaje y firma, sin saludo ni despedida de config."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
            email_mensaje='Mensaje del CSV',
            email_firma='Firma del CSV',
        )
        with app.app_context():
            from app.services.email_service import _build_override_email_body
            body = _build_override_email_body(
                factura, 'Test SA', email_config, 'Factura A 00001-00000001',
                mensaje='Mensaje del CSV',
                firma='Firma del CSV',
            )
            assert 'Mensaje del CSV' in body
            assert 'Firma del CSV' in body
            assert 'Estimado/a' not in body
            assert 'Saludos cordiales' not in body

    def test_override_body_empty_mensaje_and_firma(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Sin mensaje ni firma, el body tiene solo el footer HTML."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
        )
        with app.app_context():
            from app.services.email_service import _build_override_email_body
            body = _build_override_email_body(
                factura, 'Test SA', email_config, 'Factura A 00001-00000001',
                mensaje=None,
                firma=None,
            )
            assert 'Estimado/a' not in body
            assert 'Saludos cordiales' not in body
            assert 'adain.dev' in body

    def test_override_body_placeholders_applied(self, app, db, tenant, facturador, receptor_con_email, email_config):
        """Placeholders en mensaje y firma se sustituyen correctamente."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto',
            email_mensaje='Hola {receptor}',
            email_firma='De {facturador}',
        )
        with app.app_context():
            from app.services.email_service import _build_override_email_body
            body = _build_override_email_body(
                factura, 'Test SA', email_config, 'Factura A 00001-00000001',
                mensaje='Hola {receptor}',
                firma='De {facturador}',
            )
            assert 'Hola Receptor Email SA' in body
            assert 'De Test SA' in body
            assert '{receptor}' not in body
            assert '{facturador}' not in body


class TestHasFacturaOverrides:
    """Tests para _has_factura_overrides()."""

    def test_returns_true_when_email_asunto_has_content(self, db, tenant, facturador, receptor_con_email):
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='Asunto Custom',
        )
        from app.tasks.facturacion import _has_factura_overrides
        assert _has_factura_overrides(factura) is True

    def test_returns_false_when_email_asunto_is_none(self, db, tenant, facturador, receptor_con_email):
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto=None,
        )
        from app.tasks.facturacion import _has_factura_overrides
        assert _has_factura_overrides(factura) is False

    def test_returns_false_when_email_asunto_is_empty(self, db, tenant, facturador, receptor_con_email):
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='',
        )
        from app.tasks.facturacion import _has_factura_overrides
        assert _has_factura_overrides(factura) is False

    def test_returns_false_when_email_asunto_is_whitespace(self, db, tenant, facturador, receptor_con_email):
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            email_asunto='   ',
        )
        from app.tasks.facturacion import _has_factura_overrides
        assert _has_factura_overrides(factura) is False


class TestDispatchUseFacturaOverrides:
    """Tests para verificar que use_factura_overrides se pasa correctamente en ambas ramas."""

    def test_cc_branch_passes_use_overrides_true(self, app, db, tenant, facturador, receptor_con_email):
        """Con emails_cc + email_asunto -> use_factura_overrides=True en rama CC."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='cc@test.com',
            email_asunto='Asunto Custom',
        )
        from app.tasks.facturacion import _resolver_destinatarios_email, _has_factura_overrides
        destinatarios = _resolver_destinatarios_email(factura)
        use_overrides = _has_factura_overrides(factura)
        assert destinatarios is not None
        assert use_overrides is True

    def test_cc_branch_passes_use_overrides_false(self, app, db, tenant, facturador, receptor_con_email):
        """Con emails_cc pero sin email_asunto -> use_factura_overrides=False en rama CC."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc='cc@test.com',
            email_asunto=None,
        )
        from app.tasks.facturacion import _resolver_destinatarios_email, _has_factura_overrides
        destinatarios = _resolver_destinatarios_email(factura)
        use_overrides = _has_factura_overrides(factura)
        assert destinatarios is not None
        assert use_overrides is False

    def test_no_cc_branch_passes_use_overrides_true(self, app, db, tenant, facturador, receptor_con_email):
        """Sin emails_cc + email_asunto -> use_factura_overrides=True en rama no-CC."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc=None,
            email_asunto='Asunto Custom',
        )
        from app.tasks.facturacion import _resolver_destinatarios_email, _has_factura_overrides
        destinatarios = _resolver_destinatarios_email(factura)
        use_overrides = _has_factura_overrides(factura)
        assert destinatarios is None
        assert use_overrides is True

    def test_no_cc_no_overrides(self, app, db, tenant, facturador, receptor_con_email):
        """Sin emails_cc ni email_asunto -> use_factura_overrides=False en rama no-CC."""
        factura = _make_factura(
            db, tenant, facturador, receptor_con_email,
            emails_cc=None,
            email_asunto=None,
        )
        from app.tasks.facturacion import _resolver_destinatarios_email, _has_factura_overrides
        destinatarios = _resolver_destinatarios_email(factura)
        use_overrides = _has_factura_overrides(factura)
        assert destinatarios is None
        assert use_overrides is False
