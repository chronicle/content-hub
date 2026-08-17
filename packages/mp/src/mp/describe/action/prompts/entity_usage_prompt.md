**Input Data:**
I have provided the following files for a Google SecOps action:

1. `Script Code`: The Python logic.
2. `Script Settings`: The JSON metadata containing parameters and simulation data. Important: Integration-level parameters are provided within this JSON solely for background context.

**Reference Documentation:**

* **SOAR SDK:** https://github.com/chronicle/soar-sdk/tree/main/src/soar_sdk
* **TIPCommon:** https://github.com/chronicle/content-hub/tree/main/packages/tipcommon/TIPCommon
* **EnvironmentCommon**:
  https://github.com/chronicle/content-hub/tree/main/packages/envcommon/EnvironmentCommon
* **Case Manipulation**:
  https://docs.cloud.google.com/chronicle/docs/soar/reference/case-manipulation
* **TIPCommon**:
  https://docs.cloud.google.com/chronicle/docs/soar/marketplace-integrations/tipcommon
* **Integrations:** https://docs.cloud.google.com/chronicle/docs/soar/marketplace-integrations
* **SOAR SDK Docs:**
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/custom-lists
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/integration-configuration-script-parameters
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-action-module
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-connectors-module
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-data-model-module
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-job-module
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-module
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/script-result-module

**Instructions:**

1. **Extract Entity Scopes:** Analyze how the action uses target entities. You MUST write out your step-by-step reasoning in the `reasoning` field of the `entity_usage` object before setting boolean flags:
    * **Presence of Entities**: An action "runs on entities" if it satisfies at least one of the following criteria:
        - It iterates over or references `target_entities` within the Python script.
        - It accepts or processes entity identifiers via input parameters (e.g., $all_entity_param_examples).
          CRITICAL: If an action accepts an input parameter representing an entity, set the corresponding entity type flag to `true`.
        - It calls SOAR SDK helper methods that internally iterate over or mutate alert entities (e.g., `siemplify.add_alert_entities_to_custom_list()`, `siemplify.remove_alert_entities_from_custom_list()`, and `siemplify.any_alert_entities_in_custom_list()`).
        - It dynamically resolves entities across case alerts by accessing alert collections (e.g., `siemplify.case.alerts`) and extracting entity attributes (`alert.entities`), either directly or through integration core helper functions.
          CRITICAL: If `alert.entities[0]` (or `siemplify.current_alert.entities[0]`) is accessed solely as a platform storage vehicle to retrieve alert-level properties (e.g., `additional_properties["SourceFileContent"]`) without any subsequent entity filtering, enrichment, or iteration, do NOT classify the action as running on entities (set all entity type flags to `false`). However, if the action also iterates over, filters, or updates target entities, evaluate those entity operations independently.
    * **Specific Types & Parameter Mapping**: If an action restricts execution to specific entity types, set boolean flags to `true` exclusively for the targeted types based on code filters (e.g., `if entity.entity_type == EntityTypes.<ENTITY_TYPE_NAME>`) or entity input parameters:
$entity_type_mapping_rules
    * **Exclusion Logic vs. Type Filtering**: Negative conditional checks (e.g., `if entity.additional_properties.get("Type") != "<ENTITY_TYPE_NAME>"`) are exclusion filters used to omit specific entities (`<entity>: false`). They do NOT restrict scope to specific types. If an action processes `target_entities` using an exclusion filter, make sure the excluded entity type flag is set to `false`.
    * **Unfiltered (Global) Scope**: If an action processes entities globally without type-based filtering—either by iterating over `target_entities` (directly or via SDK helper methods) or by dynamically aggregating entities across case alerts (`siemplify.case.alerts` / `alert.entities`) - it runs on all supported entity types; set all flags to `true`.
    * **Generic Type**: `generic` (GenericEntity) is a standalone type. Do not use it as a fallback for "all types"; only set it to true if explicitly filtered for, or if all flags are true.
    * **Filter Properties**: Populate boolean flags for how target entities are filtered:
        * `filters_by_identifier`: Set to `true` ONLY if the code actively filters or matches platform `siemplify.target_entities` by identifier. Do NOT set to `true` if entity parameters are used solely for entity creation or case alert duplicate checks.
        * `filters_by_creation_time` / `filters_by_modification_time`: filters by timestamp.
        * `filters_by_additional_properties`: filters by entity's `additional_properties` dictionary.
        * `filters_by_case_identifier` / `filters_by_alert_identifier`: filters by parent case/alert ID.
        * `filters_by_entity_type` / `filters_by_is_internal` / `filters_by_is_suspicious` / `filters_by_is_artifact` / `filters_by_is_vulnerable` / `filters_by_is_enriched` / `filters_by_is_pivot`: filters by the corresponding attribute of the entity.
