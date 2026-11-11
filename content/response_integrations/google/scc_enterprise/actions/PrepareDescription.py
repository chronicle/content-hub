from __future__ import annotations

import json
import sys
from typing import NoReturn

from soar_sdk import SiemplifyUtils

import TIPCommon.base.action
import TIPCommon.extraction
import TIPCommon.validation
from TIPCommon.types import SingleJson
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import SCCEnterpriseDatamodels as SCCEDatamodels
from scc_enterprise.core import SCCEnterpriseDescParams
from scc_enterprise.core.SCCEnterpriseDescCreation import get_create_desc_fn
from scc_enterprise.core.SCCEnterpriseUtils import (
    create_html_table,
    create_jwm_table,
    get_alert_source_group_identifier,
    get_cloud_provider_from_source_group_id,
    get_first_event_data,
    update_html_desc_table,
    update_jira_wiki_desc_table,
)


class GetCaseContextError(Exception):
    """Case context failed to be fetched"""


class PrepareDescription(TIPCommon.base.action.Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self._fix_sdk_stdout()
        self.output_type = SCCEDatamodels.DescriptionOutputType.HTML

    def _extract_action_parameters(self) -> None:
        self.params.output = TIPCommon.extraction.extract_action_param(
            siemplify=self.soar_action, param_name="Output", print_value=True
        )
        self.output_type = SCCEDatamodels.DescriptionOutputType(self.params.output)

    def _validate_params(self) -> None:
        validator = TIPCommon.validation.ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Output",
            value=str(self.params.output),
            ddl_values=[
                SCCEnterpriseConsts.HTML_TEMPLATE_TYPE,
                SCCEnterpriseConsts.JWM_TEMPLATE_TYPE,
            ],
        )

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        self.logger.info("Creating description based on template and case data")
        create_desc_fn = get_create_desc_fn(self.output_type)
        params = self._get_template_params_for_cloud_provider()

        self.logger.info("Generating description")
        description = create_desc_fn(params)
        description = self._add_table_to_description(description)
        self.json_results = _create_json_result(description)
        self.output_message = "Generated Description"

        if not description:
            self.result_value = False
            self.output_message = "No description was generated"

    def _get_template_params_for_cloud_provider(self) -> SingleJson:
        cloud_provider = self._get_current_alert_cloud_provider()
        self.logger.info(
            "Creating template params based on "
            f'"{cloud_provider.value}" cloud provider and "{self.params.output}" '
            "output format"
        )
        finding_data = get_first_event_data(self.soar_action)
        param_creator = SCCEnterpriseDescParams.get_desc_parameter_creator(
            output_type=self.output_type,
            cloud_provider=cloud_provider,
            event_data=finding_data,
        )

        return param_creator.get_parameters()

    def _get_current_alert_cloud_provider(self) -> SCCEDatamodels.CloudProviderEnum:
        sg_id = get_alert_source_group_identifier(self.soar_action.current_alert)
        return get_cloud_provider_from_source_group_id(sg_id)

    def _add_table_to_description(self, description: str) -> str:
        findings: list[dict[str, str]] = self._get_scc_finding_context()
        finding_context: list[SCCEDatamodels.FindingContext] = [
            SCCEDatamodels.FindingContext(**finding_json) for finding_json in findings
        ]
        table = self._create_desc_table(finding_context)
        return self._update_desc_with_table(table, description)

    def _get_scc_finding_context(self) -> list[dict[str, str]]:
        self.logger.info("Getting finding state context")
        scc_finding_states = self._get_scc_finding_states()
        self.logger.info(f"Found {len(scc_finding_states)} findings to process")
        return scc_finding_states

    def _get_scc_finding_states(self) -> list[dict[str, str]]:
        try:
            scc_finding_context: dict[str, list[dict[str, str]]]
            scc_finding_context = json.loads(
                self.soar_action.get_case_context_property(
                    SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY
                )
            )
        except Exception as e:
            raise GetCaseContextError(
                f"Failed to get case context.\n"
                'Make sure to run "Set SCC-FINDINGS-STATE Context Value" '
                f"action first. Error: {e}"
            ) from e

        if not scc_finding_context:
            raise ValueError(
                "Case context is empty, cannot create description.\n"
                'Make sure to run "Set SCC-FINDINGS-STATE Context Value" '
                f"action first. Case context: {scc_finding_context!r}"
            )

        return scc_finding_context["finding_context_list"]

    def _create_desc_table(self, findings: list[SCCEDatamodels.FindingContext]) -> str:
        if self.output_type == SCCEDatamodels.DescriptionOutputType.HTML:
            return create_html_table(findings, self._soar_action.platform_url)

        return create_jwm_table(findings, self._soar_action.platform_url)

    def _update_desc_with_table(self, table: str, description: str) -> str:
        if self.output_type == SCCEDatamodels.DescriptionOutputType.HTML:
            return update_html_desc_table(table, description)

        return update_jira_wiki_desc_table(table, description)

    def _fix_sdk_stdout(self) -> None:
        def end_script() -> NoReturn:
            output_object = self.soar_action._build_output_object()
            SiemplifyUtils.resume_stdout()
            sys.stdout.write(json.dumps(output_object))
            sys.exit(0)

        self.soar_action.end_script = end_script


def _create_json_result(description: str) -> SingleJson:
    return {
        "description": json.dumps(description),
        "unescaped_description": description,
    }


def main() -> NoReturn:
    PrepareDescription(SCCEnterpriseConsts.PREPARE_DESC_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
