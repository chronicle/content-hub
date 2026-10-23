from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import VegaApiAction, current_vega_id
from ..core.constants import GET_INCIDENT_DETAILS_SCRIPT_NAME


class GetIncidentDetails(VegaApiAction):
    """Fetch one Vega incident by id (or from the current case)."""

    def __init__(self) -> None:
        super().__init__(GET_INCIDENT_DETAILS_SCRIPT_NAME)
        self.incident_id: str = ""

    def _extract_action_parameters(self) -> None:
        self.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            default_value="",
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        incident_id = str(self.incident_id or "").strip() or current_vega_id(self.soar_action)
        if not incident_id:
            raise ValueError("Incident ID is required.")
        result = self.api_client.get_incident(incident_id)
        self.json_results = result
        self.output_message = f"Fetched Vega incident details for {incident_id}."


def main() -> None:
    GetIncidentDetails().run()


if __name__ == "__main__":
    main()
