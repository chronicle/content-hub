from __future__ import annotations

from ..core.base_action import RubrikFileDownloadAction
from ..core.constants import DOWNLOAD_REMEDIATION_LOG_SCRIPT_NAME, USER_FILE_TYPE_LOG

# RSC names remediation log downloads as "<object_name> actions log...".
# Matching on this exact pattern (not just the bare object name) prevents this action from
# ever picking up a concurrent download triggered for a different object.
REMEDIATION_LOG_FILENAME_SUFFIX: str = " actions log"


class DownloadRemediationLog(RubrikFileDownloadAction):
    rubrik_error_prefix = "Failed to generate remediation log"
    file_type = USER_FILE_TYPE_LOG
    file_label = "remediation log"
    default_filename = "remediation_log.csv"

    def __init__(self, is_first_run: bool | None = None) -> None:
        super().__init__(DOWNLOAD_REMEDIATION_LOG_SCRIPT_NAME, is_first_run)

    def _trigger_generation(self) -> str:
        # Step 1: validate the inputs against the violation before triggering.
        violation_raw = self._fetch_violation()
        self._resolve_object_name(violation_raw)

        # Step 2: trigger remediation log generation (only after inputs validated).
        self.logger.info("Step 2: Creating violation remediation log.")
        remediation_id = self.api_client.trigger_remediation_log(
            violation_id=self.params.violation_id,
            resource_id=self.params.object_id,
        )
        self.logger.info(f"Step 2 complete: remediationId={remediation_id}")

        return f"{self.params.object_name}{REMEDIATION_LOG_FILENAME_SUFFIX}"

    def _success_message(self, filename: str) -> str:
        return (
            f"Remediation log '{filename}' attached to case "
            f"for violation ID: {self.params.violation_id}."
        )


def main(is_first_run: bool | None = None) -> None:
    DownloadRemediationLog(is_first_run).run()


if __name__ == "__main__":
    main()
