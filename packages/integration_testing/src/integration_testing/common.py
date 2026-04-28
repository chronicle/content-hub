# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import copy
import json
import os
import pathlib
import sys
import time
from typing import TYPE_CHECKING

import yaml
from OverflowManager import OverflowManager, OverflowManagerSettings
from SiemplifyDataModel import DomainEntityInfo
from TIPCommon.base.action import CaseComment, EntityTypesEnum
from TIPCommon.base.job import JobParameter
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.data_models import (
    SLA,
    AlertCard,
    CaseDataStatus,
    CaseDetails,
    CasePriority,
    ConnectorParameter,
    DatabaseContextType,
)

from .platform.external_context import ExternalContextRow

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from TIPCommon.types import Entity, SingleJson

    from .request import MockRequest

TIP_MARKETPLACE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent.parent
INTEGRATIONS_DIR_PATH: pathlib.Path = TIP_MARKETPLACE_PATH / "Integrations"
INTEGRATION_DEF_FILE: str = "Integration-{}.def"
DEFAULT_PROCESS_TIMEOUT: int = 180

INGEST_ALERT_AS_OVERFLOW_SETTINGS: ExternalContextRow[str] = ExternalContextRow(
    context_type=DatabaseContextType.CONNECTOR,
    identifier=OverflowManager.OVERFLOW_SETTINGS_IDENTIFIER,
    property_key=OverflowManager.OVERFLOW_SETTINGS_KEY,
    property_value=json.dumps(vars(OverflowManagerSettings(max_alerts_in_time_period=0))),
)
DEFAULT_OVERFLOW_SETTINGS: ExternalContextRow[str] = ExternalContextRow(
    context_type=DatabaseContextType.CONNECTOR,
    identifier=OverflowManager.OVERFLOW_SETTINGS_IDENTIFIER,
    property_key=OverflowManager.OVERFLOW_SETTINGS_KEY,
    property_value=json.dumps(vars(OverflowManagerSettings())),
)

USE_LIVE_API_ENVAR: str = "USE_LIVE_API"
BUILT_DEF_SUFFIX: str = ".yaml"
VALID_DEF_SUFFIXES: Collection[str] = (
    ".json",
    ".jobdef",
    ".def",
    ".connectordef",
    ".actiondef",
    BUILT_DEF_SUFFIX,
)


def create_case_comment(  # noqa: PLR0913, PLR0917
    comment: str,
    comment_id: int,
    case_id: int,
    alert_identifier: str,
    creator_user_id: str = "",
    comment_type: int = -1,
    modification_time_unix_time_in_ms: int | None = None,
    creation_time_unix_time_in_ms: int | None = None,
    creator_full_name: str | None = None,
    last_editor: str | None = None,
    last_editor_full_name: str | None = None,
    modification_time_unix_time_in_ms_for_client: int | None = None,
    comment_for_client: str | None = None,
    *,
    is_deleted: bool | None = None,
    is_favorite: bool = False,
) -> CaseComment:
    """Create a case comment object with default values.

    Returns:
        A CaseComment object

    """
    now: int = int(time.time()) * NUM_OF_MILLI_IN_SEC
    return CaseComment(
        comment=comment,
        comment_id=comment_id,
        case_id=case_id,
        alert_identifier=alert_identifier,
        creator_user_id=creator_user_id,
        comment_type=comment_type,
        is_favorite=is_favorite,
        modification_time_unix_time_in_ms=(
            modification_time_unix_time_in_ms
            if modification_time_unix_time_in_ms is not None
            else now
        ),
        creation_time_unix_time_in_ms=(
            creation_time_unix_time_in_ms if creation_time_unix_time_in_ms is not None else now
        ),
        creator_full_name=creator_full_name,
        is_deleted=is_deleted,
        last_editor=last_editor,
        last_editor_full_name=last_editor_full_name,
        modification_time_unix_time_in_ms_for_client=(
            modification_time_unix_time_in_ms_for_client
            if modification_time_unix_time_in_ms_for_client is not None
            else now
        ),
        comment_for_client=comment_for_client,
    )


