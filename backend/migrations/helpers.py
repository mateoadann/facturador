"""Helpers para migraciones idempotentes.

Provee funciones para verificar si columnas, constraints y tablas ya existen
antes de crearlas/eliminarlas, evitando errores cuando la DB ya tiene los cambios.
"""

from alembic import op
from sqlalchemy import inspect


def _get_inspector():
    bind = op.get_bind()
    return inspect(bind)


def column_exists(table_name, column_name):
    inspector = _get_inspector()
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name):
    inspector = _get_inspector()
    return table_name in inspector.get_table_names()


def constraint_exists(table_name, constraint_name):
    inspector = _get_inspector()
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def fk_exists(table_name, constraint_name):
    inspector = _get_inspector()
    fks = inspector.get_foreign_keys(table_name)
    return any(fk['name'] == constraint_name for fk in fks)
