"""
Seed de datos para E2E tests.
Garantiza un estado predecible para los tests de Playwright.

Ejecutar: python seed_e2e.py
Requiere: tenant "demo" ya existente (creado por seed.py).
"""
from app import create_app
from app.extensions import db
from app.models import Tenant, Usuario

app = create_app()

with app.app_context():
    tenant = Tenant.query.filter_by(slug='demo').first()
    if not tenant:
        print('ERROR: Tenant "demo" no existe. Ejecutá seed.py primero.')
        exit(1)

    # ── Resetear passwords y estado de usuarios conocidos ─────────────────
    users = {
        'admin@facturador.local': ('Admin', 'admin', 'admin123'),
        'operador@facturador.local': ('Operador', 'operator', 'operador123'),
        'viewer@facturador.local': ('Viewer', 'viewer', 'viewer123'),
    }

    for email, (nombre, rol, password) in users.items():
        user = Usuario.query.filter_by(email=email, tenant_id=tenant.id).first()
        if user:
            user.set_password(password)
            user.login_attempts = 0
            user.locked_until = None
            user.activo = True
            print(f'  Reset: {email} / {password}')
        else:
            user = Usuario(
                tenant_id=tenant.id,
                email=email,
                nombre=nombre,
                rol=rol,
                activo=True,
            )
            user.set_password(password)
            db.session.add(user)
            print(f'  Creado: {email} / {password}')

    # ── Limpiar datos de tests anteriores ─────────────────────────────────
    # Eliminar facturadores de test
    from app.models import Facturador
    test_facturadores = Facturador.query.filter(
        Facturador.cuit.in_(['20999999990', '20888888880']),
        Facturador.tenant_id == tenant.id,
    ).all()
    for f in test_facturadores:
        db.session.delete(f)
        print(f'  Eliminado facturador test: {f.cuit}')

    # Eliminar receptores de test
    from app.models import Receptor
    test_receptores = Receptor.query.filter(
        Receptor.doc_nro.in_(['20888888880']),
        Receptor.tenant_id == tenant.id,
    ).all()
    for r in test_receptores:
        db.session.delete(r)
        print(f'  Eliminado receptor test: {r.doc_nro}')

    # Eliminar usuarios de test
    test_users = Usuario.query.filter(
        Usuario.email.like('e2e-%'),
        Usuario.tenant_id == tenant.id,
    ).all()
    for u in test_users:
        db.session.delete(u)
        print(f'  Eliminado usuario test: {u.email}')

    # Eliminar lotes de test (E2E-*)
    from app.models import Lote, Factura, FacturaItem
    test_lotes = Lote.query.filter(
        Lote.etiqueta.like('E2E-%'),
        Lote.tenant_id == tenant.id,
    ).all()
    for lote in test_lotes:
        facturas = Factura.query.filter_by(lote_id=lote.id).all()
        for factura in facturas:
            FacturaItem.query.filter_by(factura_id=factura.id).delete()
            db.session.delete(factura)
        db.session.delete(lote)
        print(f'  Eliminado lote test: {lote.etiqueta}')

    db.session.commit()
    print('\nSeed E2E completado.')
