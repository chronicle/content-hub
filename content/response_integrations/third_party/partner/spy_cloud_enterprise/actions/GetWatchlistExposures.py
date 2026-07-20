"""
SpyCloud Enterprise - Get Watchlist Exposures

Presents the SpyCloud Watchlist exposures that already live on the current
case as a single case-wall data table. It iterates every alert in the case,
reads the SpyCloud fields the connector/parser flattened onto each alert's
security events, and renders one row per exposure event.

Data source: this action does NOT call the SpyCloud API. The connector already
fetched, normalized, and de-duplicated the exposures into alerts; those alerts
are grouped into this case. This action simply surfaces what is in the case, so
there is no reason to pull unrelated exposures that belong to other cases.

Sensitive data: SpyCloud records can contain plaintext passwords, cookies, and
tokens. Whether those raw values reach this action is controlled by the
connector's "Include Plaintext Secrets" option:
  - Disabled (default): the connector strips secrets before persisting the
    alert, so this action only has metadata and booleans to show (for example
    "Plaintext Password Exposed: Yes").
  - Enabled: the connector persists the raw secrets onto the case event and this
    action surfaces them verbatim in the data table, the expandable full-detail
    view on the case wall, and the JSON result. Those values are stored in the
    SecOps case permanently; enable the option only with explicit sign-off.
"""
from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightType
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import construct_csv

from ..core import datamodels
from ..core.Constants import (
    GET_WATCHLIST_EXPOSURES_SCRIPT_NAME,
    INTEGRATION_NAME,
)

SCRIPT_NAME = GET_WATCHLIST_EXPOSURES_SCRIPT_NAME
EXPOSURES_TABLE_NAME = "SpyCloud Watchlist Exposures"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = 0
    output_message = ""

    try:
        rows: list[dict] = []
        json_rows: list[dict] = []

        alerts = siemplify.case.alerts or []
        siemplify.LOGGER.info(f"Scanning {len(alerts)} alert(s) in the case")

        for alert in alerts:
            alert_name = getattr(alert, "name", "") or ""
            for event in getattr(alert, "security_events", []) or []:
                props = getattr(event, "additional_properties", {}) or {}
                if not datamodels.is_spycloud_event(props):
                    continue
                rows.append(datamodels.event_row(alert_name, props))
                json_rows.append(datamodels.event_json(props))

        siemplify.LOGGER.info(f"Found {len(rows)} SpyCloud exposure event(s) in the case")

        if rows:
            # Surface a compact HTML panel directly on the case wall so analysts
            # see the exposures at a glance, then keep the full detail in the
            # case-wall data table and JSON result.
            siemplify.create_case_insight(
                triggered_by=INTEGRATION_NAME,
                title=EXPOSURES_TABLE_NAME,
                content=datamodels.build_case_insight_html(rows),
                entity_identifier="",
                severity=datamodels.insight_severity(rows),
                insight_type=InsightType.General,
            )
            siemplify.result.add_data_table(EXPOSURES_TABLE_NAME, construct_csv(rows))
            siemplify.result.add_result_json({"exposures": json_rows})
            result_value = len(rows)
            output_message = (
                f"Presented {len(rows)} SpyCloud Watchlist exposure(s) from the case."
            )
        else:
            output_message = (
                "No SpyCloud Watchlist exposures were found on the alerts in this case."
            )

    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "{SCRIPT_NAME}". Reason: {error}')
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = 0
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"status: {status}, result_value: {result_value}, output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
