from __future__ import annotations

import datetime

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity

from sample_integration.actions import enrich_entity_action_example
from sample_integration.tests.common import CONFIG_PATH, MOCK_RATES_DEFAULT
from sample_integration.tests.core.product import VatComply
from sample_integration.tests.core.session import VatComplySession

DEFAULT_PARAMETERS: dict[str, str] = {
    "Entity Type": "All Entities",
}
USERNAME_ENTITY_ID: str = "abcd@x.com"
USERNAME_ENTITY_1: Entity = create_entity(USERNAME_ENTITY_ID, EntityTypesEnum.USER)
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
    entities=[USERNAME_ENTITY_1],
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_enrich_entity_action_example_success(
    script_session: VatComplySession,
    action_output: MockActionOutput,
    vatcomply: VatComply,
) -> None:
    # Arrange
    today: str = datetime.date.today().isoformat()
    MOCK_RATES_DEFAULT["date"]: str = today
    vatcomply.set_rates(MOCK_RATES_DEFAULT)
    success_output_msg = (
        f"Successfully enriched the following entities: {USERNAME_ENTITY_ID.upper()}"
    )

    # Act
    enrich_entity_action_example.main()

    # Assert
    assert len(script_session.request_history) == 1
    assert action_output.results.output_message == success_output_msg
    assert action_output.results.execution_state == ExecutionState.COMPLETED
