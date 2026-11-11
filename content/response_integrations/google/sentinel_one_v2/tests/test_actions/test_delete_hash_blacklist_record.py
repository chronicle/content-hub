from __future__ import annotations

import pathlib

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.types import Entity, SingleJson

from sentinel_one_v2.actions import DeleteHashBlacklistRecord
from sentinel_one_v2.tests.core.product import SentinelOneV2
from sentinel_one_v2.tests.core.session import SentinelOneV2Session
from integration_testing.common import create_entity, get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CONFIG_FILE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "config.json"
INTEGRATION_CONFIG: SingleJson = get_def_file_content(CONFIG_FILE_PATH)

# Must be a SHA1 (40 hex chars) for the action to attempt deletion
TEST_HASH: str = "aaabbbcccddd1234aaabbbcccddd1234aaabbbcc"
HASH_ENTITY: Entity = create_entity(identifier=TEST_HASH, type_=EntityTypesEnum.FILE_HASH)

ACTION_PARAMETERS: dict[str, str | bool] = {
    "Site IDs": "site_001",
    "Group IDs": "",
    "Account IDs": "",
    "Remove from global black list": False,
}

ACTION_PARAMETERS_NO_SCOPE: dict[str, str | bool] = {
    "Site IDs": "",
    "Group IDs": "",
    "Account IDs": "",
    "Remove from global black list": False,
}


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HASH_ENTITY],
)
def test_delete_hash_blacklist_success(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    DeleteHashBlacklistRecord.main()
    # Hash is found in mock restrictions response and deleted
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters=ACTION_PARAMETERS_NO_SCOPE,
    integration_config=INTEGRATION_CONFIG,
    entities=[HASH_ENTITY],
)
def test_delete_hash_blacklist_no_scope_fails(
    _script_session: SentinelOneV2Session,
    action_output: MockActionOutput,
) -> None:
    DeleteHashBlacklistRecord.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    parameters=ACTION_PARAMETERS,
    integration_config=INTEGRATION_CONFIG,
    entities=[HASH_ENTITY],
)
def test_delete_hash_blacklist_api_error(
    sentinel_one_v2: SentinelOneV2,
    action_output: MockActionOutput,
) -> None:
    sentinel_one_v2.simulate_api_error = True
    DeleteHashBlacklistRecord.main()
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
