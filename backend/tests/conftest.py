import os
import shutil
import tempfile
import pytest
from pathlib import Path

# Threading & TF optimizations
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

# Create an isolated temporary directory and database file for the test session
_test_dir = tempfile.mkdtemp(prefix="cricketiq_test_db_")
_test_db = Path(_test_dir) / "test_cricketiq.db"

# Set environment variables immediately at conftest load time before any module imports
os.environ["DATABASE_URL"] = str(_test_db)
os.environ["DB_PATH"] = str(_test_db)

from backend.app.core.config import settings
from backend.app.repositories.session_repository import session_repo

# Explicitly point settings and session_repo to the temporary database
settings.DB_PATH = _test_db
session_repo.set_db_path(_test_db)


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """
    Guarantees that every test in the suite operates on the temporary database.
    Verifies that the production database path is not being used.
    """
    real_db_path = settings.STORAGE_DIR / "cricketiq.db"
    assert Path(settings.DB_PATH).resolve() != real_db_path.resolve(), (
        f"CRITICAL: Tests must not use production database {real_db_path}!"
    )
    assert Path(session_repo.db_path).resolve() != real_db_path.resolve(), (
        f"CRITICAL: session_repo must not use production database {real_db_path}!"
    )
    
    yield _test_db

    # Clean up test database directory after all tests complete
    try:
        shutil.rmtree(_test_dir, ignore_errors=True)
    except Exception:
        pass
