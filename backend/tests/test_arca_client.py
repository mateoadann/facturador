import os
import pickle
import time
import tempfile
import json
import logging

from arca_integration.client import ArcaClient


class _FakeTicket:
    def __init__(self, is_expired):
        self.is_expired = is_expired


class TestArcaClientTAFallback:
    def test_uses_shared_ta_cache_dir_from_env(self, monkeypatch):
        custom_root = os.path.join(tempfile.gettempdir(), 'arca_cache_test_shared')
        monkeypatch.setenv('ARCA_TA_CACHE_DIR', custom_root)

        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        assert client._ta_path.startswith(custom_root)

    def test_has_valid_local_ta_true_when_not_expired(self):
        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        ta_file = os.path.join(client._ta_path, 'wsfe.pkl')
        with open(ta_file, 'wb') as f:
            pickle.dump(_FakeTicket(is_expired=False), f)

        assert client._has_valid_local_ta('wsfe') is True

    def test_has_valid_local_ta_false_when_expired(self):
        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        ta_file = os.path.join(client._ta_path, 'wsfe.pkl')
        with open(ta_file, 'wb') as f:
            pickle.dump(_FakeTicket(is_expired=True), f)

        assert client._has_valid_local_ta('wsfe') is False

    def test_wsfe_retries_when_arca_reports_existing_ta(self, monkeypatch):
        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        calls = {'count': 0}

        class _FakeWS:
            pass

        def _fake_ws(_wsdl, service, enable_logging=False):
            assert service == 'wsfe'
            calls['count'] += 1
            if calls['count'] == 1:
                raise Exception('El CEE ya posee un TA valido para el acceso al WSN solicitado')
            return _FakeWS()

        monkeypatch.setattr('arca_integration.client.ArcaWebService', _fake_ws)
        monkeypatch.setattr(client, '_has_valid_local_ta', lambda _service: True)
        monkeypatch.setattr(time, 'sleep', lambda _seconds: None)

        ws = client.wsfe

        assert isinstance(ws, _FakeWS)
        assert calls['count'] == 2


class _FakeResultNode:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeWSForLogs:
    def __init__(self):
        self.token = 'token-test-123'
        self.sign = 'sign-test-456'
        self.cuit = '20409378472'
        self.last_data = None

    def get_type(self, _name):
        return {}

    def send_request(self, _method_name, data):
        self.last_data = data
        det = _FakeResultNode(
            CAE='86080011696158',
            CAEFchVto='20260307',
            CbteDesde=483,
            Resultado='A',
            Observaciones=None,
        )
        return _FakeResultNode(
            FeCabResp=_FakeResultNode(Resultado='A', Reproceso='N'),
            FeDetResp=_FakeResultNode(FECAEDetResponse=[det]),
            Errors=None,
        )