2. **Strict Classification**:
    * Only set boolean flags to `true` under `entity_usage` if supported by the script's actual execution model (either through explicit type filtering/mapping OR through unfiltered global/dynamic scope). Do not set flags to `true` based on potential capability, generic placeholder functions, or print logs.

**Golden Dataset (Few-Shot Examples):**

***Example 1: Enrichment Action***

*Input Snippet (Python):*

```python
suitable_entities = [
    entity
    for entity in siemplify.target_entities
    if entity.entity_type == EntityTypes.ADDRESS and entity.is_internal
]
for entity in suitable_entities:
    manager = VirusTotalManager(api_key=api_key)
    ip_data = manager.get_ip_data(ip=entity.identifier)
    if ip_data.threshold > 5:
        entity.is_suspicious = True
    siemplify.update_entities([entity])
    siemplify.add_entity_insight(entity, ip_data.to_insight())
```

*Input Snippet (JSON):*

```json
{
  "Description": "Enrich IP using VirusTotal.",
  "SimulationDataJson": "{\"Entities\": [\"ADDRESS\"]}"
}
```

*Expected Output:*

```json
{
  "entity_usage": {
    "reasoning": "The code iterates over `siemplify.target_entities` and filters using `entity.entity_type == EntityTypes.ADDRESS and entity.is_internal`. This means it targets ADDRESS entities, filtering by entity_type and is_internal.",
    "entity_types": {
      "address": true,
      "alert": false,
      "application": false,
      "child_hash": false,
      "child_process": false,
      "cluster": false,
      "container": false,
      "credit_card": false,
      "cve": false,
      "cve_id": false,
      "database": false,
      "deployment": false,
      "destination_domain": false,
      "domain": false,
      "email_message": false,
      "event": false,
      "file_hash": false,
      "file_name": false,
      "generic": false,
      "host_name": false,
      "ip_set": false,
      "mac_address": false,
      "parent_hash": false,
      "parent_process": false,
      "phone_number": false,
      "pod": false,
      "process": false,
      "service": false,
      "source_domain": false,
      "threat_actor": false,
      "threat_campaign": false,
      "threat_signature": false,
      "url": false,
      "usb": false,
      "user": false
    },
    "filters_by_identifier": false,
    "filters_by_creation_time": false,
    "filters_by_modification_time": false,
    "filters_by_additional_properties": false,
    "filters_by_case_identifier": false,
    "filters_by_alert_identifier": false,
    "filters_by_entity_type": true,
    "filters_by_is_internal": true,
    "filters_by_is_suspicious": false,
    "filters_by_is_artifact": false,
    "filters_by_is_vulnerable": false,
    "filters_by_is_enriched": false,
    "filters_by_is_pivot": false
  }
}
```

***Example 2: Containment Action***

*Input Snippet (Python):*

```python
entity = next((e for e in entities if e.entity_type == "ADDRESS"), None)
if entity is None:
    raise ValueError

firewall = FirewallManager(api_key=api_key)
# this performs a POST to the firewall to add the IP to a blocklist
result = firewall.block_ip(ip=entity.identifier, reason="SOAR Automated Block")
if result['success']:
    siemplify.result.add_result_json(result)
```

*Input Snippet (JSON):*

```json
{
  "Description": "Blocks an IP address on the perimeter firewall.",
  "SimulationDataJson": "{\"Entities\": [\"ADDRESS\"]}"
}
```

*Expected Output:*

