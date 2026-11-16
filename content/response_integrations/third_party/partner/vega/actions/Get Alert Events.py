from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import VegaApiAction
from ..core.constants import ALERT_EVENTS_MAX_FETCH, GET_ALERT_EVENTS_SCRIPT_NAME
from ..core.utils import iter_current_vega_ids


class GetAlertEvents(VegaApiAction):
    """Fetch all getAlertsEvents pages for a Vega alert."""

    def __init__(self) -> None:
        super().__init__(GET_ALERT_EVENTS_SCRIPT_NAME)
        self.alert_id: str = ""
        self.limit: str = "100"
        self.offset: str = "0"

    def _extract_action_parameters(self) -> None:
        self.alert_id = extract_action_param(
            self.soar_action,
            param_name="Alert ID",
            default_value="",
            print_value=True,
        )
        self.limit = extract_action_param(
            self.soar_action,
            param_name="Limit",
            default_value="100",
            print_value=True,
        )
        self.offset = extract_action_param(
            self.soar_action,
            param_name="Offset",
            default_value="0",
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        candidates: list[str] = []
        if str(self.alert_id).strip():
            candidates.append(str(self.alert_id).strip())
        else:
            candidates.extend(iter_current_vega_ids(self.soar_action))
        if not candidates:
            raise ValueError(
                "Alert ID is required. Enter the Vega alert UUID, or run this action on a Vega Alert case."
            )
        page_size = int(self.limit or 100)
        all_events: list = []
        used_id = candidates[0]
        last_error: Exception | None = None
        fetched = False
        for candidate in candidates:
            try:
                all_events = self.api_client.get_all_alert_events(
                    candidate,
                    page_size=page_size,
                    max_records=ALERT_EVENTS_MAX_FETCH,
                )
            except Exception as error:
                last_error = error
                continue
            fetched = True
            used_id = candidate
            break
        if not fetched:
            raise last_error or ValueError("Unable to fetch Vega alert events.")
        self.json_results = {
            "total": len(all_events),
            "limit": page_size,
            "offset": int(self.offset or 0),
            "alert_id": used_id,
            "results": all_events,
        }
        self.output_message = f"Fetched {len(all_events)} Vega alert event(s) for {used_id}."


def main() -> None:
    GetAlertEvents().run()


if __name__ == "__main__":
    main()
