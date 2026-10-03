"""Compatibility for immutable revisions that explicitly create PostgreSQL enums."""
from contextlib import contextmanager

from sqlalchemy import Table, event, text
from sqlalchemy.dialects.postgresql import ENUM


@contextmanager
def existing_enum_guard(connection):
    """Avoid implicit duplicate CREATE TYPE after a revision's explicit enum.create()."""
    def before_table_create(table, bind, **kwargs):
        for column in table.columns:
            enum = column.type
            if not isinstance(enum, ENUM):
                continue
            if bind.dialect.has_type(bind, enum.name, schema=enum.schema):
                labels = bind.execute(text(
                    'SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid=e.enumtypid '
                    'JOIN pg_namespace n ON n.oid=t.typnamespace '
                    'WHERE t.typname=:name AND n.nspname=COALESCE(:schema,current_schema()) '
                    'ORDER BY e.enumsortorder'
                ), {'name': enum.name, 'schema': enum.schema}).scalars().all()
                if list(enum.enums) != labels:
                    raise RuntimeError(f'Existing enum definition differs: {enum.name}')
                enum.create_type = False
    if connection.dialect.name != 'postgresql':
        yield
        return
    event.listen(Table, 'before_create', before_table_create)
    try:
        yield
    finally:
        event.remove(Table, 'before_create', before_table_create)
