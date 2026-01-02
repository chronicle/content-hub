from __future__ import annotations

import datetime

from integration_testing.set_meta import set_metadata
from sample_integration.jobs import simple_job_example
from sample_integration.tests.common import (
    CONFIG,
    CONFIG_PATH,
    GET_CASE_DETAILS,
    MOCK_RATES_DEFAULT,
)
from sample_integration.tests.core.product import VatComply
from sample_integration.tests.core.session import VatComplySession

DEFAULT_PARAMETERS: dict[str, str] = CONFIG.copy()
DEFAULT_PARAMETERS["Verify SSL"] = "True"
CASE_ID: int = 1
TAG_1: str = "Closed"
TAG_2: str = "Currency"


@set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
def test_simple_job_example_success(
    script_session: VatComplySession,
    vatcomply: VatComply,
) -> None:
    # Arrange
    today: str = datetime.date.today().isoformat()
    MOCK_RATES_DEFAULT["date"]: str = today
    vatcomply.set_rates(MOCK_RATES_DEFAULT)
    vatcomply.add_case_details(CASE_ID, GET_CASE_DETAILS)
    vatcomply.add_tag(CASE_ID, TAG_1)
    vatcomply.add_tag(CASE_ID, TAG_2)

    # Act
    simple_job_example.main()

    # Assert
    assert len(script_session.request_history) == 3
    request_1 = script_session.request_history[0].request
    assert request_1.url.path.endswith("/GetCasesIdByFilter")
    request_2 = script_session.request_history[1].request
    assert request_2.url.path.endswith(f"/GetCaseDetails/{CASE_ID}")
    request_3 = script_session.request_history[2].request
    assert request_3.url.path.endswith("/Close")
