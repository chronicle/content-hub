from __future__ import annotations
import json
from integration_testing.common import get_def_file_content

import copy
import pathlib
from typing import Any

from TIPCommon.types import SingleJson

from g_suite.core.GSuiteParser import GSuiteParser
from g_suite.core.datamodels import (
    Browser,
    ExtensionDetails,
    OrgUnit,
    RequestingDevice,
    RequestingUser,
    ResolvedPolicy,
    UserActivityEvent,
)
from integration_testing.common import get_def_file_content

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"

CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

HOST_BROWSER_DETAILS_RESPONSE: Any = MOCK_DATA["host_browser_details"]
EXTENSION_DETAILS_RESPONSE: Any = MOCK_DATA["extension_details"]
USER_DETAILS_RESPONSE: Any = MOCK_DATA["user_details"]["userDetails"][0]
DEVICE_DETAILS_RESPONSE: Any = MOCK_DATA["device_details"]["deviceDetails"][0]
OU_DETAILS_RESPONSE: Any = MOCK_DATA["ou_details"]
SEARCH_USER_ACTIVITY_EVENTS_RAW: list[SingleJson] = MOCK_DATA[
    "search_user_activity_events_raw"
]

SEARCH_USER_ACTIVITY_EVENTS_MOCK: list[UserActivityEvent] = [
    GSuiteParser.build_user_activity_event_obj(event)
    for event in SEARCH_USER_ACTIVITY_EVENTS_RAW
]

HOST_BROWSER_DETAILS_DATA: Browser = GSuiteParser.build_browser_obj(
    HOST_BROWSER_DETAILS_RESPONSE,
)

EXTENSION_DETAILS_DATA: ExtensionDetails = GSuiteParser.build_extension_details_obj(
    EXTENSION_DETAILS_RESPONSE
)

USER_DETAILS_DATA: RequestingUser = GSuiteParser.build_requesting_user_obj(
    USER_DETAILS_RESPONSE
)

DEVICE_DETAILS_DATA: RequestingDevice = GSuiteParser.build_requesting_device_obj(
    DEVICE_DETAILS_RESPONSE
)

OU_DETAILS_DATA: list[OrgUnit] = GSuiteParser.build_org_units_objs(OU_DETAILS_RESPONSE)
ORG_UNIT_ID: str = OU_DETAILS_DATA[0].org_unit_id.split(":")[-1]
ORG_UNIT_NAME: str = OU_DETAILS_DATA[0].name

BLOCKED_POLICY_DATA: ResolvedPolicy = ResolvedPolicy(
    MOCK_DATA["resolved_policies"]["blocked"]
)
ALLOWED_POLICY_DATA: ResolvedPolicy = ResolvedPolicy(
    MOCK_DATA["resolved_policies"]["allowed"]
)
REMOVED_POLICY_DATA: ResolvedPolicy = ResolvedPolicy(
    MOCK_DATA["resolved_policies"]["removed"]
)


def get_direct_blocked_policy() -> ResolvedPolicy:
    """Returns a deep copy of the direct blocked policy.

    The returned policy has the ORG_UNIT_ID formatted. This prevents side effects
    across tests that might modify the object.

    Returns:
        ResolvedPolicy: A deep copy of the direct blocked policy.
    """
    policy_data: SingleJson = copy.deepcopy(
        MOCK_DATA["resolved_policies"]["blocked_direct"]
    )
    policy_data["sourceKey"]["targetResource"] = policy_data["sourceKey"][
        "targetResource"
    ].format(org_unit_id=ORG_UNIT_ID)
    return ResolvedPolicy(policy_data)
