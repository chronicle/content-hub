# Deep Dive: Jobs

**Jobs**—a Python script that runs continuously, similar to the connector, but the use case for this
script is to synchronize information between Google SecOps and Third Party Product. For example, if a
comment was added to a Google SecOps Alert, to add the same comment to a Third Party Alert. Jobs are
available under Response → Job’s Scheduler.

**Job Definition Example:**

```yaml
name: Comment on tagged cases
parameters:
    -   name: Tags
        default_value: Job Comment
        type: string
        description: Case tags that the job will comment on
        is_mandatory: true
    -   name: Comment
        default_value: Job Comment
        type: string
        description: The comment that will be written to cases with the matching tags
        is_mandatory: true
description: Job Description
integration: Integration
creator: Admin
```

**Simple Job Example:**

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import TIPCommon.consts
from soar_sdk.SiemplifyDataModel import CaseFilterStatusEnum
from TIPCommon.base.job import Job
from TIPCommon.extraction import extract_job_param
from TIPCommon.validation import ParameterValidator


if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ApiClient
    from TIPCommon.types import Contains


def main() -> None:
    CommentOnTaggedCases(name="Comment on tagged cases").start()


class CommentOnTaggedCases(Job):
    def _extract_job_params(self) -> None:
        self.params.tags = None
        self.params.tags_string = extract_job_param(
            param_name="Tags",
            siemplify=self.soar_job,
            is_mandatory=True,
            print_value=True,
        )
        self.params.comment = extract_job_param(
            param_name="Comment",
            siemplify=self.soar_job,
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_hours_back = None
        self.params.max_hours_back_string = extract_job_param(
            param_name="Max Hours Backwards",
            siemplify=self.soar_job,
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_job)
        self.params.tags = validator.validate_csv(
            param_name="Tags",
            csv_string=self.params.tags_string,
        )
        self.params.self.params.max_hours_back = validator.validate_positive(
            param_name="Max Hours Backwards",
            value=self.params.max_hours_back_string,
        )

    def _init_api_clients(self) -> Contains[ApiClient]:
        """No API Client needed for this job."""

    def _perform_job(self) -> None:
        last_run_timestamp: int = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.self.params.max_hours_back},
            time_format=TIPCommon.consts.UNIX_FORMAT,
        )

        case_ids = list[int] = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.OPEN,
            update_time_from_unix_time_in_ms=last_run_timestamp,
            start_time_from_unix_time_in_ms=last_run_timestamp,
            tags=self.params.tags,
            environments=[self.params.environment_name],
        )
        for case_id in case_ids:
            self._add_comment_to_case_by_id(case_id)

        self._save_timestamp_by_unique_id(self.job_start_time)

    def _add_comment_to_case_by_id(self, case_id: int) -> None:
        alert_ids: list[str] = self.soar_job.get_alerts_ticket_ids_by_case_id(case_id)
        if not alert_ids:
            return

        alert_id: str = alert_ids[0]
        self.soar_job.add_comment(self.params.comment, case_id, alert_id)


if __name__ == "__main__":
    main()

```