def create_case_details(  # noqa: PLR0913, PLR0917
    id_: int,
    name: str,
    creation_time_unix_time_ms: int | None = None,
    modification_time_unix_time_ms: int | None = None,
    priority: CasePriority = CasePriority.INFORMATIVE,
    start_time_unix_time_ms: int | None = None,
    end_time_unix_time_ms: int | None = None,
    assigned_user: str = "Siemplify Admin",
    description: str | None = None,
    type_: int = 0,
    stage: str = "",
    environment: str = "Default Environment",
    status: CaseDataStatus = CaseDataStatus.NEW,
    incident_id: str | None = None,
    tags: list[str] | None = None,
    alerts: list[AlertCard] | None = None,
    sla_expiration_unix_time: int | None = None,
    sla_critical_expiration_unix_time: int | None = None,
    stage_sla_expiration_unix_time_ms: int | None = None,
    stage_sla__critical_expiration_unix_time_in_ms: int | None = None,
    sla: SLA | None = None,
    stage_sla: SLA | None = None,
    *,
    is_important: bool = False,
    is_incident: bool = False,
    is_test_case: bool = False,
    is_overflow_case: bool = False,
    is_manual_case: bool = False,
    can_open_incident: bool = False,
) -> CaseDetails:
    """Create a case details object.

    Returns:
        A CaseDetails object

    """
    now: int = int(time.time()) * NUM_OF_MILLI_IN_SEC
    return CaseDetails(
        id_=id_,
        name=name,
        creation_time_unix_time_ms=(
            creation_time_unix_time_ms if creation_time_unix_time_ms is not None else now
        ),
        modification_time_unix_time_ms=(
            modification_time_unix_time_ms if modification_time_unix_time_ms is not None else now
        ),
        priority=priority,
        is_important=is_important,
        is_incident=is_incident,
        start_time_unix_time_ms=(
            start_time_unix_time_ms if start_time_unix_time_ms is not None else now
        ),
        end_time_unix_time_ms=(end_time_unix_time_ms if end_time_unix_time_ms is not None else now),
        assigned_user=assigned_user,
        description=description,
        is_test_case=is_test_case,
        type_=type_,
        stage=stage,
        environment=environment,
        status=status,
        incident_id=incident_id,
        tags=tags if tags is not None else [],
        alerts=alerts if alerts is not None else [],
        is_overflow_case=is_overflow_case,
        is_manual_case=is_manual_case,
        sla_expiration_unix_time=sla_expiration_unix_time,
        sla_critical_expiration_unix_time=sla_critical_expiration_unix_time,
        stage_sla_expiration_unix_time_ms=stage_sla_expiration_unix_time_ms,
        stage_sla__critical_expiration_unix_time_in_ms=(
            stage_sla__critical_expiration_unix_time_in_ms
        ),
        can_open_incident=can_open_incident,
        sla=sla,
        stage_sla=stage_sla,
    )


def create_entity(  # noqa: PLR0913, PLR0917
    identifier: str,
    type_: EntityTypesEnum,
    alert_identifier: str = "Id",
    case_identifier: int = 1,
    creation_time: int = 10,
    modification_time: int = 0,
    additional_properties: SingleJson | None = None,
    *,
    is_pivot: bool = False,
    is_artifact: bool = False,
    is_enriched: bool = False,
    is_internal: bool = False,
    is_suspicious: bool = False,
    is_vulnerable: bool = False,
) -> Entity:
    """Create an entity object that has default values to parameters.

    Returns:
        An Entity object

    """
    if additional_properties is None:
        additional_properties = {"OriginalIdentifier": identifier}

    return DomainEntityInfo(
        identifier=identifier.upper(),
        entity_type=type_.value,
        is_pivot=is_pivot,
        is_artifact=is_artifact,
        is_enriched=is_enriched,
        is_internal=is_internal,
        is_suspicious=is_suspicious,
        is_vulnerable=is_vulnerable,
        alert_identifier=alert_identifier,
        case_identifier=str(case_identifier),
        creation_time=creation_time,
        modification_time=modification_time,
        additional_properties=additional_properties,
    )


def prepare_connector_params(
    connector_def_file: str | pathlib.Path | None,
    params: SingleJson,
) -> list[ConnectorParameter]:
    """Prepare connector parameters as a list of ConnectorParameter objects.

    Returns:
        A list of ConnectorParameter objects.

    """
    connector_def: SingleJson = get_def_file_content(connector_def_file)
    def_parameters: list[SingleJson] = connector_def.get("Parameters", [])
    if not def_parameters:
        def_parameters = _fill_parameter_data(params)

    def_parameters = _set_default_connector_params(def_parameters)
    return _create_connector_parameters(def_parameters, params)


def prepare_job_params(
    job_def_file: str | pathlib.Path | None,
    params: SingleJson,
) -> list[JobParameter]:
    """Prepare job parameters as a list of JobParameter objects.

    Returns:
        A list of JobParameter objects.

    """
    _remove_python_process_from_job_params(params)
    job_def: SingleJson = get_def_file_content(job_def_file)
    def_parameters: list[SingleJson] = job_def.get("Parameters", [])
    if not def_parameters:
        def_parameters = _fill_parameter_data(params)

    return _create_job_parameters(def_parameters, params)


def use_live_api() -> bool:
    """Whether to use live API requests or mocks.

    Returns:
        Whether the USE_LIVE_API environment variable is set to true.

    """
    envar: str = os.environ.get(USE_LIVE_API_ENVAR, "false")
    return envar.lower() not in {"false", "", None}


