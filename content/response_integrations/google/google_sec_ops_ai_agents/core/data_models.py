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

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional

from dataclass_wizard import JSONWizard

if TYPE_CHECKING:
    from typing import Self
    from TIPCommon.types import ChronicleSOAR


@dataclass(slots=True, frozen=True)
class IntegrationParameters(JSONWizard):
    """Data model for integration parameters."""

    api_root: str
    verify_ssl: bool


@dataclass(slots=True, frozen=True)
class SessionAuthenticationParameters(JSONWizard):
    """Data model for session authentication parameters."""

    api_root: str
    chronicle_soar: ChronicleSOAR
    verify_ssl: bool

    @classmethod
    def from_integration_params(
        cls,
        chronicle_soar: ChronicleSOAR,
        integration_params: IntegrationParameters,
    ) -> Self:
        """Create a new instance from integration parameters.

        Args:
            chronicle_soar: The Chronicle SOAR instance.
            integration_params: The integration parameters.

        Returns:
            A new instance of the class.
        """
        return cls(
            api_root=integration_params.api_root,
            verify_ssl=integration_params.verify_ssl,
            chronicle_soar=chronicle_soar,
        )


@dataclass(slots=True, frozen=True)
class ApiParameters(JSONWizard):
    """Data model for API parameters."""

    api_root: str

    @classmethod
    def from_integration_params(cls, integration_params: IntegrationParameters) -> Self:
        """Create a new instance from integration parameters.

        Args:
            integration_params: The integration parameters.

        Returns:
            A new instance of the class.
        """
        return cls(
            api_root=integration_params.api_root,
        )


class BaseDataModel(JSONWizard):
    class _(JSONWizard.Meta):
        case = "AUTO"  # Handles mixed camelCase and snake_case transparently


# --- Enums for RemediationPlanExecution ---

class RemediationPlanExecutionState(str, Enum):
    UNSPECIFIED = "REMEDIATION_PLAN_EXECUTION_STATE_UNSPECIFIED"
    IN_PROGRESS = "REMEDIATION_PLAN_EXECUTION_STATE_IN_PROGRESS"
    EXECUTED = "REMEDIATION_PLAN_EXECUTION_STATE_EXECUTED"
    REJECTED = "REMEDIATION_PLAN_EXECUTION_STATE_REJECTED"
    ERROR = "REMEDIATION_PLAN_EXECUTION_STATE_ERROR"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the execution state."""
        return self.name.replace("_", " ").title()


class RemediationPlanExecutionSummaryState(str, Enum):
    UNSPECIFIED = "REMEDIATION_PLAN_EXECUTION_SUMMARY_STATE_UNSPECIFIED"
    IN_PROGRESS = "REMEDIATION_PLAN_EXECUTION_SUMMARY_STATE_IN_PROGRESS"
    EXECUTED = "REMEDIATION_PLAN_EXECUTION_SUMMARY_STATE_EXECUTED"
    REJECTED = "REMEDIATION_PLAN_EXECUTION_SUMMARY_STATE_REJECTED"
    ERROR = "REMEDIATION_PLAN_EXECUTION_SUMMARY_STATE_ERROR"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the execution summary state."""
        return self.name.replace("_", " ").title()


# --- RemediationPlanExecution Model ---

@dataclass
class RemediationPlanExecution(BaseDataModel):
    """Represents a single execution instance of a Remediation Plan."""

    remediation_plan: Optional[str] = None
    state: Optional[RemediationPlanExecutionState] = None
    summary_status: Optional[RemediationPlanExecutionSummaryState] = None
    actions_count: Optional[int] = None
    pending_action_count: Optional[int] = None
    success_actions_count: Optional[int] = None
    failure_actions_count: Optional[int] = None
    summary: Optional[str] = None
    additional_data: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None


# --- RemediationActionExecution Model ---

class RemediationActionExecutionState(str, Enum):
    UNSPECIFIED = "REMEDIATION_ACTION_EXECUTION_STATE_UNSPECIFIED"
    INITIALIZED = "REMEDIATION_ACTION_EXECUTION_STATE_INITIALIZED"
    IN_PROGRESS = "REMEDIATION_ACTION_EXECUTION_STATE_IN_PROGRESS"
    SUCCESS = "REMEDIATION_ACTION_EXECUTION_STATE_SUCCESS"
    FAILURE = "REMEDIATION_ACTION_EXECUTION_STATE_FAILURE"


