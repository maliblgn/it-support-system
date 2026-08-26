from collections.abc import Generator
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


def _configure_sqlite_connection(
    dbapi_connection: Any,
    _connection_record: Any,
) -> None:
    """Test veritabanına MSSQL şemasında kullanılan işlevlerin karşılıklarını ekler."""
    dbapi_connection.create_function(
        "LEN",
        1,
        lambda value: len(value.rstrip()) if value is not None else None,
        deterministic=True,
    )
    dbapi_connection.create_function(
        "SYSUTCDATETIME",
        0,
        lambda: datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="milliseconds"),
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    database_uri = settings.sqlalchemy_database_uri
    engine_options: dict[str, object] = {"pool_pre_ping": True}

    if database_uri.startswith("sqlite"):
        engine_options.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine_options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )

    engine = create_engine(database_uri, **engine_options)
    if database_uri.startswith("sqlite"):
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def dispose_engine() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
