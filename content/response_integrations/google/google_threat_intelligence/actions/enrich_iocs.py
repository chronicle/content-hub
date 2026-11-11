from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    ENRICH_IOCS_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    WIDGET_THEME_MAPPING,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from TIPCommon import validation
from TIPCommon.base.action.data_models import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from google_threat_intelligence.core.utils import prepare_ioc_for_manager

ERROR_MESSAGE = f"Error executing action {ENRICH_IOCS_SCRIPT_NAME}."
entity_type_map = {
    "Filehash": "files",
    "URL": "urls",
    "IP Address": "ip_addresses",
    "Domain": "domains",
}


class EnrichIOCs(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = ERROR_MESSAGE
        self.json_results = []
        self.successful_iocs = []
        self.failed_iocs = []
        self.result_value = True

    def _extract_action_parameters(self) -> None:
        self.params.iocs = extract_action_param(
            self.soar_action,
            param_name="IOCs",
            is_mandatory=True,
            print_value=True,
        )
        self.params.ioc_type = extract_action_param(
            self.soar_action,
            param_name="IOC Type",
            print_value=True,
        )
        self.params.widget_theme = extract_action_param(
            self.soar_action,
            param_name="Widget Theme",
            print_value=True,
            default_value="Chronicle",
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.ioc_type = validator.validate_ddl(
            param_name="IOC Type",
            value=self.params.ioc_type,
            ddl_values=list(entity_type_map.keys()),
        )
        self.params.widget_theme = validator.validate_ddl(
            param_name="Widget Theme",
            value=self.params.widget_theme,
            ddl_values=list(WIDGET_THEME_MAPPING.keys()),
        )
        self.params.iocs = validator.validate_csv(
            param_name="IOCs",
            csv_string=self.params.iocs,
            print_value=False,
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        ioc_details = []
        for ioc in self.params.iocs:
            ioc_value = prepare_ioc_for_manager(ioc, self.params.ioc_type)
            try:
                ioc_data = self.api_client.get_ioc_details(
                    ioc=ioc_value, ioc_type=entity_type_map.get(self.params.ioc_type)
                )
                if ioc_data:
                    widget_link, widget_html = self.api_client.get_widget(
                        ioc,
                        theme_colors=WIDGET_THEME_MAPPING.get(self.params.widget_theme),
                    )
                    ioc_details.append({
                        "identifier": ioc,
                        "details": ioc_data.to_json_shorten(
                            widget_link=widget_link, cached_html_widget=widget_html
                        ),
                    })
                    self.soar_action.result.add_entity_link(ioc, ioc_data.report_link)
                    self.data_tables.append(
                        DataTable(
                            title=ioc,
                            data_table=construct_csv(ioc_data.to_csv()),
                        )
                    )
                    self.successful_iocs.append(ioc)

            except GoogleThreatIntelligenceExceptions as err:
                self.failed_iocs.append(ioc)
                self.logger.error(f"Failed processing ioc: {ioc}")
                self.logger.exception(err)
        if self.successful_iocs:
            self.json_results = {"iocs": ioc_details}
            self.output_message += (
                f"Successfully enriched the following "
                f"IOCs using {INTEGRATION_DISPLAY_NAME}: "
                f"\n{', '.join(self.successful_iocs)}"
            )

        if self.failed_iocs:
            self.output_message += (
                f"\nNo information found for the "
                f"following IOCs using "
                f"{INTEGRATION_DISPLAY_NAME} \n"
                f"{', '.join(self.failed_iocs)}"
            )

        if not self.successful_iocs:
            self.result_value = False
            self.output_message = "No information about IOCs was found."


def main() -> None:
    EnrichIOCs(ENRICH_IOCS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
