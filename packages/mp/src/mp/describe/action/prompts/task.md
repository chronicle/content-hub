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

**Action Product Categories Definitions:**
Review these categories carefully. An action can belong to one or more categories if it matches the expected outcome.
- **Enrich IOC**: Returns reputation, prevalence, and threat intelligence for the indicator.
- **Enrich Asset**: Returns contextual metadata (e.g., OS version, owner, department, MAC address) for a user or resource.
- **Update Alert**: Changes the status, severity, or assignee of the alert within the SecOps platform.
- **Add Alert Comment**: Appends analyst notes or automated log entries to the alert's activity timeline.
- **Create Ticket**: Generates a new record in an external ITSM (e.g., Jira, ServiceNow) and returns the Ticket ID.
- **Update Ticket**: Synchronizes status, priority, or field changes from SecOps to the external ticketing system.
- **Add IOC To Blocklist**: Updates security controls (Firewall, EDR, Proxy) to prevent any future interaction with the IOC.
- **Remove IOC From Blocklist**: Restores connectivity or execution rights for an indicator by removing it from restricted lists.
- **Add IOC To Allowlist**: Marks an indicator as "known good" to prevent future security alerts or false positives.
- **Remove IOC From Allowlist**: Re-enables standard security monitoring and blocking for a previously trusted indicator.
- **Disable Identity**: Revokes active sessions and prevents a user or service account from authenticating to the network.
- **Enable Identity**: Restores authentication capabilities and system access for a previously disabled account.
- **Contain Host**: Isolates an endpoint from the network via EDR, allowing communication only with the management console.
- **Uncontain Host**: Removes network isolation and restores the endpoint's full communication capabilities.
- **Reset Identity Password**: Invalidates the current credentials and triggers a password change or temporary password generation.
- **Update Identity**: Modifies account metadata, such as group memberships, permissions, or contact information.
- **Search Events**: Returns a collection of historical logs or telemetry data matching specific search parameters.
- **Execute Command on the Host**: Runs a script or system command on a remote endpoint and returns the standard output (STDOUT).
- **Download File**: Retrieves a specific file from a remote host for local forensic analysis or sandboxing.
- **Send Email**: Dispatches an outbound email notification or response to specified recipients.
- **Search Email**: Identifies and lists emails across the mail server based on criteria like sender, subject, or attachment.
- **Delete Email**: Removes a specific email or thread from one or more user mailboxes (Purge/Withdraw).
- **Update Email**: Modifies the state of an email, such as moving it to quarantine, marking as read, or applying labels.
- **Submit File**: Uploads a file or sample to a sandbox or analysis engine (e.g., VirusTotal, Joe Sandbox) and returns a behavior report or threat score.
- **Send Message**: Sends a message to a communication app (e.g., Google Chat, Microsoft Teams).
- **Search Asset**: Searches for the asset associated with the alert within the product.
- **Get Alert Information**: Fetches information about the alert from the 3rd party product.

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
4. **Action Product Categories & Reasoning:** You MUST write out your step-by-step reasoning in the `reasoning` field of the `action_product_categories` object BEFORE populating the boolean flags. Discuss why the action matches or fails to match specific categories based on the expected outcomes defined above.

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
        "reasoning": "The code iterates over `siemplify.target_entities` and filters using `entity.entity_type == EntityTypes.ADDRESS and entity.is_internal`. This means it targets ADDRESS entities, filtering by entity_type and is_internal.",
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
    "categories": {
        "enrichment": true
    },
    "action_product_categories": {
        "reasoning": "The action fetches IP data from VirusTotal, returning threat intelligence and evaluating risk. This matches the 'Enrich IOC' expected outcome. It does not mutate data on external systems, so it is not a Contain Host or Blocklist action.",
        "add_alert_comment": false,
        "add_ioc_to_allowlist": false,
        "add_ioc_to_blocklist": false,
        "contain_host": false,
        "create_ticket": false,
        "delete_email": false,
        "disable_identity": false,
        "download_file": false,
        "enable_identity": false,
        "enrich_asset": false,
        "enrich_ioc": true,
        "execute_command_on_the_host": false,
        "get_alert_information": false,
        "remove_ioc_from_allowlist": false,
        "remove_ioc_from_blocklist": false,
        "reset_identity_password": false,
        "search_asset": false,
        "search_email": false,
        "search_events": false,
        "send_email": false,
        "send_message": false,
        "submit_file": false,
        "uncontain_host": false,
        "update_alert": false,
        "update_email": false,
        "update_identity": false,
        "update_ticket": false
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
        "reasoning": "The code processes `entities` looking for `e.entity_type == \"ADDRESS\"`, filtering strictly by entity_type.",
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
    "categories": {
        "enrichment": false
    },
    "action_product_categories": {
        "reasoning": "The action performs a POST to a firewall to block an IP address. This directly aligns with the 'Contain Host' expected outcome of isolating an endpoint, or 'Add IOC To Blocklist' depending on exact definition. Based on the JSON snippet, 'Contain Host' is true.",
        "add_alert_comment": false,
        "add_ioc_to_allowlist": false,
        "add_ioc_to_blocklist": false,
        "contain_host": true,
        "create_ticket": false,
        "delete_email": false,
        "disable_identity": false,
        "download_file": false,
        "enable_identity": false,
        "enrich_asset": false,
        "enrich_ioc": false,
        "execute_command_on_the_host": false,
        "get_alert_information": false,
        "remove_ioc_from_allowlist": false,
        "remove_ioc_from_blocklist": false,
        "reset_identity_password": false,
        "search_asset": false,
        "search_email": false,
        "search_events": false,
        "send_email": false,
        "send_message": false,
        "submit_file": false,
        "uncontain_host": false,
        "update_alert": false,
        "update_email": false,
        "update_identity": false,
        "update_ticket": false
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
    "ai_description": "Opens a new ticket in the ticket service by a post request.",
    "capabilities": {
        "reasoning": "The action makes a POST request to create a ticket (can_mutate_external_data=true). It does not fetch context data or update internal entities.",
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
    "categories": {
        "reasoning": "The action creates external data (a ticket) rather than retrieving data, so it cannot be an Enrichment action.",
        "enrichment": false
    },
    "action_product_categories": {
        "reasoning": "The action creates a new ticket in an external ticket service. This directly aligns with the 'Create Ticket' category.",
        "add_alert_comment": false,
        "add_ioc_to_allowlist": false,
        "add_ioc_to_blocklist": false,
        "contain_host": false,
        "create_ticket": true,
        "delete_email": false,
        "disable_identity": false,
        "download_file": false,
        "enable_identity": false,
        "enrich_asset": false,
        "enrich_ioc": false,
        "execute_command_on_the_host": false,
        "get_alert_information": false,
        "remove_ioc_from_allowlist": false,
        "remove_ioc_from_blocklist": false,
        "reset_identity_password": false,
        "search_asset": false,
        "search_email": false,
        "search_events": false,
        "send_email": false,
        "send_message": false,
        "submit_file": false,
        "uncontain_host": false,
        "update_alert": false,
        "update_email": false,
        "update_identity": false,
        "update_ticket": false
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

3. Ensure valid JSON syntax.
ttings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
 settings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
ttings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
 settings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
