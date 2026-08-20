**Input Data:**
I have provided the following files for a Google SecOps SOAR action:

1. `Script Code`: The Python logic.
2. `Script Settings`: The JSON metadata containing parameters and simulation data. Important: Integration-level parameters are provided within this JSON solely for background context.
3. `Manager Code`: The core Python manager class or API client files wrapping external service interactions.

**Objective:**
Classify the provided Google SecOps SOAR action into the **Entity Usage** (`entity_usage`) model by determining targeted entity types (35 types), identifying entity filtering attributes (13 flags), and constructing a rigorous, step-by-step reasoning string grounded in physical code evidence.

---

### Mandatory Evaluation Rules & Classification Taxonomy

1. **Entity Interaction & Presence Criteria**:
   An action "runs on entities" if it satisfies at least one of the following criteria:
   - **Platform Target Entities**: Iterates over or references `siemplify.target_entities` within the Python script.
   - **Entity Input Parameters**: Accepts or processes entity identifiers via input parameters (e.g., `Address`, `Host Name`, `User`, `URL`, `File Hash`). Accepting an entity input parameter directly activates its corresponding entity type flag as `true` (see Rule 3).
   - **SDK Helper Methods**: Calls SOAR SDK helper methods that internally iterate over or mutate alert entities (e.g., `siemplify.add_alert_entities_to_custom_list()`, `siemplify.remove_alert_entities_from_custom_list()`, and `siemplify.any_alert_entities_in_custom_list()`).
   - **Dynamic Case/Alert Aggregation**: Dynamically resolves entities across case alerts by accessing alert collections (e.g., `siemplify.case.alerts`) and extracting entity attributes (`alert.entities`), either directly or through core helper functions.

2. **Alert Storage Vehicle Negative Constraint**:
   If `alert.entities[0]` (or `siemplify.current_alert.entities[0]`) is accessed solely as a platform storage vehicle to retrieve alert-level properties (e.g., `additional_properties["SourceFileContent"]`) without any subsequent entity filtering, enrichment, or iteration, do NOT classify the action as running on entities (set all 35 entity type flags and all 13 filter flags to `false`).
   *Exception*: If the action also iterates over, filters, or updates target entities, evaluate those entity operations independently.

3. **Entity Type Scope Determination & Parameter Mapping**:
   - **Type-Filtered Scope**: If an action restricts execution to specific entity types (via code filters like `if entity.entity_type == EntityTypes.<NAME>` or entity input parameters), set boolean flags to `true` exclusively for the targeted types.
   - **Unfiltered (Global) Scope**: If an action processes entities globally without type-based filtering - either by iterating over `target_entities` (directly or via SDK helper methods) or by dynamically aggregating entities across case alerts (`siemplify.case.alerts` / `alert.entities`) - it runs on all supported entity types; set all 35 `entity_types` flags to `true`.
   - **Exclusion Logic vs. Type Filtering**: Negative conditional checks (e.g., `if entity.additional_properties.get("Type") != "<NAME>"`) are exclusion filters used to omit specific entities (`<entity>: false`). They do NOT restrict scope to specific types. If an action processes `target_entities` using an exclusion filter, ensure the excluded entity type flag is set to `false`.
   - **Generic Entity (`generic`)**: `generic` (GenericEntity) is a standalone type. Do not use it as a fallback for "all types"; only set it to `true` if explicitly filtered for, or if all flags are `true` (global scope).
   - **Parameter-to-Entity Mapping Rules**: When an action processes entities via input parameters, map parameter names to entity types according to:
$entity_type_mapping_rules

4. **Entity Filtering Attributes Classification (13 Flags)**:
   Populate boolean flags for how target entities are filtered:
   - `filters_by_identifier`: Set to `true` ONLY if the code actively filters or matches platform `siemplify.target_entities` by identifier. Do NOT set to `true` if entity parameters are used solely for entity creation or case alert duplicate checks.
   - `filters_by_creation_time` / `filters_by_modification_time`: filters entities by timestamp.
   - `filters_by_additional_properties`: filters entities by `additional_properties` dictionary keys/values.
   - `filters_by_case_identifier` / `filters_by_alert_identifier`: filters entities by parent case/alert ID.
   - `filters_by_entity_type`: filters entities by the `entity_type` attribute.
   - `filters_by_is_internal`: filters entities by the `is_internal` attribute.
   - `filters_by_is_suspicious`: filters entities by the `is_suspicious` attribute.
   - `filters_by_is_artifact`: filters entities by the `is_artifact` attribute.
   - `filters_by_is_vulnerable`: filters entities by the `is_vulnerable` attribute.
   - `filters_by_is_enriched`: filters entities by the `is_enriched` attribute.
   - `filters_by_is_pivot`: filters entities by the `is_pivot` attribute.