class TestArcaVerboseLogs:
    def test_logs_request_response_when_enabled_and_omits_token_sign(self, monkeypatch, caplog):
        monkeypatch.setenv('ARCA_VERBOSE_LOGS', 'true')
        monkeypatch.setenv('ARCA_VERBOSE_INCLUDE_RAW', 'true')
        monkeypatch.setenv('FLASK_ENV', 'development')

        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        fake_ws = _FakeWSForLogs()
        client._wsfe = fake_ws

        request_data = {
            'FeCAEReq': {
                'FeCabReq': {'CantReg': 1, 'PtoVta': 1, 'CbteTipo': 1},
                'FeDetReq': {
                    'FECAEDetRequest': {
                        'Concepto': 1,
                        'DocTipo': 80,
                        'DocNro': 33693450239,
                    }
                },
            }
        }

        with caplog.at_level(logging.INFO, logger='arca_integration.client'):
            response = client.fe_cae_solicitar(request_data)

        assert response['resultado'] == 'A'
        logs = [r.message for r in caplog.records if r.message.startswith('ARCA_VERBOSE ')]
        assert logs, 'Se esperaba al menos un log ARCA_VERBOSE'

        payloads = [json.loads(entry.split('ARCA_VERBOSE ', 1)[1]) for entry in logs]
        request_payload = next(p for p in payloads if p.get('event') == 'arca.ws.request' and p.get('method') == 'FECAESolicitar')

        assert request_payload['environment'] == 'dev'
        assert request_payload['wsid'] == 'wsfe'
        assert request_payload['params']['Auth']['Cuit'] == '20409378472'
        assert 'Token' not in request_payload['params']['Auth']
        assert 'Sign' not in request_payload['params']['Auth']

        response_payloads = [p for p in payloads if p.get('event') == 'arca.ws.response' and p.get('method') == 'FECAESolicitar']
        assert any(p.get('stage') == 'raw' for p in response_payloads)
        assert any(p.get('stage') == 'parsed' for p in response_payloads)

    def test_skips_raw_response_stage_when_include_raw_disabled(self, monkeypatch, caplog):
        monkeypatch.setenv('ARCA_VERBOSE_LOGS', 'true')
        monkeypatch.setenv('ARCA_VERBOSE_INCLUDE_RAW', 'false')

        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        client._wsfe = _FakeWSForLogs()

        request_data = {
            'FeCAEReq': {
                'FeCabReq': {'CantReg': 1, 'PtoVta': 1, 'CbteTipo': 1},
                'FeDetReq': {'FECAEDetRequest': {'Concepto': 1, 'DocTipo': 80, 'DocNro': 33693450239}},
            }
        }

        with caplog.at_level(logging.INFO, logger='arca_integration.client'):
            client.fe_cae_solicitar(request_data)

        logs = [r.message for r in caplog.records if r.message.startswith('ARCA_VERBOSE ')]
        payloads = [json.loads(entry.split('ARCA_VERBOSE ', 1)[1]) for entry in logs]
        response_payloads = [p for p in payloads if p.get('event') == 'arca.ws.response' and p.get('method') == 'FECAESolicitar']

        assert not any(p.get('stage') == 'raw' for p in response_payloads)
        assert any(p.get('stage') == 'parsed' for p in response_payloads)

    def test_does_not_log_when_disabled(self, monkeypatch, caplog):
        monkeypatch.setenv('ARCA_VERBOSE_LOGS', 'false')

        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        client._wsfe = _FakeWSForLogs()

        request_data = {
            'FeCAEReq': {
                'FeCabReq': {'CantReg': 1, 'PtoVta': 1, 'CbteTipo': 1},
                'FeDetReq': {'FECAEDetRequest': {'Concepto': 1, 'DocTipo': 80, 'DocNro': 33693450239}},
            }
        }

        with caplog.at_level(logging.INFO, logger='arca_integration.client'):
            client.fe_cae_solicitar(request_data)

        logs = [r.message for r in caplog.records if r.message.startswith('ARCA_VERBOSE ')]
        assert not logs

    def test_ws_constancia_applies_same_ta_fallback(self, monkeypatch):
        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        calls = {'count': 0}

        class _FakeWS:
            pass

        def _fake_ws(_wsdl, service, enable_logging=False):
            assert service == 'ws_sr_constancia_inscripcion'
            calls['count'] += 1
            if calls['count'] == 1:
                raise Exception('El CEE ya posee un TA valido para el acceso al WSN solicitado')
            return _FakeWS()

        monkeypatch.setattr('arca_integration.client.ArcaWebService', _fake_ws)
        monkeypatch.setattr(client, '_has_valid_local_ta', lambda _service: True)
        monkeypatch.setattr(time, 'sleep', lambda _seconds: None)

        ws = client.ws_constancia

        assert isinstance(ws, _FakeWS)
        assert calls['count'] == 2

    def test_wsfe_fallback_handles_accented_valido_message(self, monkeypatch):
        client = ArcaClient(
            cuit='20123456789',
            cert=b'cert',
            key=b'key',
            ambiente='testing',
        )

        calls = {'count': 0}

        class _FakeWS:
            pass

        def _fake_ws(_wsdl, service, enable_logging=False):
            assert service == 'wsfe'
            calls['count'] += 1
            if calls['count'] == 1:
                raise Exception('El CEE ya posee un TA válido para el acceso al WSN solicitado')
            return _FakeWS()

        monkeypatch.setattr('arca_integration.client.ArcaWebService', _fake_ws)
        monkeypatch.setattr(client, '_has_valid_local_ta', lambda _service: True)
        monkeypatch.setattr(time, 'sleep', lambda _seconds: None)

        ws = client.wsfe

        assert isinstance(ws, _FakeWS)
        assert calls['count'] == 2
