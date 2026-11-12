from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import VegaApiAction
from ..core.constants import UPDATE_ALERT_SCRIPT_NAME
from ..core.utils import get_current_vega_id, parse_csv_list, to_graphql_enum


class UpdateAlert(VegaApiAction):
    """Update Vega alert status, severity, verdict, assignees, and/or comment."""

    def __init__(self) -> None:
        super().__init__(UPDATE_ALERT_SCRIPT_NAME)
        self.alert_ids_raw: str = ""
        self.status: str = ""
        self.verdict: str = ""
        self.severity: str = ""
        self.reasoning: str = ""
        self.comment: str = ""
        self.assignees_raw: str = ""

    def _extract_action_parameters(self) -> None:
        self.alert_ids_raw = extract_action_param(
            self.soar_action, param_name="Alert IDs", default_value="", print_value=True
        )
        self.status = extract_action_param(self.soar_action, param_name="Status", default_value="", print_value=True)
        self.verdict = extract_action_param(self.soar_action, param_name="Verdict", default_value="", print_value=True)
        self.severity = extract_action_param(
            self.soar_action, param_name="Severity", default_value="", print_value=True
        )
        self.reasoning = extract_action_param(
            self.soar_action, param_name="Verdict Reasoning", default_value="", print_value=True
        )
        self.comment = extract_action_param(self.soar_action, param_name="Comment", default_value="", print_value=True)
        self.assignees_raw = extract_action_param(
            self.soar_action, param_name="Assignees", default_value="", print_value=True
        )

    def _perform_action(self, _=None) -> None:
        alert_ids = parse_csv_list(self.alert_ids_raw)
        if not alert_ids:
            current = get_current_vega_id(self.soar_action)
            if current:
                alert_ids = [current]
        if not alert_ids:
            raise ValueError("Alert IDs are required.")
        payload = {"alertIds": alert_ids}
        status = str(self.status or "").strip()
        verdict = str(self.verdict or "").strip()
        severity = str(self.severity or "").strip()
        reasoning = str(self.reasoning or "").strip()
        comment = str(self.comment or "").strip()
        assignees = parse_csv_list(self.assignees_raw)
        if status:
            payload["status"] = to_graphql_enum(status)
        if verdict:
            payload["verdict"] = verdict
        if severity:
            payload["severity"] = severity
        if reasoning:
            payload["verdictReasoning"] = reasoning
        if comment:
            payload["comment"] = comment
        if assignees:
            payload["assignees"] = assignees
        result = self.api_client.update_alerts(payload)
        self.json_results = result
        self.output_message = f"Updated {len(alert_ids)} Vega alert(s)."


def main() -> None:
    UpdateAlert().run()


if __name__ == "__main__":
    main()
