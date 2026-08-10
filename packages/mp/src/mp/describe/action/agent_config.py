from mp.describe.action.agent_factory import AgentConfig

PARAMETERS_VALIDATION = """
1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file?
2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)?
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file?
4. If the original action has zero parameters defined, did the AI output the exact string: 'There are no parameters for this action' instead of a table?
5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description |?
6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table?
7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column?
8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes?
"""

OUTCOME_CATEGORIES_VALIDATION = """
1. For every outcome category flagged as True, does the Python script make an explicit, physical API call to execute that specific outcome, or did the AI hallucinate it based on the name of the action or assumptions about standard playbooks?
2. Did the AI correctly respect the boundary between data enrichment (reading) and state mutation (writing)? (e.g. if add_ioc_to_blocklist or disable_identity is True, verify that a POST/PUT/PATCH request is sent; if it's only a GET request, these mutation categories must fail the evaluation)
3. Based on the provided outcome definitions, did the AI omit (flag as False) any category that is explicitly performed in the action code?
4. Does the text provided in the reasoning field logically trace the True flags directly to specific functionalities, loops, or API endpoints found in the provided Python code snippet?
"""

ENTITY_USAGE_VALIDATION = """
1. Did the AI accurately verify if the action iterates over `target_entities` or uses entity-specific identifiers, as opposed to just looking at a variable named `entity` string matching?
2. If the action does NOT work on entities (e.g. fetching a static URL or using unrelated data), are all flags across the entites properly set to False?
3. If the action code specifically filters entities by type (e.g. `if entity.type == "USER"`), are only those specific flag types set to True? 
4. Alternatively, if no type filtering is applied and the action processes the entire `target_entities` list, are ALL available entity types set to True?
5. Did the AI correctly trace each true filter flag (like `filters_by_identifier`, `filters_by_entity_type`, `filters_by_is_suspicious` etc.) to an explicit conditional check (e.g. `if ...`) in the provided Python code?
6. Does the reasoning step explicitly state why each filtering condition is met or not met based on the Python code snippet before setting the boolean flags?
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
