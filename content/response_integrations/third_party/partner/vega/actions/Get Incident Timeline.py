from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import VegaApiAction
from ..core.constants import GET_INCIDENT_TIMELINE_SCRIPT_NAME
from ..core.utils import get_current_vega_id


class GetIncidentTimeline(VegaApiAction):
    """Fetch the full getIncidentTimeline for a Vega incident."""

    def __init__(self) -> None:
        super().__init__(GET_INCIDENT_TIMELINE_SCRIPT_NAME)
        self.incident_id: str = ""

    def _extract_action_parameters(self) -> None:
        self.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            default_value="",
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        incident_id = str(self.incident_id or "").strip() or get_current_vega_id(self.soar_action)
        if not incident_id:
            raise ValueError("Incident ID is required.")
        events = self.api_client.get_all_incident_timeline(incident_id)
        self.json_results = {
            "events": events,
            "total": len(events),
            "limit": len(events),
            "offset": 0,
        }
        self.output_message = f"Fetched {len(events)} timeline event(s) for Vega incident {incident_id}."


def main() -> None:
    GetIncidentTimeline().run()


if __name__ == "__main__":
    main()
