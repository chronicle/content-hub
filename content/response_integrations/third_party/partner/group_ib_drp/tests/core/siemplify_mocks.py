"""Lightweight test doubles for the ``soar_sdk`` Siemplify* classes.

The DRP integration uses the legacy ``SiemplifyAction``/``SiemplifyConnectorExecution``/``SiemplifyJob`` API. Spinning up the
real classes inside a unit test would require reproducing the SOAR
runtime context (a JSON document fed via stdin, a session pointing at
the SOAR REST API, etc.). These tests bypass that entirely by patching
each script's module-level ``SiemplifyAction``/``SiemplifyConnectorExecution``/``SiemplifyJob`` symbol with a small recording stub
defined here.

The stubs intentionally mimic only the surface the DRP scripts actually
use:

- ``LOGGER`` (info/error/warn/exception/debug)
- ``end()`` / ``return_package()`` / ``end_script()``
- ``add_result_json()`` / ``create_case_insight()``
- ``current_alert.security_events`` (Alert) and ``target_entities`` (list[Entity]) for actions
- ``extract_job_param()`` for the job
- ``context.connector_info.environment`` / ``fetch_timestamp`` /
  ``save_timestamp`` / ``is_overflowed_alert`` for connectors
- ``get_cases_ids_by_filter`` / ``_get_case_by_id`` /
  ``close_case`` / ``add_comment`` / ``add_tag`` /
  ``add_entity_to_case`` / ``get_case_comments`` for the dedup job
"""

from __future__ import annotations

import dataclasses
from typing import Any
from unittest.mock import MagicMock


@dataclasses.dataclass
class FakeAlert:
    security_events: list = dataclasses.field(default_factory=list)
    rule_generator: str = ""


@dataclasses.dataclass
class FakeEntity:
    identifier: str
    entity_type: str = "DestinationURL"


@dataclasses.dataclass
class FakeSecurityEvent:
    """Mimics ``current_alert.security_events[i]``.

    The DRP actions read ``getattr(event, 'additional_properties', {}) or {}``
    and pull ``violation_url`` / ``violation_uid`` out of it.
    """

    additional_properties: dict = dataclasses.field(default_factory=dict)


def make_logger() -> MagicMock:
    """Return a ``LOGGER`` stand-in supporting every method the scripts call.

    SOAR's logger exposes ``info``, ``error``, ``warn``, ``warning``,
    ``exception``, and ``debug``; ``MagicMock`` is permissive enough but we
    set ``spec=None`` so unexpected attribute access still works. Using a
    plain ``MagicMock`` keeps each call recorded for optional assertions.
    """
    return MagicMock(name="LOGGER")


def make_action_siemplify(
    parameters: dict | None = None,
    target_entities: list[FakeEntity] | None = None,
    security_events: list[FakeSecurityEvent] | None = None,
    integration_config: dict | None = None,
) -> MagicMock:
    """Build a ``SiemplifyAction`` test double.

    ``integration_config`` is consulted by ``extract_configuration_param``
    via ``siemplify.get_configuration``. The DRP ``GIBConnector.init_action_poller`` calls ``extract_configuration_param`` which in turn calls
    ``siemplify.get_configuration(provider_name)``; we wire that to return
    the supplied dictionary so the action picks up the test credentials.
    """
    parameters = parameters or {}
    target_entities = target_entities or []
    security_events = security_events or []
    integration_config = integration_config or {}

    siemplify = MagicMock(name="SiemplifyAction")
    siemplify.LOGGER = make_logger()
    siemplify.script_name = ""

    siemplify.parameters = dict(parameters)
    siemplify.target_entities = list(target_entities)
    siemplify.current_alert = FakeAlert(security_events=list(security_events))

    siemplify.get_configuration.return_value = dict(integration_config)
    siemplify.extract_configuration_param.side_effect = (
        lambda *a, **kw: integration_config.get(kw.get("param_name") or (a[1] if len(a) > 1 else ""))
    )

    siemplify.result = MagicMock(name="result")

    siemplify._end_calls = []

    def _end(message: str = "", result_value: Any = None, status: int | None = None) -> None:
        siemplify._end_calls.append(
            {"message": message, "result_value": result_value, "status": status}
        )

    siemplify.end.side_effect = _end

    siemplify.add_entity_to_case = MagicMock(name="add_entity_to_case")
    siemplify.create_case_insight = MagicMock(name="create_case_insight")
    return siemplify