def get_def_file_content(def_file_path: str | pathlib.Path | None) -> SingleJson:
    """Get the content of a def file.

    Returns:
        the contents of an integration's definition file as a dictionary.

    Raises:
        ValueError:
            When the provided path is not of a valid JSON file.

    """
    if def_file_path is None:
        return {}

    if isinstance(def_file_path, str):
        def_file_path = pathlib.Path(def_file_path)

    if def_file_path.suffix not in VALID_DEF_SUFFIXES:
        msg: str = f"The provided config file {def_file_path} path is not a json file!"
        raise ValueError(msg)

    if def_file_path.suffix == BUILT_DEF_SUFFIX:
        return yaml.safe_load(def_file_path.read_text(encoding="utf-8"))

    return json.loads(def_file_path.read_text(encoding="utf-8"))


def set_sys_argv(args: list[str]) -> None:
    """Set 'sys.argv'."""
    sys.argv = args


def set_is_first_run_to_true() -> None:
    """Set the 'is_first_run' sys arg of async actions to True."""
    first_run_arg_num: int = 3
    if not sys.argv or len(sys.argv) < first_run_arg_num:
        set_sys_argv(["", "", ""])

    sys.argv[2] = str(True)


def set_is_first_run_to_false() -> None:
    """Set the 'is_first_run' sys arg of async actions to True."""
    first_run_arg_num: int = 3
    if not sys.argv or len(sys.argv) < first_run_arg_num:
        set_sys_argv(["", "", ""])

    sys.argv[2] = str(False)


def set_is_test_run_to_false() -> None:
    """Set the 'is_test_run' sys arg of connectors to False."""
    test_run_arg_length: int = 2
    if not sys.argv or len(sys.argv) < test_run_arg_length:
        set_sys_argv(["", "", ""])

    sys.argv[1] = str(True)


def set_is_test_run_to_true() -> None:
    """Set the 'is_test_run' sys arg of connectors to True."""
    test_run_arg_length: int = 2
    if not sys.argv or len(sys.argv) < test_run_arg_length:
        set_sys_argv(["", "", ""])

    sys.argv[1] = str(False)


def _set_default_connector_params(params: list[SingleJson]) -> list[SingleJson]:
    p: list[SingleJson] = copy.deepcopy(params)
    param_names: set[str] = {param["Name"] for param in params}

    if "PythonProcessTimeout" not in param_names:
        p.append(
            {
                "Name": "PythonProcessTimeout",
                "Type": 1,
                "DefaultValue": DEFAULT_PROCESS_TIMEOUT,
                "IsMandatory": True,
                "Mode": 2,
            },
        )

    return p


def _fill_parameter_data(parameters: SingleJson) -> list[SingleJson]:
    return [
        {
            "IsMandatory": False,
            "Type": 2,
            "Mode": 0,
            "Name": param_name,
            "DefaultValue": param_value,
        }
        for param_name, param_value in parameters.items()
    ]


def _remove_python_process_from_job_params(params: SingleJson) -> None:
    if "PythonProcessTimeout" in params:
        del params["PythonProcessTimeout"]


def _create_connector_parameters(
    def_parameters: list[SingleJson],
    params: SingleJson,
) -> list[ConnectorParameter]:
    """Create a connector parameters list made out of parameters and def parameters.

    Returns:
        A list of ConnectorParameter objects.

    """
    results: list[ConnectorParameter] = []
    for parameter in def_parameters:
        parameter["param_name"] = parameter["Name"]
        parameter["param_value"] = params.get(
            parameter["Name"],
            parameter["DefaultValue"],
        )
        parameter["is_mandatory"] = parameter["IsMandatory"]
        parameter["type"] = parameter["Type"]
        parameter["mode"] = parameter["Mode"]

        results.append(ConnectorParameter(parameter))

    return results


def _create_job_parameters(
    def_parameters: list[SingleJson],
    params: SingleJson,
) -> list[JobParameter]:
    """Create a job parameters list made out of parameters and def parameters.

    Returns:
        A list of JobParameter objects.

    """
    results: list[JobParameter] = []
    for parameter in def_parameters:
        parameter["name"] = parameter["Name"]
        parameter["value"] = params.get(parameter["Name"], parameter["DefaultValue"])
        parameter["isMandatory"] = parameter["IsMandatory"]
        parameter["type"] = parameter["Type"]

        results.append(JobParameter(parameter))

    return results


def get_request_payload(
    request: MockRequest,
    keys: Iterable[str] | None = None,
) -> SingleJson:
    """Get the payload of a request.

    Returns:
        The payload of a request.

    """
    if keys is None:
        keys = ("json", "payload", "params", "data")

    for key in keys:
        if key in request.kwargs:
            return request.kwargs[key]

    return {}
