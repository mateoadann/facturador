import os
import pickle
import time
import tempfile

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
