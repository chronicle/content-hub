
"""
Tests configuration file
"""
import pytest
from _pytest.monkeypatch import MonkeyPatch
from rsa_net_witness_edr.core.RSAManager import (
    RSAManager,
)
from rsa_net_witness_edr.core.RSAExceptions import (
    RSAError,
)


@pytest.fixture
def mock_get_endpoint_details_to_raise_manager_error(
    monkeypatch: MonkeyPatch
) -> None:
    """
    Mock the test get endpoint details function to raise
    RSANetWitnessEDR error
    """
    def mock_raise_manager_error(*args: list, **kwargs: dict) -> None:
        raise RSAError("Connectivity error")
    monkeypatch.setattr(
        RSAManager,
        "get_endpoint_details",
        mock_raise_manager_error,
    )