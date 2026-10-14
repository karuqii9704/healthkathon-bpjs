"""Guard GR-13: tes hanya boleh jalan terhadap DB yang namanya berakhiran _test."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest


def _db_name(url: str) -> str:
    return urlparse(url).path.lstrip("/").split("?")[0]


def pytest_configure(config: pytest.Config) -> None:
    url = os.environ.get("DATABASE_URL", "")
    if url and not _db_name(url).endswith("_test"):
        pytest.exit(
            f"DATABASE_URL menunjuk DB '{_db_name(url)}', bukan *_test. Tes dihentikan (GR-13).",
            returncode=4,
        )


@pytest.fixture(scope="session")
def db_url() -> str:
    """URL admin ke DB *_test yang sudah dimigrasi. Tes DB gagal jelas bila DATABASE_URL kosong."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.fail("Tes DB butuh DATABASE_URL ke DB *_test (lihat README).")
    from scripts.migrate import migrate

    migrate(url)
    return url
