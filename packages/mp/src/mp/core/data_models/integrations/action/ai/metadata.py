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

from typing import Annotated

from pydantic import BaseModel, Field

from .capabilities import ActionCapabilities  # ruff:ignore[typing-only-first-party-import]
from .entity_usage import EntityUsage  # ruff:ignore[typing-only-first-party-import]
from .outcome_categories import OutcomeCategories  # ruff:ignore[typing-only-first-party-import]


class ImpactAnalysisActionsMetadata(BaseModel):
    volume_risk_reasoning: Annotated[
        str,
        Field(
            description=(
                "Step-by-step reasoning evaluating the scale of deployment (localized to a single target, small subset, or broad-scale across an entire fleet)."
            ),
        ),
    ] = ""
    scope_risk_reasoning: Annotated[
        str,
        Field(
            description=(
                "Step-by-step reasoning measuring the breadth of impact on the spectrum from an isolated user account/workstation "
                "up to foundational corporate infrastructure."
            ),
        ),
    ] = ""
    friction_risk_reasoning: Annotated[
        str,
        Field(
            description=(
                "Step-by-step reasoning evaluating the extent to which mistaken execution halts standard employee productivity if it occurs as a false positive."
            ),
        ),
    ] = ""
    reversibility_risk_reasoning: Annotated[
        str,
        Field(
            description=(
                "Step-by-step reasoning evaluating the ease with which a human operator can undo an action if the agent errs. "
                "State whether the action is fully reversible, partially reversible with manual intervention, or completely irreversible."
            ),
        ),
    ] = ""
    asset_criticality_relevance: Annotated[
        bool,
        Field(
            description=(
                "A Boolean indicator (true or false) indicating whether the action's primary purpose is read-only data enrichment/retrieval "
                "AND its response data helps calculate the asset criticality level for assets or entities."
            ),
        ),
    ] = False
    asset_criticality_relevance_reasoning: Annotated[
        str,
        Field(
            description=(
                "Step-by-step rationale evaluating whether the action's primary purpose is data enrichment/retrieval and whether its response payload "
                "can help calculate asset criticality. Evaluates: 1. Operation Type Check, 2. Asset or Group Identifier Presence, "
                "3. Discovery of Pre-existing Metadata/Scope Signals, 4. Downstream Utility."
            ),
        ),
    ] = ""
    volume_risk_score: Annotated[
        str,
        Field(
            description=(
                "Score evaluating the scale of deployment (Low, Medium, or High)."
            ),
        ),
    ] = ""
    scope_risk_score: Annotated[
        str,
        Field(
            description=(
                "Score measuring the breadth of impact from isolated target up to foundational corporate infrastructure (Low, Medium, or High)."
            ),
        ),
    ] = ""
    friction_risk_score: Annotated[
        str,
        Field(
            description=(
                "Score evaluating the extent to which mistaken execution halts standard employee productivity (Low, Medium, or High)."
            ),
        ),
    ] = ""
    reversibility_risk_score: Annotated[
        str,
        Field(
            description=(
                "Score evaluating the ease with which a human operator can undo an action if the agent errs (Low, Medium, or High)."
            ),
        ),
    ] = ""
    asset_criticality_categories: Annotated[
        list[str],
        Field(
            default_factory=list,
            description=(
                "When asset_criticality_relevance is enabled, map the operation to any of the following five classification buckets "
                "based on the returned metadata and environmental context: 'Enrichment: Asset Risk & Reputation', "
                "'Enrichment: Identity & Organizational Context', 'Enrichment: Organizational Network Context', "
                "'Enrichment: Endpoint Telemetry & Vulnerability', 'Enrichment: External Network Routing'. "
                "Multiple categories may be assigned for multi-faceted payloads. If relevance is false, return an empty array `[]`."
            ),
        ),
    ]
    asset_criticality_categories_reasoning: Annotated[
        str,
        Field(
            description=(
                "Provide a concise, single-sentence rationale justifying the selected categories based on the function logic and expected response data. "
                "State 'Not applicable as relevance is false' if relevance is disabled."
            ),
        ),
    ] = ""


class ActionAiMetadata(BaseModel):
    ai_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description that will be used by LLMs to understand what the action does."
                " This should be an informative summary of the action's purpose and expected outcome."
                " Use markdown formatting for clarity, as this is a description for LLMs."
                " The description must be divided into 3 distinct sections: 'General Description',"
                " 'Flow Description', and 'Additional Notes'."
                " Under the 'Flow Description' section, please add a description of the flow of the action"
                " in numbered or bulleted points to describe each stage of the action logically."
                " If an API call is being made during the execution of this action, it must be explicitly"
                " mentioned and detailed within this flow description."
            ),
        ),
    ]
    ai_short_description: Annotated[
        str,
        Field(
            description=(
                "A concise, high-level summary of the action's primary purpose and expected outcome."
                " This should be a direct, single-paragraph distillation of the 'General Description'"
                " designed for quick LLM parsing, completely free of step-by-step flow overhead"
                " or parameter details."
            ),
        ),
    ]
    parameters_description: Annotated[
        str,
        Field(
            description=(
                "Detailed description of the action's parameters, formatted using markdown for LLM clarity."
                "CRITICAL SOURCE CONSTRAINT: You must extract parameter information EXCLUSIVELY from the action's "
                "parameters list (under 'Parameters' or 'parameters' key in the metadata definitions). You "
                "are strictly "
                "forbidden from including, inferring, or falling back to any integration-level parameters "
                "(including parameters retrieved via siemplify.extract_configuration_param or listed under "
                "integration-level configurations)."
                "Create a table that describes these action-specific parameters with the following columns: "
                "Parameter, Type, Mandatory, Description."
                "The Description column should explain how to use the parameter and how it might affect the "
                "action's flow."
                "If there are no action-specific parameters defined, you must NOT generate a table. Instead, "
                "set this field value exactly to: 'There are no parameters for this action'."
                "If a parameter is not mandatory but code execution requires it based on the presence of other "
                "parameters, mention this relationship within its specific row description, or add an optional "
                "'Parameter Notes' section below the table (e.g., 'Either this set of parameters or this set of "
                "parameters must be configured')."
            ),
        ),
    ]
    entity_usage: Annotated[
        EntityUsage,
        Field(
            description=(
                "A detailed set of properties that describe how the action uses entities."
                " Determine each of the fields by going over the code."
            ),
        ),
    ]
    outcome_categories: Annotated[
        OutcomeCategories,
        Field(
            description=(
                "Describes what the action achieves - its expected outcomes."
                " This field classifies the action based on what it does, rather than how it operates."
            ),
        ),
    ]
    capabilities: Annotated[
        ActionCapabilities,
        Field(
            description=(
                "Fields that describe how the action operates. Determine these fields based on the"
                "metadata json and the code itself."
            ),
        ),
    ]
    impact_analysis_actions_metadata: Annotated[
        ImpactAnalysisActionsMetadata,
        Field(
            description=(
                "Metadata related to impact analysis, including risk scores, reasonings, and asset criticality."
            ),
        ),
    ]


ActionAiMetadata.model_rebuild()
