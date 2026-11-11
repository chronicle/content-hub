from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import GET_GRAPH_DETAILS_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon import validation
from TIPCommon.base.action.data_models import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv, convert_list_to_comma_string
from TIPCommon.utils import is_empty_string_or_none

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {INTEGRATION_DISPLAY_NAME}."


class GetGraphDetails(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.graph_ids = extract_action_param(
            self.soar_action,
            param_name="Graph ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_links_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Links To Return",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.graph_ids = validator.validate_csv(
            param_name="Graph ID",
            csv_string=self.params.graph_ids,
            print_value=False,
        )

        if not is_empty_string_or_none(self.params.max_links_to_return):
            self.params.max_links_to_return = validator.validate_positive(
                param_name="Max Links To Return",
                value=self.params.max_links_to_return,
                print_value=False,
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()

        not_found_graph_ids = []
        graphs_details = {}

        for graph_id in self.params.graph_ids:
            try:
                graphs_details[graph_id] = self.api_client.get_graph_details(
                    graph_id, self.params.max_links_to_return
                )
            except GoogleThreatIntelligenceExceptions as e:
                self.logger.error(
                    f"Failed to fetch details for {graph_id}. Error is {e}"
                )
                not_found_graph_ids.append(graph_id)

        if not graphs_details:
            self.output_message = "No information about the provided graphs was found."
            self.result_value = False
            return

        graphs_details_csv = convert_list_to_comma_string(
            list(graphs_details.keys()), delimiter=",\n"
        )

        self.output_message = (
            f"Successfully returned details about the following graphs in "
            f"{INTEGRATION_DISPLAY_NAME}: {graphs_details_csv}"
        )

        if not_found_graph_ids:
            not_found_graph_ids_csv = convert_list_to_comma_string(
                not_found_graph_ids, delimiter=",\n"
            )
            self.output_message += (
                "\n\nAction wasn't able to return details about the following "
                f"graphs in {INTEGRATION_DISPLAY_NAME}: {not_found_graph_ids_csv}"
            )

        self.logger.info("Adding graphs details to JSON results")
        json_results = {
            graph_id: graph_details.raw_data
            for graph_id, graph_details in graphs_details.items()
        }
        self.json_results = convert_dict_to_json_result_dict(json_results)

        self.logger.info("Adding links details to case wall table")
        for graph_id, graph_details in graphs_details.items():
            self.data_tables.append(
                DataTable(
                    title=f"Graph {graph_id} Links",
                    data_table=construct_csv([
                        link.to_csv() for link in graph_details.links
                    ]),
                )
            )


def main() -> None:
    GetGraphDetails(GET_GRAPH_DETAILS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
