import os

import pytest

os.environ.setdefault("APP_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("APP_LOG_FILE", "")
os.environ.setdefault("APP_ALLOWED_EMAIL_DOMAINS", '["company.com"]')

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import dispose_engine, get_engine  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_database() -> None:
    """Her test için temiz ve paylaşımlı bir bellek içi SQLite şeması sağlar."""
    get_settings.cache_clear()
    dispose_engine()
    engine = get_engine()
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    dispose_engine()
    get_settings.cache_clear()
