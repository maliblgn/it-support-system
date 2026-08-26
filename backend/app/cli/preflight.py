"""Üretim sürecini başlatmadan önce kritik bağımlılıkları doğrular."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import dispose_engine, get_engine


def check_upload_root(upload_root: Path) -> None:
    if not upload_root.is_dir():
        raise RuntimeError(f"Dosya depolama klasörü bulunamadı: {upload_root}")
    with NamedTemporaryFile(prefix=".preflight-", dir=upload_root, delete=True):
        pass


def check_database_and_revision() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        database_revision = MigrationContext.configure(connection).get_current_revision()

    config = Config("alembic.ini")
    expected_revision = ScriptDirectory.from_config(config).get_current_head()
    if database_revision != expected_revision:
        raise RuntimeError(
            "Veritabanı migration seviyesi güncel değil. "
            f"Beklenen={expected_revision}, mevcut={database_revision or 'yok'}"
        )


def main() -> int:
    settings = get_settings()
    if settings.environment.casefold() != "production":
        raise SystemExit("Preflight yalnızca APP_ENVIRONMENT=production ile çalıştırılabilir.")

    checks = [
        ("Production güvenlik ayarları", lambda: None),
        ("Dosya depolama erişimi", lambda: check_upload_root(settings.upload_root_path)),
        ("MSSQL bağlantısı ve migration seviyesi", check_database_and_revision),
    ]
    try:
        for label, check in checks:
            check()
            print(f"[OK] {label}")
    except Exception as exc:
        print(f"[HATA] {type(exc).__name__}: {exc}")
        return 1
    finally:
        dispose_engine()

    print("Üretim ön kontrolü tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
