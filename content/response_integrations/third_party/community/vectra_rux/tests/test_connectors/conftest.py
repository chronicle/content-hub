from __future__ import annotations

import datetime
import types

import pytest

from SiemplifyConnectors import SiemplifyConnectorExecution

CONNECTOR_IDENTIFIER = "vectra-rux-detection-events-connector-test"


@pytest.fixture
def connector() -> SiemplifyConnectorExecution:
    """A SiemplifyConnectorExecution test double.

    Only the bare class needs to come from `tests/stubs/SiemplifyConnectors.py`
    (so that TIPCommon.DataStream's `isinstance(siemplify,
    SiemplifyConnectorExecution)` check resolves) - every attribute/method
    the connector script and TIPCommon actually call is attached here as a
    plain in-memory double:

    - `context.connector_info.identifier` + `get/set_connector_context_property`
      back both the detection-events checkpoint (VectraRUXManager) and the
      existing-ids store (TIPCommon.smp_io.read_ids/write_ids via
      TIPCommon.DataStream.ConnectorDBStream).
    - `get/set_context_property` backs the OAuth token cache
      (TIPCommon.oauth.CredStorage).
    - `fetch_timestamp`/`save_timestamp` back TIPCommon.smp_time's
      get_last_success_time/save_timestamp.
    - `is_overflowed_alert` backs TIPCommon.utils.is_overflowed; defaults to
      "never overflow", override per test with a MagicMock/side_effect.
    - `return_package` records the alerts the connector produced.
    """
    conn = SiemplifyConnectorExecution()
    conn.script_name = "Vectra RUX - Detection Events Connector"
    conn.parameters = {}

    connector_info = types.SimpleNamespace(identifier=CONNECTOR_IDENTIFIER, environment="Default Environment")
    conn.context = types.SimpleNamespace(connector_info=connector_info)

    conn._connector_context = {}
    conn.get_connector_context_property = (
        lambda identifier, key: conn._connector_context.get((identifier, key))
    )
    conn.set_connector_context_property = (
        lambda identifier, key, value: conn._connector_context.__setitem__((identifier, key), value)
    )

    conn._global_context = {}
    conn.get_context_property = (
        lambda context_type, identifier, property_key: conn._global_context.get(
            (context_type, identifier, property_key),
        )
    )
    conn.set_context_property = (
        lambda context_type, identifier, property_key, property_value: conn._global_context.__setitem__(
            (context_type, identifier, property_key),
            property_value,
        )
    )

    conn._last_run_timestamp = datetime.datetime(1970, 1, 1)
    conn.fetch_timestamp = (
        lambda datetime_format=False, timezone=False: conn._last_run_timestamp
    )
    conn.save_timestamp = (
        lambda **kwargs: setattr(conn, "_last_run_timestamp", kwargs.get("new_timestamp"))
    )

    conn.is_overflowed_alert = lambda **kwargs: False

    conn._alerts = []
    conn.return_package = lambda alerts: setattr(conn, "_alerts", alerts)

    return conn


def run_connector(connector_module, connector_execution, parameters, is_test_run=True):
    """Runs a connector module's `main(is_test_run)` with the given
    parameters against the provided (already-configured) test double, and
    returns the list of AlertInfo objects passed to `return_package`.
    """
    connector_execution.parameters = parameters

    original = connector_module.SiemplifyConnectorExecution
    connector_module.SiemplifyConnectorExecution = lambda: connector_execution
    try:
        connector_module.main(is_test_run)
    finally:
        connector_module.SiemplifyConnectorExecution = original

    return connector_execution._alerts
