Determine the action-specific parameter documentation (`parameters_description`) based on the provided Action JSON Settings and Python File.

### Instructions & Rules:

1. **Table Structure & Formatting**:
   - If the action defines action-specific parameters, format the output precisely as a Markdown table with exactly these four column headers:
     `| Parameter | Type | Mandatory | Description |`
   - If the action has zero parameters defined, output the exact string:
     `There are no parameters for this action`
     (do not output a table or any markdown wrapper).

2. **Action-Specific Exclusivity & Integration Parameter Exclusion**:
   - Exclusively list action-specific parameters declared in the action definition.
   - Strictly avoid leaking or including any Integration-level parameters (e.g., API keys, Server URLs, Verify SSL, environment configuration, or parameters extracted via `siemplify.extract_configuration_param`).

3. **Parameter Traceability & Completeness**:
   - For every parameter listed in the Markdown table, an exact corresponding parameter definition must exist in the provided JSON settings file.
   - Document every single action-specific parameter declared in the JSON settings file; zero required or optional action parameters may be omitted.

4. **Parameter Name Casing & Technical Identifier Accuracy**:
   - Every entry in the `Parameter` column must use the exact technical parameter identifier (preserving real casing such as camelCase or snake_case matching the definition file), rather than human-readable display names or arbitrary titles.

5. **Parameter Type Closed List Conformance**:
   - Every entry in the `Type` column must strictly use one of the approved valid SOAR parameter types from this closed list:
     `Boolean`, `Int`, `String`, `Password`, `IP`, `Email`, `User_Repository`, `Stages_Repository`, `CloseCase_Reason_Repository`, `CloseCase_RootCause_Repository`, `Priorities_Repository`, `EmailContent`, `Content`, `Script`, `PlaybookNames`, `Entity_Type`, `List`, `TimeSpanSeconds`, `URL`, `Domain`, `Code`, `MultipleChoiceParameter`, `Other`
     accurately reflecting the type declared in the integration definition.

6. **Mandatory Column Strict Value Constraint**:
   - The `Mandatory` column must accurately reflect the integration definition's mandatory status for each parameter, using exclusively `True` when required and `False` when optional (do not use "Yes", "No", etc.).

7. **Description Column Details**:
   - **Purpose & Impact**: Clearly describe the parameter's purpose, how to use it, and how it affects the action's execution flow.
   - **Default Values & Formatting Constraints**: Explicitly state default values, integer ranges, or formatting rules (such as comma-separated lists or regex patterns) defined in the JSON settings or Python script.
   - **Exhaustive Enum / DDL Choices**: For parameters with predefined dropdown/DDL options, or where the Python script evaluates the parameter against a fixed set of constants (enums, `in [...]` list membership, dictionary keys), explicitly list all allowed choices (e.g., `Possible values: ...`).
   - **Structured String Formats**: For parameters requiring structured string formats (e.g., key-value pairs, timestamps, JSON paths), explicitly document the expected structure with concrete syntax examples.
   - **Conditional Parameter Dependencies**: If the Python script or metadata enforces conditional dependencies between parameters (e.g., "Either Parameter A or Parameter B must be configured", or "Required only if Parameter X is True"), explicitly document the dependency within the specific parameter row description or notes.

---

JSON Settings:
$json_file_content

Python File:
$python_file_content
