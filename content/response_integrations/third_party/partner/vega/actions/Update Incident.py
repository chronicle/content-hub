from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import VegaApiAction
from ..core.constants import UPDATE_INCIDENT_SCRIPT_NAME
from ..core.utils import get_current_vega_id, parse_csv_list, to_graphql_enum


class UpdateIncident(VegaApiAction):
    """Update Vega incident user status, severity, verdict, assignees, and/or comment."""

    def __init__(self) -> None:
        super().__init__(UPDATE_INCIDENT_SCRIPT_NAME)
        self.incident_ids_raw: str = ""
        self.user_status: str = ""
        self.severity: str = ""
        self.verdict: str = ""
        self.reasoning: str = ""
        self.comment: str = ""
        self.emails_raw: str = ""

    def _extract_action_parameters(self) -> None:
        self.incident_ids_raw = extract_action_param(
            self.soar_action, param_name="Incident IDs", default_value="", print_value=True
        )
        self.user_status = extract_action_param(
            self.soar_action, param_name="User Status", default_value="", print_value=True
        )
        self.severity = extract_action_param(
            self.soar_action, param_name="Severity", default_value="", print_value=True
        )
        self.verdict = extract_action_param(
            self.soar_action, param_name="Verdict", default_value="", print_value=True
        )
        self.reasoning = extract_action_param(
            self.soar_action, param_name="Verdict Reasoning", default_value="", print_value=True
        )
        self.comment = extract_action_param(
            self.soar_action, param_name="Comment", default_value="", print_value=True
        )
        self.emails_raw = extract_action_param(
            self.soar_action, param_name="Assignee Emails", default_value="", print_value=True
        )

    def _perform_action(self, _=None) -> None:
        incident_ids = parse_csv_list(self.incident_ids_raw)
        if not incident_ids:
            current = get_current_vega_id(self.soar_action)
            if current:
                incident_ids = [current]
        if not incident_ids:
            raise ValueError("Incident IDs are required.")
        payload = {"incidentIds": incident_ids}
        user_status = str(self.user_status or "").strip()
        severity = str(self.severity or "").strip()
        verdict = str(self.verdict or "").strip()
        reasoning = str(self.reasoning or "").strip()
        comment = str(self.comment or "").strip()
        emails = parse_csv_list(self.emails_raw)
        if user_status:
            payload["userStatus"] = to_graphql_enum(user_status)
        if severity:
            payload["severity"] = severity
        if verdict or reasoning:
            payload["verdict"] = {"value": verdict or "NA", "reasoning": reasoning}
        if comment:
            payload["comment"] = comment
        if emails:
            payload["assigneeEmails"] = emails
        result = self.api_client.update_incidents(payload)
        self.json_results = result
        self.output_message = f"Updated {len(incident_ids)} Vega incident(s)."


def main() -> None:
    UpdateIncident().run()


if __name__ == "__main__":
    main()
