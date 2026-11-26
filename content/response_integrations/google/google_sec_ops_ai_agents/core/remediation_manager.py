# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Remediation Manager for initialization and status fetches."""
from __future__ import annotations

from typing import TYPE_CHECKING

from .data_models import (
    RemediationActionExecutionsList,
    RemediationPlan,
    RemediationPlanList,
)

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger

    from .api_client import ChronicleInvestigationApiClient


class RemediationManager:
    """Manager for remediation plan initialization, action monitoring, and status fetching."""

    def __init__(
        self,
        api_client: ChronicleInvestigationApiClient,
        logger: ScriptLogger,
    ) -> None:
        """Initialize RemediationManager.

        Args:
            api_client: The Chronicle API client instance.
            logger: The script logger instance.
        """
        self.api_client = api_client
        self.logger = logger

    def test_connectivity(self) -> None:
        self.logger.info("Testing connectivity")
        self.api_client.test_connectivity()

    def list_remediation_plans(
        self,
        alert_id: str | None = None,
        filter: str | None = None,
        order_by: str | None = None,
        expand: str | None = None,
        page_size: int | None = None,
        limit: int | None = None,
    ) -> RemediationPlanList:
        """Fetch a list of existing remediation plans for the alert.

        Args:
            alert_id: Optional SIEM alert identifier.
            filter: Optional filter string for filtering plans.
            order_by: Optional order by expression for sorting plans.
            expand: Optional expand parameter to include related resources.
            page_size: Optional page size for pagination.
            limit: Optional maximum number of plans to fetch in total.

        Returns:
            RemediationPlanList instance.
        """
        self.logger.info(f"Listing remediation plans for alert: {alert_id}")
        raw_plans = self.api_client.list_remediation_plans(
            alert_id=alert_id,
            filter=filter,
            order_by=order_by,
            expand=expand,
            page_size=page_size,
            limit=limit,
        )
        return RemediationPlanList.from_dict({"remediation_plans": raw_plans})

    def generate_remediation_plan(self, alert_id: str) -> RemediationPlan:
        """Trigger a new remediation plan generation for the alert.

        Args:
            alert_id: SIEM alert identifier.
            parent: Optional GCP AIP parent collection resource name.

        Returns:
            RemediationPlanDetails instance.
        """
        self.logger.info(f"Generating remediation plan for alert: {alert_id}")
        raw_resp = self.api_client.generate_remediation_plan(alert_id)
        return RemediationPlan.from_dict(raw_resp)

    def get_remediation_plan_details(self, plan_id: int) -> RemediationPlan:
        """Fetch details, actions status, and summary for a specific remediation plan.

        Args:
            plan_id: Remediation plan identifier.

        Returns:
            RemediationPlanDetails instance.
        """
        self.logger.info(f"Fetching details for remediation plan: {plan_id}")
        raw_plan = self.api_client.get_remediation_plan(plan_id)
        return RemediationPlan.from_dict(raw_plan)

    def list_remediation_action_executions(
        self,
        plan_id: int | str,
        filter: str | None = None,
        order_by: str | None = None,
        include_all_executions: bool | None = None,
        page_size: int | None = None,
        limit: int | None = None,
    ) -> RemediationActionExecutionsList:
        """Fetch execution records for actions within a remediation plan.

        Args:
            plan_id: Remediation plan identifier.
            filter: Optional filter string for filtering action executions.
            order_by: Optional order by expression for sorting action executions.
            include_all_executions: Optional flag to include all historical executions or just the latest.
            page_size: Optional page size for pagination.
            limit: Optional maximum number of action executions to fetch in total.

        Returns:
            RemediationActionExecutionsList instance.
        """
        self.logger.info(f"Fetching action executions for plan: {plan_id}")
        action_executions = self.api_client.list_remediation_action_executions(
            plan_id=plan_id,
            filter=filter,
            order_by=order_by,
            include_all_executions=include_all_executions,
            page_size=page_size,
            limit=limit,
        )
        return RemediationActionExecutionsList.from_dict(
            {"remediation_action_executions": action_executions}
        )
