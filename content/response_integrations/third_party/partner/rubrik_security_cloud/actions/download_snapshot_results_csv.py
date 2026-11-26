from __future__ import annotations

from ..core.base_action import RubrikFileDownloadAction, validate_uuid_param
from ..core.constants import DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME, USER_FILE_TYPE_CSV
from ..core.rubrik_exceptions import ItemNotFoundException

# RSC names snapshot-results CSV downloads as "<object_name>-violating-files_file_results...".
# Matching on this exact pattern (not just the bare object name) prevents this action from
# ever picking up a concurrent download triggered for a different object.
SNAPSHOT_CSV_FILENAME_SUFFIX: str = "-violating-files_file_results"


class DownloadSnapshotResultsCsv(RubrikFileDownloadAction):
    """Generate a violation's snapshot results CSV in RSC and attach it to the case."""

    rubrik_error_prefix = "Failed to generate snapshot results CSV"
    file_type = USER_FILE_TYPE_CSV
    file_label = "snapshot results CSV"
    default_filename = "snapshot_results.csv"

    def __init__(self, is_first_run: bool | None = None) -> None:
        super().__init__(DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME, is_first_run)

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.snapshot_id = self._extract_string_param("Snapshot ID", is_mandatory=True)

    def _validate_params(self) -> None:
        super()._validate_params()
        self.params.snapshot_id = validate_uuid_param(self.params.snapshot_id, "Snapshot ID")

    def _trigger_generation(self) -> str:
        object_id: str = self.params.object_id
        violation_id: str = self.params.violation_id
        snapshot_id: str = self.params.snapshot_id

        # Step 1: validate the inputs against the violation before triggering.
        violation_raw = self._fetch_violation()

        # Validate Snapshot ID matches the violation's snapshotId.
        expected_snapshot_id = (violation_raw.get("details") or {}).get("snapshotId") or ""
        if snapshot_id.strip().lower() != expected_snapshot_id.strip().lower():
            raise ItemNotFoundException(
                f"Snapshot ID '{snapshot_id}' does not match the snapshot of violation ID "
                f"{violation_id} (expected '{expected_snapshot_id}')."
            )

        # Resolve/validate Object Name from the same response.
        self._resolve_object_name(violation_raw)

        # Step 2: trigger CSV generation (only after all inputs are validated).
        self.logger.info("Step 2: Triggering snapshot results CSV generation.")
        self.api_client.trigger_snapshot_csv(
            snappable_fid=object_id,
            snapshot_fid=snapshot_id,
            violation_id=violation_id,
        )
        self.logger.info("Step 2 complete: CSV generation triggered.")

        # RSC replaces spaces in the object name with hyphens when naming the
        # download (e.g. "User Action Level" -> "User-Action-Level-violating-...").
        sanitized_object_name = self.params.object_name.replace(" ", "-")
        return f"{sanitized_object_name}{SNAPSHOT_CSV_FILENAME_SUFFIX}"

    def _success_message(self, filename: str) -> str:
        return (
            f"CSV file '{filename}' attached to case. "
            f"Contains files at risk for violation ID: {self.params.violation_id}."
        )


def main(is_first_run: bool | None = None) -> None:
    DownloadSnapshotResultsCsv(is_first_run).run()


if __name__ == "__main__":
    main()
