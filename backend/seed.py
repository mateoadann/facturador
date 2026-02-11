"""
Script para crear datos iniciales (tenant + usuario admin).
Ejecutar: python seed.py
"""
from app import create_app
from app.extensions import db
from app.models import Tenant, Usuario

app = create_app()

with app.app_context():
    db.create_all()

    # Verificar si ya existe
    existing = Tenant.query.filter_by(slug='demo').first()
    if existing:
        print('Seed ya ejecutado. Tenant "demo" existe.')
    else:
        # Crear tenant
        tenant = Tenant(
            nombre='Demo',
            slug='demo',
            activo=True
        )
        db.session.add(tenant)
        db.session.flush()

        # Crear usuario admin
        admin = Usuario(
            tenant_id=tenant.id,
            email='admin@facturador.local',
            nombre='Admin',
            rol='admin',
            activo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # Crear usuario operador
        operator = Usuario(
            tenant_id=tenant.id,
            email='operador@facturador.local',
            nombre='Operador',
            rol='operator',
            activo=True
        )
        operator.set_password('operador123')
        db.session.add(operator)

        # Crear usuario viewer
        viewer = Usuario(
            tenant_id=tenant.id,
            email='viewer@facturador.local',
            nombre='Viewer',
            rol='viewer',
            activo=True
        )
        viewer.set_password('viewer123')
        db.session.add(viewer)

        db.session.commit()

        print(f'Tenant creado: {tenant.nombre} (ID: {tenant.id})')
        print(f'Usuario admin: {admin.email} / admin123')
        print(f'Usuario operador: {operator.email} / operador123')
        print(f'Usuario viewer: {viewer.email} / viewer123')
        print('Seed completado.')
