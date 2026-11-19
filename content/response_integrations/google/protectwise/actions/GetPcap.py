from __future__ import annotations

import base64
from enum import Enum
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.types import SingleJson

from protectwise.core.ProtectwiseManager import ProtectwiseManager, ProtectwiseManagerError


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


def get_target_alerts(siemplify: SiemplifyAction, execution_scope: Any) -> list[Any]:
    """Determines target alerts based on execution scope."""
    if execution_scope.value == ExecutionScope.Alert.value:
        alerts = [siemplify.current_alert]
    else:
        alerts = getattr(siemplify.case, "open_alerts", siemplify.case.alerts)

    return alerts


def download_and_attach_pcap(
    siemplify: SiemplifyAction,
    protectwise_manager: ProtectwiseManager,
    event_name: str,
    event_id: str,
) -> bool:
    """Downloads and attaches a PCAP file from ProtectWise."""
    try:
        pcap_content: bytes = protectwise_manager.download_pcap(event_id)

        siemplify.result.add_attachment(
            f"ProtectWise pcap - {event_name}: {event_id}",
            f"{event_id}.pcap",
            base64.b64encode(pcap_content).decode("utf-8"),
        )
        return True
    except ProtectwiseManagerError as e:
        siemplify.LOGGER.error(
            f"Failed to process PCAP for event {event_name}: {e}"
        )
        return False
    except Exception as e:
        siemplify.LOGGER.error(
            f"An unexpected error occurred while processing PCAP for event "
            f"{event_name}: {e}"
        )
        return False


def process_event(
    siemplify: SiemplifyAction,
    protectwise_manager: ProtectwiseManager,
    event: Any,
) -> bool:
    """Processes a single security event to fetch and attach PCAPs."""
    start_time: str = event.start_time
    end_time: str = event.end_time

    if start_time == end_time:
        end_time = str(int(end_time) + 1)

    try:
        protectwise_events: list[SingleJson] = protectwise_manager.get_events(
            start_time, end_time
        )
    except ProtectwiseManagerError as e:
        siemplify.LOGGER.error(
            f"Failed to process PCAP for event {event.name}: {e}"
        )
        return False
    except Exception as e:
        siemplify.LOGGER.error(
            f"An unexpected error occurred while processing PCAP for event "
            f"{event.name}: {e}"
        )
        return False

    pcap_downloaded = False

    for protectwise_event in protectwise_events:
        event_id: str | None = protectwise_event.get("id")
        if event_id and download_and_attach_pcap(
            siemplify, protectwise_manager, event.name, event_id
        ):
            pcap_downloaded = True

    return pcap_downloaded


def process_alert(
    siemplify: SiemplifyAction,
    protectwise_manager: ProtectwiseManager,
    alert: Any,
) -> list[str]:
    """Processes all events in an alert."""
    found_pcaps_events: list[str] = []
    events: list[Any] = alert.security_events or []

    for event in events:
        if process_event(siemplify, protectwise_manager, event):
            found_pcaps_events.append(event.name)

    return found_pcaps_events


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    execution_scope: Any = getattr(
        siemplify,
        "execution_scope",
        ExecutionScope.Alert,
    )

    target_alerts: list[Any] = get_target_alerts(siemplify, execution_scope)

    configurations: dict[str, str] = siemplify.get_configuration("Protectwise")
    email: str = configurations["Email"]
    password: str = configurations["Password"]

    protectwise_manager: ProtectwiseManager = ProtectwiseManager(email, password)

    found_pcaps_events: list[str] = []

    for alert in target_alerts:
        found_pcaps_events.extend(process_alert(siemplify, protectwise_manager, alert))

    if execution_scope.value == ExecutionScope.Alert.value:
        if found_pcaps_events:
            output_message: str = (
                "Successfully downloaded pcap for events in the case timeframe: \n"
                + "\n".join(found_pcaps_events)
            )
        else:
            output_message: str = "No pcaps were downloaded."
    else:
        if found_pcaps_events:
            output_message: str = (
                "Successfully downloaded pcap for events in the case timeframe "
                f"for all alert(s) in case {siemplify.case_id}: \n"
                + "\n".join(found_pcaps_events)
            )
        else:
            output_message: str = (
                "No pcaps were downloaded "
                f"for all alert(s) in case {siemplify.case_id}."
            )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