def make_connector_siemplify(
    parameters: dict | None = None,
    integration_config: dict | None = None,
    fetched_timestamp: int | None = None,
    environment: str = "Default Environment",
    is_overflow: bool = False,
) -> MagicMock:
    """Build a ``SiemplifyConnectorExecution`` test double.

    ``fetched_timestamp`` programs the value returned by
    ``fetch_timestamp(...)`` — used by the connectors to decide whether
    to call ``poller.get_seq_update_dict`` for the bootstrap case.

    ``is_overflow`` toggles the response of ``is_overflowed_alert`` so a
    test can verify the connector skips overflow-flagged alerts.

    ``parameters`` is a mapping of connector parameter names to their
    string values, the same shape the SOAR runtime presents via
    ``extract_connector_param``.
    """
    parameters = parameters or {}
    integration_config = integration_config or {}

    siemplify = MagicMock(name="SiemplifyConnectorExecution")
    siemplify.LOGGER = make_logger()
    siemplify.script_name = ""

    siemplify.parameters = dict(parameters)
    siemplify.context = MagicMock()
    siemplify.context.connector_info.environment = environment
    siemplify.context.connector_info.params = [
        {"param_name": k, "param_value": v} for k, v in parameters.items()
    ]

    siemplify.fetch_timestamp.return_value = fetched_timestamp
    siemplify.save_timestamp = MagicMock(name="save_timestamp")
    siemplify.is_overflowed_alert.return_value = is_overflow

    siemplify._returned_packages: list[list] = []

    def _return_package(alerts):
        siemplify._returned_packages.append(list(alerts))

    siemplify.return_package.side_effect = _return_package

    siemplify.extract_connector_param.side_effect = (
        lambda *a, **kw: parameters.get(kw.get("param_name") or (a[1] if len(a) > 1 else ""))
    )
    return siemplify


def make_job_siemplify(
    parameters: dict | None = None,
    case_ids: list[Any] | None = None,
    cases_by_id: dict[str, dict] | None = None,
) -> MagicMock:
    """Build a ``SiemplifyJob`` test double for the dedup job.

    ``parameters`` programs the values returned by ``extract_job_param``.
    ``case_ids`` programs the list returned by
    ``get_cases_ids_by_filter``. ``cases_by_id`` programs
    ``_get_case_by_id``: keys are stringified case IDs, values are the
    JSON-shaped case payload (``status`` / ``creation_time`` /
    ``cyber_alerts`` / ``tags`` / ``environment``).
    """
    parameters = parameters or {}
    case_ids = case_ids or []
    cases_by_id = cases_by_id or {}

    siemplify = MagicMock(name="SiemplifyJob")
    siemplify.LOGGER = make_logger()
    siemplify.script_name = ""

    siemplify.extract_job_param.side_effect = lambda **kw: parameters.get(
        kw.get("param_name"), kw.get("default_value")
    )

    siemplify.get_cases_ids_by_filter.return_value = list(case_ids)
    siemplify._get_case_by_id.side_effect = lambda cid: cases_by_id[str(cid)]

    siemplify.close_case = MagicMock(name="close_case")
    siemplify.add_comment = MagicMock(name="add_comment")
    siemplify.add_tag = MagicMock(name="add_tag")
    siemplify.add_entity_to_case = MagicMock(name="add_entity_to_case")
    siemplify.get_case_comments = MagicMock(name="get_case_comments", return_value=[])

    siemplify.session = MagicMock(name="session")

    siemplify.end_script = MagicMock(name="end_script")
    return siemplify
