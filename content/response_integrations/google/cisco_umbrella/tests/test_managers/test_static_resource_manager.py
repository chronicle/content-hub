from itertools import islice
from unittest.mock import Mock
from pathlib import Path
import pytest
import requests
from cisco_umbrella.core.CiscoUmbrellaStaticResourcesManager import (
    CiscoUmbrellaStaticResourcesManager,
    StaticAssets,
)
from cisco_umbrella.core.exceptions import CiscoUmbrellaManagerError

CURRENT_PATH = Path(__file__).parent
TEST_CSV_ZIP_PATH = CURRENT_PATH / "../resources/top-1m.csv.zip"


@pytest.fixture(name="session")
def get_session() -> requests.Session:
    session = Mock(requests.Session)
    return session


@pytest.fixture(name="manager")
def get_manager(session: requests.Session) -> CiscoUmbrellaStaticResourcesManager:
    return CiscoUmbrellaStaticResourcesManager(session=session)


def read_resource_file(name: str) -> bytes:
    with open(name, "rb") as f:
        return f.read()


@pytest.mark.parametrize(
    "asset", [StaticAssets.TOP_1M_CSV_ZIP, StaticAssets.TOP_1M_TLD_CSV_ZIP]
)
def test_fetch_static_asset(
    manager: CiscoUmbrellaStaticResourcesManager,
    session: requests.Session,
    asset: StaticAssets,
):
    # GIVEN
    response_mock = Mock(requests.Response)
    response_mock.status_code = 200
    response_mock.content = read_resource_file(TEST_CSV_ZIP_PATH)
    session.get.return_value = response_mock

    # WHEN
    resp = manager.get_asset(asset)
    results = list(islice(resp, 10))

    # THEN
    assert len(results) == 10
    assert results[0].domain == "google.com"


@pytest.mark.parametrize(
    "asset", [StaticAssets.TOP_1M_CSV_ZIP, StaticAssets.TOP_1M_TLD_CSV_ZIP]
)
def test_failed_fetch_static_asset(
    manager: CiscoUmbrellaStaticResourcesManager,
    session: requests.Session,
    asset: StaticAssets,
):
    # GIVEN
    response_mock = Mock(requests.Response)
    response_mock.status_code = 400
    response_mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Bad Request"
    )
    session.get.return_value = response_mock

    # WHEN
    with pytest.raises(CiscoUmbrellaManagerError) as error_info:
        _ = next(manager.get_asset(asset))

    # THEN
    assert error_info.type == CiscoUmbrellaManagerError
