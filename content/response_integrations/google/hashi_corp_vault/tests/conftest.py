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
from hashi_corp_vault.core.HashiCorpVaultManager import HashiCorpVaultManager

import pytest
import json


@pytest.fixture(scope="module")
def manager_fixture():
    with open("config.json", "r") as f:
        data = f.read()

    config = json.loads(data)

    api_root = config.get("API Root")
    token = config.get("Token")
    username = config.get("Username")
    password = config.get("Password")
    verify_ssl = config.get("Verify SSL")
    key_value_secret_engine_path = config.get("Key-Value Secret Engine Path")

    yield HashiCorpVaultManager(
        api_root,
        token,
        username,
        password,
        verify_ssl,
        key_value_secret_engine_path
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
