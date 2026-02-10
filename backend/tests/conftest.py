import pytest
import uuid
from app import create_app
from app.extensions import db as _db
from app.config import TestingConfig
from app.models import Tenant, Usuario, Facturador, Receptor


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    return app


@pytest.fixture(scope='function')
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Test client."""
    return app.test_client()


@pytest.fixture
def tenant(db):
    """Create a test tenant."""
    t = Tenant(
        nombre='Test Tenant',
        slug='test-tenant',
        activo=True
    )
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def admin_user(db, tenant):
    """Create an admin user."""
    user = Usuario(
        tenant_id=tenant.id,
        email='admin@test.com',
        nombre='Admin Test',
        rol='admin',
        activo=True
    )
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def operator_user(db, tenant):
    """Create an operator user."""
    user = Usuario(
        tenant_id=tenant.id,
        email='operator@test.com',
        nombre='Operator Test',
        rol='operator',
        activo=True
    )
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def facturador(db, tenant):
    """Create a test facturador."""
    f = Facturador(
        tenant_id=tenant.id,
        cuit='20123456789',
        razon_social='Test SA',
        punto_venta=1,
        condicion_iva='IVA Responsable Inscripto',
        ambiente='testing',
        activo=True
    )
    db.session.add(f)
    db.session.commit()
    return f


@pytest.fixture
def receptor(db, tenant):
    """Create a test receptor."""
    r = Receptor(
        tenant_id=tenant.id,
        doc_tipo=80,
        doc_nro='30111111111',
        razon_social='Receptor SA',
        condicion_iva='IVA Responsable Inscripto',
        activo=True
    )
    db.session.add(r)
    db.session.commit()
    return r


@pytest.fixture
def auth_headers(client, admin_user):
    """Get auth headers for admin user."""
    response = client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'test123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def operator_headers(client, operator_user):
    """Get auth headers for operator user."""
    response = client.post('/api/auth/login', json={
        'email': 'operator@test.com',
        'password': 'test123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}
