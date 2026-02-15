from __future__ import annotations

from typing import Never

from TIPCommon.base.action import ExecutionState, Markdown

from ..core import constants, exceptions
from ..core.base_action import BaseAction

SCRIPT_NAME = "Chronicle - Trigger Investigation"
CONTEXT_KEY_INVESTIGATION_NAME = "chronicle_investigation_name"
FAILED_TO_OBTAIN_INVESTIGATION_NAME_ERROR = "Failed to obtain an investigation name."
MISSING_INVESTIGATION_NAME_IN_CONTEXT_ERROR = "Could not find investigation name in alert context."
NO_INVESTIGATION_FOUND_MESSAGE = "No existing investigation found. Triggering new one..."
ALERT_NOT_FROM_SIEM_MESSAGE = (
    "Triage agent couldn't execute this alert as it didn't originate in Google's SIEM detection"
    " engine."
)


def main() -> None:
    ServiceNowAgent().run()


class ServiceNowAgent(BaseAction):
    def __init__(self) -> None:
        super().__init__(f"{constants.INTEGRATION_NAME} - {SCRIPT_NAME}")

    def _perform_action(self, _: Never) -> None:
        alert_id = None
        current_alert = self.soar_action.current_alert
        if current_alert and current_alert.additional_properties:
            alert_id = current_alert.additional_properties.get("SiemAlertId")

        if not alert_id:
            self.logger.info(ALERT_NOT_FROM_SIEM_MESSAGE)
            self.output_message = ALERT_NOT_FROM_SIEM_MESSAGE
            self.execution_state = ExecutionState.FAILED
            return

        if self.is_first_run:
            self._handle_first_run(alert_id)
        else:
            self._handle_polling()

    def _handle_first_run(self, alert_id: str) -> None:
        self.logger.info(
            "Checking for existing investigations for Alert ID: %s",
            alert_id,
        )
        existing_investigations = self.api_client.list_investigations(alert_id)
        investigation_name = None
        if existing_investigations:
            inv = existing_investigations[0]
            investigation_name = inv.get("name")
            self.logger.info(
                "Found existing investigation: %s",
                investigation_name,
            )

        if investigation_name:
            self.soar_action.set_alert_context_property(
                CONTEXT_KEY_INVESTIGATION_NAME,
                investigation_name,
            )
            self._handle_investigation_status(investigation_name)
        else:
            self.logger.info(NO_INVESTIGATION_FOUND_MESSAGE)
            investigation_data = self.api_client.trigger_investigation(alert_id)
            investigation_name = investigation_data.get("name")
            if not investigation_name:
                raise exceptions.AgentError(FAILED_TO_OBTAIN_INVESTIGATION_NAME_ERROR)

            self.output_message = f"Successfully triggered investigation: {investigation_name}"
            self.soar_action.set_alert_context_property(
                CONTEXT_KEY_INVESTIGATION_NAME,
                investigation_name,
            )
            self.execution_state = ExecutionState.IN_PROGRESS

    def _handle_polling(self) -> None:
        investigation_name = self.soar_action.get_alert_context_property(
            CONTEXT_KEY_INVESTIGATION_NAME,
        )
        if not investigation_name:
            raise exceptions.AgentError(MISSING_INVESTIGATION_NAME_IN_CONTEXT_ERROR)
        self.logger.info(
            "Retrieved investigation name from context: %s",
            investigation_name,
        )
        self._handle_investigation_status(investigation_name)

    def _handle_investigation_status(self, investigation_name: str) -> None:
        self.logger.info(
            "Checking status for investigation: %s",
            investigation_name,
        )
        investigation_data = self.api_client.get_investigation_status(
            investigation_name,
        )
        current_status = investigation_data.get("status")
        if current_status in {
            "STATUS_PENDING",
            "IN_PROGRESS",
            "STATUS_IN_PROGRESS",
        }:
            self.output_message = (
                f"Investigation {investigation_name} is still running (Status: {current_status})"
            )
            self.execution_state = ExecutionState.IN_PROGRESS

        elif current_status == "STATUS_COMPLETED_SUCCESS":
            verdict = (investigation_data.get("verdict") or "").replace("_", " ")
            confidence = (
                (investigation_data.get("confidence") or "").replace("_", " ").lower().title()
            )
            self.output_message = f"Investigation Summary: {verdict} ({confidence})"
            self.result_value = True
            self.execution_state = ExecutionState.COMPLETED
            self.json_results = {
                "agent_raw_data": investigation_data,
                "verdict": investigation_data.get("verdict"),
                "confidence": investigation_data.get("confidence"),
            }
            alert_summary = _get_summary_point(investigation_data.get("summary"), -2)
            investigation_summary = _get_summary_point(investigation_data.get("summary"), -1)
            if alert_summary and investigation_summary:
                self.markdowns.append(
                    Markdown(
                        title="Alert Summary",
                        markdown_content=alert_summary,
                        markdown_name="Alert Summary",
                    )
                )
                self.markdowns.append(
                    Markdown(
                        title="Investigation Summary",
                        markdown_content=investigation_summary,
                        markdown_name="Investigation Summary",
                    )
                )
            else:
                self.markdowns.append(
                    Markdown(
                        title="Summary",
                        markdown_content=investigation_data.get("summary"),
                        markdown_name="Summary",
                    )
                )
            self.markdowns.append(
                Markdown(
                    title="Suggested Next Steps",
                    markdown_content=_format_next_steps_markdown(investigation_data),
                    markdown_name="Next steps",
                )
            )
        else:
            self.output_message = f"Investigation ended with non-success status: {current_status}"
            self.execution_state = ExecutionState.FAILED
            self.json_results = {"agent_raw_data": investigation_data}


def _format_next_steps_markdown(investigation_data):
    next_steps = investigation_data.get("nextSteps", [])
    recommended = investigation_data.get("recommendedNextSteps", [])

    lines = []

    # Logic matching the Angular @if / @else if structure
    if next_steps:
        for step in next_steps:
            title = step.get("title", "")
            if title:
                suffix = " 🔍" if step.get("type") == "SEARCHABLE" else ""
                lines.append(f"* {title}{suffix}")

    elif recommended:
        for step in recommended:
            lines.append(f"* {step}")

    return "\n".join(lines)


def _get_summary_point(text: str, index: int) -> str:
    if not text:
        return ""

    # Split by newline and filter lines starting with '*'
    points = [line.strip() for line in text.strip().split("\n") if line.strip().startswith("*")]

    if len(points) > index:
        # Remove the '*' (substring(1)) and trim the result
        return points[index][1:].strip()

    return ""


if __name__ == "__main__":
    main()
