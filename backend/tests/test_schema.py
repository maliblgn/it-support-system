from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateTable

from app.db.base import Base


def compile_table(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    return str(CreateTable(table).compile(dialect=mssql.dialect()))


def test_mssql_uses_datetime2_and_nvarchar_max() -> None:
    users_ddl = compile_table("users")
    tickets_ddl = compile_table("tickets")

    assert "DATETIME2(3)" in users_ddl
    assert "NVARCHAR(max)" in tickets_ddl
    assert "NTEXT" not in tickets_ddl


def test_constraint_names_match_data_dictionary() -> None:
    tickets_ddl = compile_table("tickets")

    assert "CK_tickets_priority" in tickets_ddl
    assert "CK_tickets_resolution_consistency" in tickets_ddl
    assert "CK_tickets_resolved_priority" in tickets_ddl