@dataclass
class RemediationActionExecution(BaseDataModel):
    """Represents a single execution record for an individual Remediation Action."""

    name: Optional[str] = None
    remediation_plan_execution: Optional[str] = None
    state: Optional[RemediationActionExecutionState] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    action_result: Optional[dict[str, Any]] = None


@dataclass
class RemediationActionExecutionsList(BaseDataModel):
    """Response message for listing remediation action executions."""

    remediation_action_executions: list[RemediationActionExecution] = field(default_factory=list)


# --- Inner Payload Models ---

@dataclass
class UsageMetadata(BaseDataModel):
    candidates_token_count: Optional[int] = None
    prompt_token_count: Optional[int] = None
    total_token_count: Optional[int] = None


@dataclass
class InvolvedEntity(BaseDataModel):
    entity_identifier: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class PlanData(BaseDataModel):
    planning_summary: Optional[str] = None
    involved_entities: list[InvolvedEntity] = field(default_factory=list)
    usage_metadata: Optional[UsageMetadata] = None


@dataclass
class TargetEntityDetail(BaseDataModel):
    entity_identifier: Optional[str] = None
    entity_type: Optional[str] = None
    entity_reasoning: Optional[str] = None


@dataclass
class ActionAdditionalData(BaseDataModel):
    action_status: Optional[str] = None
    target_entities_details: list[TargetEntityDetail] = field(default_factory=list)


# --- Action & Plan Models ---

@dataclass
class TargetEntity(BaseDataModel):
    identifier: Optional[str] = None


@dataclass
class RemediationAction(BaseDataModel):
    name: Optional[str] = None
    integration_id: Optional[str] = None
    integration_instance: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[str] = None
    creator: Optional[str] = None
    action_reasoning: Optional[str] = None
    target_entities: list[TargetEntity] = field(default_factory=list)
    additional_data: Optional[ActionAdditionalData] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None


class RemediationPlanState(str, Enum):
    """The state of the Remediation plan."""

    UNSPECIFIED = "REMEDIATION_PLAN_STATE_UNSPECIFIED"
    INITIALIZED = "REMEDIATION_PLAN_STATE_INITIALIZED"
    REQUESTED = "REMEDIATION_PLAN_STATE_REQUESTED"
    SUGGESTED = "REMEDIATION_PLAN_STATE_SUGGESTED"
    ERROR = "REMEDIATION_PLAN_STATE_ERROR"
    APPROVED = "REMEDIATION_PLAN_STATE_APPROVED"
    DECLINED = "REMEDIATION_PLAN_STATE_DECLINED"

    @property
    def display_name(self) -> str:
        """Human-readable display name for the plan state."""
        return self.name.replace("_", " ").title()


class RemediationPlanTriggerType(str, Enum):
    """The trigger type of the Remediation plan."""

    UNSPECIFIED = "REMEDIATION_PLAN_TRIGGER_TYPE_UNSPECIFIED"
    AUTOMATIC = "REMEDIATION_PLAN_TRIGGER_TYPE_AUTOMATIC"
    MANUAL = "REMEDIATION_PLAN_TRIGGER_TYPE_MANUAL"


@dataclass
class RemediationPlan(BaseDataModel):
    """Represents an AI-driven Remediation Plan for a specific alert or case."""

    name: Optional[str] = None
    alert_name: Optional[str] = None
    case_id: Optional[int] = None
    alert_id: Optional[str] = None
    siem_alert_id: Optional[str] = None
    agent_session_id: Optional[str] = None
    state: Optional[RemediationPlanState] = None
    trigger_type: Optional[RemediationPlanTriggerType] = None
    status_details: Optional[str] = None
    agent_classified_use_case: Optional[str] = None
    plan_data: Optional[PlanData] = None
    plan_metadata: Optional[dict[str, Any]] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    actions: Optional[list[RemediationAction]] = None
    latest_execution: Optional[RemediationPlanExecution] = None

    @cached_property
    def plan_id(self) -> Optional[str]:
        """Extracts the plan ID from the resource name path.

        Example: '.../remediationPlans/28' -> '28'
        """
        if not self.name:
            return None

        prefix, sep, plan_id = self.name.rpartition("/remediationPlans/")
        return plan_id if sep else self.name.rstrip("/").rpartition("/")[-1]


@dataclass
class RemediationPlanList(BaseDataModel):
    remediation_plans: list[RemediationPlan] = field(default_factory=list)