5. **Physical Code Traceability & Strict Classification**:
   Only set boolean flags to `true` under `entity_usage` if supported by the script's actual execution model (either through explicit type filtering/mapping OR through unfiltered global/dynamic scope). Do not set flags to `true` based on potential capability, generic placeholder functions, or print logs.

6. **Reasoning Requirement with Literal Citations**:
   You MUST provide step-by-step reasoning in the `reasoning` field quoting literal code constructs and parameter names. Explicitly state the entity interaction mechanism, the targeted entity types, and which filtering conditions are met or not met before setting the boolean flags.

---

### Generic Archetype Examples (Compact Format)

#### Example 1: Code-Filtered Enrichment Action
*Input Snippet (Python):*
```python
suitable_entities = [
    entity for entity in siemplify.target_entities
    if entity.entity_type == EntityTypes.ADDRESS and entity.is_internal
]
for entity in suitable_entities:
    manager.enrich_ip(ip=entity.identifier)
```
*Expected Output:*
```json
{
  "entity_usage": {
    "reasoning": "The action iterates over `siemplify.target_entities`. Filters explicitly using `entity.entity_type == EntityTypes.ADDRESS`, targeting only ADDRESS entities. Evaluates `entity_type` and `is_internal`. All other filter flags are false.",
    "entity_types": {
      "address": true
    },
    "filters_by_entity_type": true,
    "filters_by_is_internal": true
  }
}
```

#### Example 2: Parameter-Based Entity Action
*Input Snippet (Python & Settings):*
```python
url_to_scan = siemplify.extract_action_param(param_name="URL", is_mandatory=True)
manager.scan_url(url=url_to_scan)
```
*Expected Output:*
```json
{
  "entity_usage": {
    "reasoning": "The action receives an entity identifier via the 'URL' input parameter rather than iterating over platform target entities. The 'URL' parameter maps directly to the URL entity type (`DestinationURL`). No platform entity attributes or target entity collections are filtered.",
    "entity_types": {
      "url": true
    }
  }
}
```

#### Example 3: Unfiltered (Global) Scope Action
*Input Snippet (Python):*
```python
category = siemplify.extract_action_param(param_name="Category")
for entity in siemplify.target_entities:
    custom_list_manager.add_to_custom_list(
        category=category, entity_identifier=entity.identifier
    )
siemplify.end("Entities were added to custom list.", "true")
```
*Expected Output:*
```json
{
  "entity_usage": {
    "reasoning": "The script iterates over `siemplify.target_entities` without type filtering. Because no entity type filters are applied, the action applies globally to all supported entity types. No entity attribute filters are evaluated.",
    "entity_types": {
      "address": true,
      "alert": true,
      "application": true,
      "child_hash": true,
      "child_process": true,
      "cluster": true,
      "container": true,
      "credit_card": true,
      "cve": true,
      "cve_id": true,
      "database": true,
      "deployment": true,
      "destination_domain": true,
      "domain": true,
      "email_message": true,
      "event": true,
      "file_hash": true,
      "file_name": true,
      "generic": true,
      "host_name": true,
      "ip_set": true,
      "mac_address": true,
      "parent_hash": true,
      "parent_process": true,
      "phone_number": true,
      "pod": true,
      "process": true,
      "service": true,
      "source_domain": true,
      "threat_actor": true,
      "threat_campaign": true,
      "threat_signature": true,
      "url": true,
      "usb": true,
      "user": true
    }
  }
}
```

#### Example 4: Non-Entity Action & Alert Storage Vehicle Exception
*Input Snippet (Python):*
```python
file_content = siemplify.current_alert.entities[0].additional_properties.get("SourceFileContent")
manager.create_ticket(title="Security Alert", payload=file_content)
```
*Expected Output:*
```json
{
  "entity_usage": {
    "reasoning": "`siemplify.current_alert.entities[0]` is accessed strictly as a platform storage vehicle to read alert-level `SourceFileContent`, not for entity operations. No entities are processed or targeted. No entity filters are evaluated. All entity and filter flags are false.",
    "entity_types": {}
  }
}
```

---

**Current Task Input:**

— START OF FILE ${json_file_name} —
```
${json_file_content}
```
— END OF FILE ${json_file_name} —

— START OF FILE ${python_file_name} —
```python
${python_file_content}
```
— END OF FILE ${python_file_name} —

— START OF FILE ${manager_file_names} —
${manager_files_content}
— END OF FILE ${manager_file_names} —

**Final Instructions:**
Based strictly on the provided "Current Task Input" and guidelines:
1. Analyze script code, settings, and manager methods to determine entity interactions.
2. Formulate the step-by-step reasoning quoting exact code constructs and parameters.
3. Populate `entity_usage` with accurate entity types and filter boolean flags.
