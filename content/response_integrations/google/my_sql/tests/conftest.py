pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout
import pytest

from my_sql.tests.core.session import MySQLSession
from my_sql.core import MySQLManager


@pytest.fixture(autouse=True)
def mysql_session(monkeypatch: pytest.MonkeyPatch) -> MySQLSession:
    """Mock MySQL session connection"""
    session = MySQLSession()

    monkeypatch.setattr(
        MySQLManager.mysql.connector, "connect", lambda **kwargs: session
    )

    yield session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
