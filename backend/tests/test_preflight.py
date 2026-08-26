from pathlib import Path

import pytest

from app.cli.preflight import check_upload_root


def test_upload_preflight_accepts_writable_directory(tmp_path: Path) -> None:
    check_upload_root(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_upload_preflight_rejects_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(RuntimeError, match="Dosya depolama klasörü bulunamadı"):
        check_upload_root(missing)
