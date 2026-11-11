from __future__ import annotations

import json

from TIPCommon.base.action import Action
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core.SCCEnterpriseDatamodels import FindingContext
from scc_enterprise.core.SCCEnterpriseUtils import (
    create_scc_finding_state_json,
    get_alert_source_group_identifier,
    get_cloud_provider_from_source_group_id,
    get_first_event_data,
    load_findings_context,
)


class PopulateFindingsContext(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Set or updated the  {SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY} "
            "context value"
        )
        self.error_output_message = (
            f"Failed to update {SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY}."
        )

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        self.logger.info("Reading current FINDINGS-CONTEXT value...")
        findings_context_str = self.soar_action.get_case_context_property(
            SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY
        )
        instance_url, current_findings_context = load_findings_context(
            findings_context_str
        )

        finding_data = get_first_event_data(self.soar_action)
        new_finding_context = FindingContext.build_from_finding_event_data(
            alert_identifier=self.soar_action.current_alert.identifier,
            finding_event_data=finding_data,
        )

        if new_finding_context in current_findings_context and instance_url:
            self.output_message = (
                f"{SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY} already has "
                "the finding data."
            )
            self.json_results = json.loads(findings_context_str)
            return

        self.logger.info(
            "Finding wasn't found in current "
            f"{SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY}, adding..."
        )
        source_group_id = get_alert_source_group_identifier(
            self.soar_action.current_alert
        )
        cloud_provider = get_cloud_provider_from_source_group_id(source_group_id)
        new_finding_context.cloud_provider = cloud_provider
        current_findings_context.add(new_finding_context)

        finding_context_json = create_scc_finding_state_json(
            current_findings_context, instance_url=self.soar_action.platform_url
        )
        self.soar_action.set_case_context_property(
            SCCEnterpriseConsts.FINDINGS_CONTEXT_KEY, json.dumps(finding_context_json)
        )
        self.json_results = finding_context_json


def main() -> None:
    PopulateFindingsContext(
        SCCEnterpriseConsts.POPULATE_FINDINGS_CONTEXT_SCRIPT_NAME
    ).run()


if __name__ == "__main__":
    main()
