**Input Data:**
I have provided the following files for a Google SecOps action:

1. `Script Code`: The Python logic.
2. `Script Settings`: The JSON metadata containing parameters and simulation data.

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
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/script-result-module

**Instructions:**

1. **Analyze the Description:** Synthesize the `Script Code` logic and`Script Settings` description.
    * *Style:* Active voice. Start with the action verb.
    *
   *Content:* Explain inputs, the external service interaction, key configuration parameters (like thresholds), and the resulting outputs (enrichment data, insights, etc.).
2. **Determine Capabilities:**
    * Check for `fetches_data`: Does it call an external API (GET)?
    * Check for
      `can_mutate_external_data`: Does it perform POST/PUT/DELETE actions that change the state of the external tool (e.g., block, quarantine)?
    * Check for SOAR interactions: Look for `add_entity_insight`, `add_data_table`,
      `update_entities`, `add_case_comment`.
3. **Extract Entity Scopes:** Look at the `Supported entities` in the JSON description or the
   `SimulationDataJson` to see if it targets `ADDRESS`, `FILEHASH`, `USER`, etc.

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
    "fields": {
        "description": "Enriches IP Address entities using VirusTotal. This action retrieves threat intelligence including ASN, country, and reputation scores. It evaluates risk based on thresholds, updates the entity's suspicious status, and generates an insight with the analysis results.",
        "fetches_data": true,
        "can_mutate_external_data": false,
        "external_data_mutation_explanation": "null",
        "can_mutate_internal_data": false,
        "internal_data_mutation_explanation": "null",
        "can_update_entities": true,
        "can_create_insight": true,
        "can_create_case_wall_logs": false,
        "can_create_case_comments": false
    },
    "entity_usage": {
        "run_on_entity_types": [
            "ADDRESS"
        ],
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
    },
    "tags": {
        "is_enrichment": true
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
    "fields": {
        "description": "Blocks a specific IP address on the target Firewall. This action initiates a state change on the external device to prevent network traffic to or from the specified entity.",
        "fetches_data": false,
        "can_mutate_external_data": true,
        "external_data_mutation_explanation": "Adds the IP address to the active blocklist configuration on the firewall.",
        "can_mutate_internal_data": false,
        "internal_data_mutation_explanation": "null",
        "can_update_entities": false,
        "can_create_insight": false,
        "can_create_case_wall_logs": false,
        "can_create_case_comments": false
    },
    "entity_usage": {
        "run_on_entity_types": [
            "ADDRESS"
        ],
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
    },
    "tags": {
        "is_enrichment": false
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
    "fields": {
        "description": "Opens a new ticket in the ticket service by a post request.",
        "fetches_data": false,
        "can_mutate_external_data": true,
        "external_data_mutation_explanation": "Creates a new ticket in the ticket service.",
        "can_mutate_internal_data": false,
        "internal_data_mutation_explanation": "null",
        "can_update_entities": false,
        "can_create_insight": false,
        "can_create_case_wall_logs": false,
        "can_create_case_comments": false
    },
    "entity_usage": {
        "run_on_entity_types": [],
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
    },
    "tags": {
        "is_enrichment": false
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
${manager_files_content}
— END OF FILE ${manager_file_names}—

**Final Instructions:**
Based strictly on the provided "Current Task Input" and the guidelines defined in the System Prompt:

1. Analyze the code flow and settings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
