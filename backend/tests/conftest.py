import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so config.settings can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set default environment variables for testing
_TEST_ENV_DEFAULTS = {
    "MONGO_URI": "mongodb://test:test@localhost:27017/",
    "MONGO_DB_NAME": "test_jav",
    "MONGO_CONNECT_TIMEOUT_MS": "5000",
    "MAX_LIST_PAGES": "10",
    "LIST_PAGE_DELAY_MIN": "1.0",
    "LIST_PAGE_DELAY_MAX": "2.0",
    "DETAIL_PAGE_DELAY_MIN": "0.5",
    "DETAIL_PAGE_DELAY_MAX": "1.0",
    "SECURITY_WAIT_SECONDS": "30",
    "REQUEST_TIMEOUT": "30",
    "USE_DYNAMIC_FETCHER": "false",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)


@pytest.fixture
def client():
    # Import the app module first
    import app.main as main_module

    # Patch the local references in main.py so the lifespan doesn't need MongoDB
    with patch.object(main_module, "connect_mongo", return_value=MagicMock()), \
         patch.object(main_module, "close_mongo", return_value=None):
        with TestClient(main_module.app) as c:
            yield c
