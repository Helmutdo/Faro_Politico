#!/usr/bin/env python3
"""Inspecciona el catálogo de una instancia PostgreSQL real."""

import json
from typing import Any

from sqlalchemy import inspect, text
from trama_publica.db.session import create_database_engine


def inspect_schema() -> dict[str, Any]:
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        raise RuntimeError("inspect_postgres_schema requires PostgreSQL")
    inspector = inspect(engine)
    tables: dict[str, Any] = {}
    for table_name in sorted(
        name for name in inspector.get_table_names() if name != "alembic_version"
    ):
        columns = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "timezone": getattr(column["type"], "timezone", None),
                "nullable": column["nullable"],
                "default": str(column["default"]) if column["default"] else None,
            }
            for column in inspector.get_columns(table_name)
        ]
        foreign_keys = []
        for foreign_key in inspector.get_foreign_keys(table_name):
            foreign_keys.append(
                {
                    "name": foreign_key["name"],
                    "columns": foreign_key["constrained_columns"],
                    "referred_table": foreign_key["referred_table"],
                    "referred_columns": foreign_key["referred_columns"],
                    "on_delete": foreign_key.get("options", {}).get(
                        "ondelete", "NO ACTION"
                    ),
                }
            )
        tables[table_name] = {
            "columns": columns,
            "primary_key": inspector.get_pk_constraint(table_name),
            "foreign_keys": foreign_keys,
            "checks": inspector.get_check_constraints(table_name),
            "unique_constraints": inspector.get_unique_constraints(table_name),
            "indexes": inspector.get_indexes(table_name),
        }
    with engine.connect() as connection:
        version = connection.scalar(text("SHOW server_version"))
        database = connection.scalar(text("SELECT current_database()"))
        user = connection.scalar(text("SELECT current_user"))
    return {
        "postgresql_version": version,
        "database": database,
        "user": user,
        "table_count": len(tables),
        "tables": tables,
    }


def main() -> None:
    print(json.dumps(inspect_schema(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