```json
{
  "entity_usage": {
    "reasoning": "The code processes `entities` looking for `e.entity_type == \"ADDRESS\"`, filtering strictly by entity_type.",
    "entity_types": {
      "address": true,
      "alert": false,
      "application": false,
      "child_hash": false,
      "child_process": false,
      "cluster": false,
      "container": false,
      "credit_card": false,
      "cve": false,
      "cve_id": false,
      "database": false,
      "deployment": false,
      "destination_domain": false,
      "domain": false,
      "email_message": false,
      "event": false,
      "file_hash": false,
      "file_name": false,
      "generic": false,
      "host_name": false,
      "ip_set": false,
      "mac_address": false,
      "parent_hash": false,
      "parent_process": false,
      "phone_number": false,
      "pod": false,
      "process": false,
      "service": false,
      "source_domain": false,
      "threat_actor": false,
      "threat_campaign": false,
      "threat_signature": false,
      "url": false,
      "usb": false,
      "user": false
    },
    "filters_by_identifier": false,
    "filters_by_creation_time": false,
    "filters_by_modification_time": false,
    "filters_by_additional_properties": false,
    "filters_by_case_identifier": false,
    "filters_by_alert_identifier": false,
    "filters_by_entity_type": true,
    "filters_by_is_internal": false,
    "filters_by_is_suspicious": false,
    "filters_by_is_artifact": false,
    "filters_by_is_vulnerable": false,
    "filters_by_is_enriched": false,
    "filters_by_is_pivot": false
  }
}
```

***Example 3: Action that uses no entities***

*Input Snippet (Python):*

```python
ticket_manager = TicketMAnager(api_key=api_key)
# this performs a POST to the ticket service to open a new ticket
results = ticket_manager.create_ticket(title, description)
```

*Input Snippet (JSON):*

```json
{
  "Description": "Opens a new ticket in the ticket service.",
  "SimulationDataJson": "{\"Entities\": []}"
}
```

*Expected Output:*

```json
{
  "entity_usage": {
    "reasoning": "The action works on other data sources without referencing specific entities, so all flags must be false.",
    "entity_types": {
      "address": false,
      "alert": false,
      "application": false,
      "child_hash": false,
      "child_process": false,
      "cluster": false,
      "container": false,
      "credit_card": false,
      "cve": false,
      "cve_id": false,
      "database": false,
      "deployment": false,
      "destination_domain": false,
      "domain": false,
      "email_message": false,
      "event": false,
      "file_hash": false,
      "file_name": false,
      "generic": false,
      "host_name": false,
      "ip_set": false,
      "mac_address": false,
      "parent_hash": false,
      "parent_process": false,
      "phone_number": false,
      "pod": false,
      "process": false,
      "service": false,
      "source_domain": false,
      "threat_actor": false,
      "threat_campaign": false,
      "threat_signature": false,
      "url": false,
      "usb": false,
      "user": false
    },
    "filters_by_identifier": false,
    "filters_by_creation_time": false,
    "filters_by_modification_time": false,
    "filters_by_additional_properties": false,
    "filters_by_case_identifier": false,
    "filters_by_alert_identifier": false,
    "filters_by_entity_type": false,
    "filters_by_is_internal": false,
    "filters_by_is_suspicious": false,
    "filters_by_is_artifact": false,
    "filters_by_is_vulnerable": false,
    "filters_by_is_enriched": false,
    "filters_by_is_pivot": false
  }
}
```

***Example 4: Unfiltered (Global) Scope Action***

*Input Snippet (Python):*

```python
category = siemplify.parameters["Category"]
for entity in siemplify.target_entities:
    custom_list_manager.add_to_custom_list(
        category=category, entity_identifier=entity.identifier
    )
siemplify.end("Entities were added to custom list.", "true")
```

*Input Snippet (JSON):*

```json
{
  "Description": "Adds all target entities of the alert to a specified custom list category.",
  "SimulationDataJson": "{\"Entities\": [\"ADDRESS\", \"USERUNIQNAME\", \"DOMAIN\"]}"
}
```

*Expected Output:*

```json
{
  "entity_usage": {
    "reasoning": "The script iterates over `siemplify.target_entities` and adds each entity to the custom list category without filtering by entity type. Because it applies globally to all target entities attached to the alert, all supported entity type flags are set to true.",
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
    },
    "filters_by_identifier": false,
    "filters_by_creation_time": false,
    "filters_by_modification_time": false,
    "filters_by_additional_properties": false,
    "filters_by_case_identifier": false,
    "filters_by_alert_identifier": false,
    "filters_by_entity_type": false,
    "filters_by_is_internal": false,
    "filters_by_is_suspicious": false,
    "filters_by_is_artifact": false,
    "filters_by_is_vulnerable": false,
    "filters_by_is_enriched": false,
    "filters_by_is_pivot": false
  }
}
```

***

**Current Task Input:**

— START OF FILE ${json_file_name}—

```
${json_file_content}
```

— END OF FILE ${json_file_name}—

— START OF FILE ${python_file_name}—

```python
${python_file_content}
```

— END OF FILE ${python_file_name}—

— START OF FILE ${manager_file_names}—
${manager_files_content} — END OF FILE ${manager_file_names}—

**Final Instructions:**
Based strictly on the provided "Current Task Input" and the guidelines defined in the System Prompt:

1. Analyze the code flow and settings for entity usage.
2. Construct the Entity Usage JSON (`entity_usage`).
3. Ensure valid JSON syntax.
