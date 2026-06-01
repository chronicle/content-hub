"""Get Events action – queries security events with date, SaaS, severity, and type filters."""
import yaml

from ..core.base_action import BaseAction
from ..core.constants import GET_EVENTS_SCRIPT_NAME, SAAS_APPS_TO_SAAS_NAMES, SEVERITY_VALUES

SUCCESS_MESSAGE: str = "Successfully got Events!"
ERROR_MESSAGE: str = "Failed getting Events!"


class GetEvents(BaseAction):
    """Query Check Point HEC security events using multiple optional filters.

    Accepted filter parameters:

    * **Start Date** *(required)* – ISO 8601 start of the time window.
    * **End Date** – ISO 8601 end of the time window.
    * **SaaS Apps** – YAML list of SaaS application names (e.g. ``Microsoft Exchange``).
    * **States** – YAML list of event states (e.g. ``new``, ``dismissed``).
    * **Severities** – YAML list of severity labels (e.g. ``high``, ``critical``).
    * **Threat Types** – YAML list of threat type labels (e.g. ``Phishing``).
    * **Limit** – Maximum number of results to return (default 1000).

    SaaS application names and severity labels are mapped to API values using
    :data:`~core.constants.SAAS_APPS_TO_SAAS_NAMES` and
    :data:`~core.constants.SEVERITY_VALUES` respectively.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_EVENTS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract all event-query parameters from the SOAR action."""
        self.params.start_date = self.soar_action.extract_action_param(
            param_name="Start Date",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.end_date = self.soar_action.extract_action_param(
            param_name="End Date",
            print_value=True,
            is_mandatory=False,
        )
        self.params.saas_apps = self.soar_action.extract_action_param(
            param_name="SaaS Apps",
            print_value=True,
            is_mandatory=False,
        )
        self.params.states = self.soar_action.extract_action_param(
            param_name="States",
            print_value=True,
            is_mandatory=False,
        )
        self.params.severities = self.soar_action.extract_action_param(
            param_name="Severities",
            print_value=True,
            is_mandatory=False,
        )
        self.params.threat_types = self.soar_action.extract_action_param(
            param_name="Threat Types",
            print_value=True,
            is_mandatory=False,
        )
        self.params.limit = self.soar_action.extract_action_param(
            param_name="Limit",
            print_value=True,
            is_mandatory=False,
            default_value=1000,
            input_type=int,
        )

    def _perform_action(self, _=None) -> dict:
        """Map filter values to API identifiers and call the event query endpoint."""
        start_date = self.params.start_date
        end_date = self.params.end_date
        saas_apps = [SAAS_APPS_TO_SAAS_NAMES[saas] for saas in yaml.safe_load(self.params.saas_apps)]
        states = [state.lower() for state in yaml.safe_load(self.params.states)]
        severities = [SEVERITY_VALUES[severity.lower()] for severity in yaml.safe_load(self.params.severities)]
        threat_types = [threat_type.lower().replace(" ", "_") for threat_type in yaml.safe_load(self.params.threat_types)]
        limit = self.params.limit

        self.json_results = self.api_client.query_events(
            start_date=start_date,
            end_date=end_date,
            saas_apps=saas_apps,
            states=states,
            severities=severities,
            threat_types=threat_types,
        )


def main() -> None:
    GetEvents().run()


if __name__ == "__main__":
    main()
