from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import ExecutionState, Link
from TIPCommon.extraction import extract_action_param

from ..core.base_action import HoudinAction
from ..core.houdin_constants import SCAN_ARTIFACT_SCRIPT_NAME
from ..core.houdin_utils import load_state, parse_scanners, scan_link, verdict_line

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

    from ..core.data_models import ScanLaunch

IN_PROGRESS_MESSAGE: str = "Houdin scan of {artifact} is in progress: {link}"
SUCCESS_MESSAGE: str = "Houdin scan of {artifact} completed. Threat score {verdict}. {link}"


class ScanArtifact(HoudinAction):
    """Scan one artifact and attach the scan document as the JSON result.

    The first run launches the scan and keeps its scanID in additional_data;
    every run reads the result once and ends IN_PROGRESS while the scan runs.
    """

    def __init__(self) -> None:
        super().__init__(SCAN_ARTIFACT_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.artifact = extract_action_param(
            self.soar_action,
            param_name="Artifact",
            is_mandatory=True,
            print_value=True,
        )
        self.params.scanners = parse_scanners(
            extract_action_param(self.soar_action, param_name="Scanners", print_value=True),
        )
        self.params.force_rescan = extract_action_param(
            self.soar_action,
            param_name="Force Rescan",
            input_type=bool,
            default_value=False,
        )
        self.params.state = load_state(extract_action_param(self.soar_action, param_name="additional_data"))

    def _perform_action(self, _: DomainEntityInfo | None = None) -> None:
        state: SingleJson | None = self.params.state
        if state is None:
            launch: ScanLaunch = self.api_client.launch_scan(
                self.params.artifact,
                self.params.scanners,
                self.params.force_rescan,
            )
            self.logger.info(f"Scan {launch.scan_id} launched, status {launch.status!r}, cached {launch.cached}")
            state = {"scanID": launch.scan_id}
        scan_id: str = state["scanID"]
        link: str = scan_link(scan_id)
        document: SingleJson | None = self.api_client.get_results([scan_id]).get(scan_id)
        if document is None:
            self.logger.info(f"Scan {scan_id} is still in progress")
            self.execution_state = ExecutionState.IN_PROGRESS
            self.result_value = json.dumps(state)
            self.output_message = IN_PROGRESS_MESSAGE.format(artifact=self.params.artifact, link=link)
            return
        self.json_results = document
        self.links = [Link(title="Open in Houdin", link=link)]
        self.result_value = True
        self.output_message = SUCCESS_MESSAGE.format(
            artifact=self.params.artifact,
            verdict=verdict_line(document),
            link=link,
        )


def main() -> None:
    ScanArtifact().run()


if __name__ == "__main__":
    main()
