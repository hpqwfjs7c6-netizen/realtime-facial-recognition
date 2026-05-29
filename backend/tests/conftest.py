import os
import tempfile

import pytest

# Configure l'environnement AVANT l'import de la config/app.
_TMP = tempfile.mkdtemp(prefix="frt_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ["REFERENCES_DIR"] = os.path.join(_TMP, "refs")
os.environ["AZURE_FACE_ENDPOINT"] = "https://example.test"
os.environ["AZURE_FACE_KEY"] = "test-key"
os.environ["RECOGNITION_ACTION"] = "log"
os.environ["API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402


@pytest.fixture()
def client():
    database.init_db()
    with TestClient(main.app) as c:
        yield c
