# Design Document: MP Describe - Parameter Description Table Agent PoC

## 1. Objective
Create a Proof of Concept (PoC) to improve the generation of the parameter description table within the `mp describe` tool. This will be achieved by introducing a dedicated agent, invoked via a prompt override, which exclusively handles parsing the parameters and generating their markdown documentation. The agent will utilize a tool-driven feedback loop to validate and self-correct its output before returning the final result.

## 2. Background / Context
Currently, the `mp describe` tool uses a prompt to generate various elements based on the provided action information, including the parameter descriptions. By delegating the parameter table generation to a specialized agent, we can:
- Isolate the prompt context specifically for parameter documentation requirements.
- Introduce structured validation and self-reflection steps to ensure higher quality output.
- Enforce strict formatting (markdown tables) and ensure complete coverage without hallucinating or leaking integration-level details.

## 3. High-Level Architecture
The PoC will consist of the following components:

### 3.1. Parent Orchestrator (MP Describe)
The main execution flow will use a **prompt override** to delegate the parameter table generation step to the new Specialized Agent. It will pass all necessary context to the agent (e.g., action definition JSON, python script insights, parameter metadata).

### 3.2. Parameter Description Agent (Specialized Agent)
An AI agent initialized with a targeted system prompt, making it an expert in accurately documenting action parameters as a Markdown table.
- **Inputs:** Action information (JSON settings file content, associated Python script metadata).
- **Workflow:** Generates a draft Markdown table, reviews the table against strict criteria using tools, and refines it iteratively until all quality checks pass.

## 4. Agent Tools
The agent will be equipped with specialized tools to enforce the generation and feedback loop:

### Tool 1: `generate_parameter_table`
- **Description:** Generates an initial draft of the parameter documentation based on the action information. *(Note: This can be implemented either as a dedicated JSON-in-Markdown-out tool, or the agent can draft it internally in its reasoning step).*
- **Inputs:** `action_json_metadata`, `python_script_metadata`
- **Outputs:** `draft_markdown_table` (String).

### Tool 2: `validate_parameter_table`
- **Description:** Validates a drafted parameter table against a pre-defined set of rigorous questions.
- **Inputs:** `draft_markdown_table`
- **Pre-defined Validation Questions:**
  1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file?
  2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)?
  3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file?
  4. If the original action has zero parameters defined, did the AI output the exact string: `There are no parameters for this action` instead of a table?
  5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: `| Parameter | Type | Mandatory | Description |`?
  6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table?
  7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column?
  8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes?
- **Outputs:**
  - `is_valid` (Boolean): True if it passed all checks.
  - `feedback` (String): Detailed explanation of which questions failed and actionable steps to fix them (e.g., "Parameter X is missing from the table", "Column headers do not exactly match").

### Tool 3: `submit_final_table`
- **Description:** Submits the validated and finalized content back to the orchestrator.
- **Inputs:** `final_markdown_table`

## 5. Execution Workflow (Sequence)
1. **Initialize:** `mp describe` hits the prompt override and launches the Parameter Description Agent, passing the action data.
2. **Drafting:** The Agent calls `generate_parameter_table` to get a baseline draft.
3. **Validation:** The Agent calls `validate_parameter_table(draft_markdown_table)`.
4. **Self-Correction (The Loop):** If `is_valid` is false, the Agent reads the `feedback`, adjusts the draft to address the issues, and re-runs `validate_parameter_table(new_draft)`.
5. **Completion:** Once `is_valid` is true, the Agent invokes `submit_final_table` to exit and return the value exactly as vetted.

## 6. Milestones & Success Criteria
- **Milestone 1:** Define the prompt override trigger and the Agent's system instructions.
- **Milestone 2:** Implement the tools (`generate`, `validate`, `submit`).
- **Milestone 3:** Wire up the validation tool to automatically execute the 8 predefined checks.
- **Milestone 4:** End-to-end testing of the agent loop against edge cases (zero parameters, complex conditional parameters, undocumented defaults).
- **Success Criteria:** The PoC successfully generates and self-corrects parameter documentation autonomously, achieving 100% adherence to the defined questions without human intervention.
