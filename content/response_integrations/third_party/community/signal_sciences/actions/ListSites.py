from __future__ import annotations

from TIPCommon.base.action.data_models import DataTable as TIPDataTable
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.base_action import SignalSciencesAction
from ..core.datamodels import Site

SCRIPT_NAME = "List Sites"


class ListSitesAction(SignalSciencesAction):
    def __init__(self):
        super().__init__(SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.max_sites_to_return_raw = extract_action_param(
            self.soar_action, "Max Sites To Return", is_mandatory=False, print_value=True
        )

    def _validate_params(self) -> None:
        if self.max_sites_to_return_raw:
            try:
                self.max_sites_to_return = int(self.max_sites_to_return_raw)
            except (ValueError, TypeError):
                raise Exception(
                    f'Invalid parameter "Max Sites To Return". The value must be an '
                    f"integer. Wrong value provided: {self.max_sites_to_return_raw}"
                )
        else:
            self.max_sites_to_return = 0

    def _perform_action(self, _=None) -> None:
        try:
            sites_data = self.api_client.get_sites(max_records=self.max_sites_to_return)
            sites = [Site(site_raw) for site_raw in sites_data]

            if not sites:
                self.output_message = "No sites found for the given corporation."
                self.result_value = True
                return

            self.json_results = [site.raw_data for site in sites]

            table_data = [site.to_table() for site in sites]
            self.data_tables.append(
                TIPDataTable(title="Signal Sciences Sites", data_table=construct_csv(table_data))
            )

            site_names = ", ".join([site.name for site in sites])
            self.output_message = (
                "Successfully fetched information about the following sites in Signal Sciences:\n"
                f"{site_names}"
            )
            self.result_value = True

        except Exception as e:
            self.output_message = f'Error executing action: "{SCRIPT_NAME}". Reason: {e}'
            self.logger.error(self.output_message)
            self.result_value = False
            self.execution_state = ExecutionState.FAILED


def main():
    ListSitesAction().run()


if __name__ == "__main__":
    main()
