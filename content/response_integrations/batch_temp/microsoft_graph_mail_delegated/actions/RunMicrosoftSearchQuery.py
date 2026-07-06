from __future__ import annotations
from collections.abc import Iterable
from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value
from ..core import action_init
from ..core import constants
from ..core import datamodels
from ..core import exceptions
from ..core.MicrosoftGraphMailDelegatedManager import ApiManager

class RunMicrosoftSearchQuery(Action[ApiManager]):

    def __init__(self) -> None:
        super().__init__(constants.RUN_MICROSOFT_SEARCH_QUERY_SCRIPT_NAME)
        self.result_value: bool = True
        self.output_message: str = ""
        self.error_output_message: str = (
            "Error executing action "
            f'"{constants.RUN_MICROSOFT_SEARCH_QUERY_SCRIPT_NAME}".'
        )
        self.json_results: list[dict] = []

    def _init_api_clients(self) -> ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        self.params.entity_types_to_search = extract_action_param(
            self.soar_action,
            param_name="Entity Types To Search",
            print_value=True,
        )
        self.params.entity_types_to_search = string_to_multi_value(
            self.params.entity_types_to_search
        )
        self.params.fields_to_return = extract_action_param(
            self.soar_action,
            param_name="Fields To Return",
            print_value=True
        )
        self.params.fields_to_return = string_to_multi_value(
            self.params.fields_to_return
        )
        self.params.search_query = extract_action_param(
            self.soar_action,
            param_name="Search Query",
            print_value=True,
        )
        self.params.max_rows_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Rows To Return",
            input_type=int,
            default_value=25,
            print_value=True,
        )
        self.params.advanced_query = extract_action_param(
            self.soar_action,
            param_name="Advanced Query",
            print_value=True
        )

    def _validate_params(self) -> None:
        if not self.params.advanced_query:
            if not self.params.entity_types_to_search or not self.params.search_query:
                raise exceptions.InvalidParameterException(
                    "Failed to construct a search query based on the provided "
                    "parameters. Please check, if you specified all parameters "
                    "properly."
                )
        unsupported_entity_types: set[str] = set(
            self.params.entity_types_to_search
        ) - set(constants.SUPPORTED_ENTITY_TYPES)
        if not self.params.advanced_query and unsupported_entity_types:
            unsupported_string = ", ".join(unsupported_entity_types)
            raise exceptions.UnsupportedEntityTypeException(
                "Failed to run the search as the provided combination of entities to "
                "search by is not supported by the API. Please consult Microsoft "
                "Documentation for supported entity combinations - https://"
                "learn.microsoft.com/en-us/graph/search-concept-interleaving.\n"
                f"Error is \"{unsupported_string}\""
            )

    def _perform_action(self, _) -> None:
        search_query_response = self._run_microsoft_search_query()
        self._set_action_result(search_query_response)

    def _run_microsoft_search_query(self) -> Iterable[datamodels.SearchResultData]:
        try:
            return self.api_client.run_microsoft_search_query(
                entity_types_to_search=self.params.entity_types_to_search,
                fields_to_return=self.params.fields_to_return,
                search_query=self.params.search_query,
                max_rows_to_return=self.params.max_rows_to_return,
                advanced_query=self.params.advanced_query,
            )

        except exceptions.MicrosoftGraphMailManagerError as e:
            if "invalid" in str(e) and self.params.advanced_query:
                raise exceptions.MicrosoftGraphMailManagerError(
                    "Failed to run the search as the provided advanced search "
                    f"query is invalid! Error is: {e}"
                ) from e

            raise  exceptions.MicrosoftGraphMailManagerError(
                f"Failed to run the search! Error is: {e}"
            ) from e

    def _set_action_result(
        self,
        result_data: Iterable[datamodels.SearchResultData]
    ) -> None:
        self.json_results = [email.to_json() for email in result_data]
        if result_data:
            self.output_message = (
                "Successfully retrieved results for the provided search query."
            )
        else:
            self.result_value = False
            self.output_message = "No results found for the provided query."


def main() -> NoReturn:
    RunMicrosoftSearchQuery().run()


if __name__ == "__main__":
    main()
