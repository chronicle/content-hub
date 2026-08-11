from mp.describe.action.agent_factory import AgentConfig

PARAMETERS_VALIDATION = """
1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file?
2. Does the ai successfully avoid leaking any Integration-level parameters - (like API, base URL or others)?
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file?
4. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description | Otherwise if the original action has zero parameters defined, does the AI output the exact string: 'There are no parameters for this action' instead of a table?
5. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table?
6. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column?
7. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes?
8. Does the 'Mandatory' column accurately reflect the integration definition's mandatory status for each parameter, using exclusively 'True' when required and 'False' when optional?
9. For every parameter that has predefined dropdown/DDL options in the specification, or where the Python script evaluates the parameter against a fixed set of constants (such as enums, list membership tests like 'in [...]', or dictionary mappings), are all allowed choices explicitly listed in the Description column (e.g., 'Possible values: ...')?
10. If a parameter requires a structured string format (e.g. key-value pairs, placeholder-separated tokens, timestamps, or JSON paths), does the Description column explicitly document the expected structure with concrete syntax examples?
11. Does every entry in the 'Parameter' column use the exact technical parameter identifier (preserving real casing such as camelCase or snake_case matching the integration's definition file), rather than human-readable display names or arbitrary titles?
12. Does every entry in the 'Type' column strictly use one of the valid SOAR parameter types from the approved closed list: 'Boolean', 'Int', 'String', 'Password', 'IP', 'Email', 'User_Repository', 'Stages_Repository', 'CloseCase_Reason_Repository', 'CloseCase_RootCause_Repository', 'Priorities_Repository', 'EmailContent', 'Content', 'Script', 'PlaybookNames', 'Entity_Type', 'List', 'TimeSpanSeconds', 'URL', 'Domain', 'Code', 'MultipleChoiceParameter', 'Other', accurately reflecting the type declared in the integration definition?
"""

OUTCOME_CATEGORIES_VALIDATION = """
1. For every outcome category flagged as True, does the Python script make an explicit, physical API call
    to execute that specific outcome, or did the AI hallucinate it based on the name of the action or
    assumptions about standard playbooks?
    Evaluate every `True` outcome category strictly against the provided Python code. Fail the response if the AI
    awarded a `True` flag based on what an analyst "might do next" with the data rather than what the script actively executes.
2. Did the AI correctly respect the boundary between data enrichment (reading) and state mutation (writing)?
    If any mutating categories (e.g., contain_host, add_ioc_to_blocklist, disable_identity, update_alert, create_ticket, update_ticket)
    are `True`, explicitly verify that the script performs an external write operation (POST/PUT/PATCH/DELETE) or internal platform update.
    If it only performs a GET/read operation, these mutation categories must be `False` and fail the evaluation if flagged as `True`.
3. Based on the provided outcome definitions, did the AI omit (flag as False) any category that is explicitly performed in the action code?
    Ensure no valid outcomes were mistakenly flagged as `False` if the script demonstrably executes them.    
4. Does the text provided in the reasoning field logically trace the True flags directly to specific functionalities,
    loops, or API endpoints found in the provided Python code snippet?
    Ensure the `reasoning` string explicitly cites mechanisms, methods, and endpoints in the Python code to justify the `True` categorizations.
"""

ENTITY_USAGE_VALIDATION = """
- title: "entity_usage - Active Processing of Target Entities"
  target_field: "entity_usage"
  criteria: >
    Did the AI correctly identify whether the action processes platform target entities
    (via siemplify.target_entities or input parameters representing entities)?

- title: "entity_usage - Unused Entity Flags Set to False"
  target_field: "entity_usage"
  criteria: >
    If the Python script does not process entities from the platform, are ALL entity
    type flags correctly set to False?

- title: "entity_usage - Specific Entity Type Conditional Filtering"
  target_field: "entity_usage"
  criteria: >
    For every specific entity type flagged as True (e.g., address), is that entity type validly targeted
    through at least one of the following mechanisms?
    1. Explicit Code Filter: The Python code explicitly contains a programmatic conditional check or filter targeting that specific type (e.g., entity.entity_type == EntityTypes.ADDRESS or checking against a set/list of supported types).
    2. Input Parameter Mapping: The action accepts or processes input parameters that explicitly target or represent that entity type.
    3. Unfiltered (Global) Scope: The Python script iterates over target_entities without type-specific filtering, applying globally to all supported entity types (excluding any types explicitly omitted via negative exclusion filters, such as excluding ALERT pseudo-entities).
    4. Dynamic Entity Resolution: The action dynamically resolves entities across case alerts (e.g., via alert.entities or _get_target_alerts()) and allows operating on any entity type via dynamic parameters.

- title: "entity_usage - Unfiltered Entity Types Defaulting to True"
  target_field: "entity_usage"
  criteria: >
    If the Python script iterates over target_entities without type-based filtering, did the AI
    correctly set ALL supported entity type flags to True (excluding any specific pseudo-entity types
    explicitly omitted via negative exclusion filters, such as setting alert: false)?

"""

AGENTS_CONFIG = {
    "parameters_description": AgentConfig(
        field_name="parameters_description",
        validation_questions=PARAMETERS_VALIDATION,
        model_name="gemini-3.1-pro-preview",
        temperature=0.1,
        max_retries=3
    ),
    "outcome_categories": AgentConfig(
        field_name="outcome_categories",
        validation_questions=OUTCOME_CATEGORIES_VALIDATION,
        model_name="gemini-3.1-pro-preview",
        temperature=0.1,
        max_retries=3
    ),
    "entity_usage": AgentConfig(
        field_name="entity_usage",
        validation_questions=ENTITY_USAGE_VALIDATION,
        model_name="gemini-3.1-pro-preview",
        temperature=0.1,
        max_retries=3
    ),
}

AI_DESCRIPTION_VALIDATION = """
1. Is the description divided precisely into exactly these 3 distinct sections with exactly these headers: "General Description", "Flow Description", and "Additional Notes"?
2. Under the "Flow Description" section, is the flow of the action described in numbered or bulleted points, systematically detailing each stage?
3. If an API call is made in the Python codebase, is the exact API endpoint or method explicitly detailed within the flow description?
4. Are markdown formatting conventions consistently and correctly applied without generating extraneous markdown wrappers around the entire output?
"""

AI_SHORT_DESCRIPTION_VALIDATION = """
1. Is the short description exactly a single, concise paragraph?
2. Did the AI successfully avoid including any step-by-step flow overhead, parameter details, or bulleted lists?
3. Does it directly distill the primary purpose and expected outcome of the action into a high-level summary without hallucinating absent features?
"""

AGENTS_CONFIG["ai_description"] = AgentConfig(
    field_name="ai_description",
    validation_questions=AI_DESCRIPTION_VALIDATION,
    model_name="gemini-3.1-pro-preview",
    temperature=0.1,
    max_retries=3
)

AGENTS_CONFIG["ai_short_description"] = AgentConfig(
    field_name="ai_short_description",
    validation_questions=AI_SHORT_DESCRIPTION_VALIDATION,
    model_name="gemini-3.1-pro-preview",
    temperature=0.1,
    max_retries=3
)
