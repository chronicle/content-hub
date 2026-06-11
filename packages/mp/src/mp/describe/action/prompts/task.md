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

**Outcome Categories Definitions:**
Review these categories carefully. An action can belong to one or more categories if it matches the expected outcome.

- **Enrich IOC (hash, filename, IP, domain, URL, CVE, Threat Actor, Campaign)**: Returns reputation, prevalence, and threat intelligence (e.g., malware family, attribution) for the indicator.
- **Enrich Asset (hostname, user or internal resource)**: Returns contextual metadata (e.g., OS version, owner, department, MAC address) for a user or resource.
- **Update Alert**: Changes the status, severity, or assignee of the alert within the SecOps platform.
- **Add Alert Comment**: Appends analyst notes or automated log entries to the alert's activity timeline.
- **Create Ticket**: Generates a new record in an external ITSM (e.g., Jira, ServiceNow) and returns the Ticket ID.
- **Update Ticket**: Synchronizes status, priority, or field changes from SecOps to the external ticketing system.
- **Add IOC To Blocklist**: Updates security controls (Firewall, EDR, Proxy) to prevent any future interaction with the IOC.
- **Remove IOC From Blocklist**: Restores connectivity or execution rights for an indicator by removing it from restricted lists.
- **Add IOC To Allowlist**: Marks an indicator as "known good" to prevent future security alerts or false positives.
- **Remove IOC From Allowlist**: Re-enables standard security monitoring and blocking for a previously trusted indicator.
- **Disable Identity (User, Account)**: Revokes active sessions and prevents a user or service account from authenticating to the network.
- **Enable Identity (User, Account)**: Restores authentication capabilities and system access for a previously disabled account.
- **Contain Host**: Isolates an endpoint from the network via EDR, allowing communication only with the management console.
- **Uncontain Host**: Removes network isolation and restores the endpoint's full communication capabilities.
- **Reset Identity Password (User, Account)**: Invalidates the current credentials and triggers a password change or temporary password generation.
- **Update Identity (User, Account)**: Modifies account metadata, such as group memberships, permissions, or contact information.
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

1. **Analyze the Description:** Synthesize the `Script Code` logic and `Script Settings` description.
    * *Style:* Active voice. Start with the action verb.
    * *Content:* Explain inputs, the external service interaction, key configuration parameters (like thresholds), and the resulting outputs (enrichment data, insights, etc.).
    * Produce three distinct fields: `ai_description` (detailed, divided into 'General Description', 'Flow Description', and 'Additional Notes'), `ai_short_description` (concise summary), and `parameters_description` (markdown table).
2. **Determine Capabilities:** Analyze the code and metadata to evaluate SOAR/system operations. You MUST provide step-by-step reasoning in the `reasoning` field of the `capabilities` object before setting boolean flags:
    * `fetches_data`: Set to true if the action requests/retrieves additional contextual data from an external tool or source (usually via HTTP GET).
    * `can_mutate_external_data`: Set to true if the action performs state-changing operations (POST/PUT/DELETE) on external systems (e.g., blocking an IP, disabling a user, creating a ticket).
    * `external_data_mutation_explanation`: If `can_mutate_external_data` is true, provide a brief explanation of how/why the data changes. Otherwise, set to `null`.
    * `can_mutate_internal_data`: Set to true if the action mutates internal data inside Google SecOps.
    * `internal_data_mutation_explanation`: If `can_mutate_internal_data` is true, provide a brief explanation. Otherwise, set to `null`.
    * `can_update_entities`: Set to true if the action updates/saves changes to entities (e.g., calling `siemplify.update_entities` or `update_entities`).
    * `can_create_insight`: Set to true if the action generates/attaches insights (e.g., calling `siemplify.add_entity_insight` or `create_insight`).
    * `can_modify_alert_data`: Set to true if the action modifies the alert metadata/data inside the platform.
    * `can_create_case_comments`: Set to true if the action creates new analyst/case comments (e.g., calling `siemplify.add_case_comment`).
3. **Extract Entity Scopes:** Analyze how the action uses target entities. You MUST write out your step-by-step reasoning in the `reasoning` field of the `entity_usage` object before setting boolean flags:
    * **Presence of Entities**: An action "runs on entities" if it iterates over `target_entities` or uses entity-specific identifiers. If it works only on static/general data sources without referencing specific entities, all entity type flags must be false.
    * **Specific Types**: If the code filters entities by type (e.g., `if entity.entity_type == EntityTypes.ADDRESS`), set only that specific type flag (e.g., `address`) to true.
    * **Unfiltered (Global) Scope**: If it processes the `target_entities` list without type-based filtering, it runs on all supported entity types; set all flags to true.
    * **Generic Type**: `generic` (GenericEntity) is a standalone type. Do not use it as a fallback for "all types"; only set it to true if explicitly filtered for, or if all flags are true.
    * **Filter Properties**: Populate boolean flags for how target entities are filtered:
      * `filters_by_identifier`: filters by entity identifier or original identifier.
      * `filters_by_creation_time` / `filters_by_modification_time`: filters by timestamp.
      * `filters_by_additional_properties`: filters by entity's `additional_properties` dictionary.
      * `filters_by_case_identifier` / `filters_by_alert_identifier`: filters by parent case/alert ID.
      * `filters_by_entity_type` / `filters_by_is_internal` / `filters_by_is_suspicious` / `filters_by_is_artifact` / `filters_by_is_vulnerable` / `filters_by_is_enriched` / `filters_by_is_pivot`: filters by the corresponding attribute of the entity.
4. **Outcome Categories & Reasoning:** You MUST write out your step-by-step reasoning in the `reasoning` field of the `outcome_categories` object BEFORE populating the boolean flags. Discuss why the action matches or fails to match specific categories based on the expected outcomes defined above.
5. **Strict Classification**: Only set a boolean flag to `true` under `capabilities` or `outcome_categories` if the script code explicitly and functionally implements that capability/action. Do not set flags to `true` based on potential capability, generic placeholder functions, or print logs.

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
  "ai_description": "Enriches IP Address entities using VirusTotal. This action retrieves threat intelligence including ASN, country, and reputation scores. It evaluates risk based on thresholds, updates the entity's suspicious status, and generates an insight with the analysis results.",
  "ai_short_description": "Enriches IP Address entities using VirusTotal.",
  "parameters_description": "| Parameter | Type | Mandatory | Description |\n| --- | --- | --- | --- |\n| api_key | String | Yes | VirusTotal API Key |",
  "capabilities": {
    "reasoning": "The action makes a GET request to VirusTotal API to fetch IP data. It does not mutate external data but updates internal entities and creates insights.",
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
  },
  "outcome_categories": {
    "reasoning": "The action fetches IP data from VirusTotal, returning threat intelligence and evaluating risk. This matches the 'Enrich IOC' expected outcome. It does not mutate data on external systems, so it is not a Contain Host or Blocklist action.",
    "enrich_ioc": true,
    "enrich_asset": false,
    "update_alert": false,
    "add_alert_comment": false,
    "create_ticket": false,
    "update_ticket": false,
    "add_ioc_to_blocklist": false,
    "remove_ioc_from_blocklist": false,
    "add_ioc_to_allowlist": false,
    "remove_ioc_from_allowlist": false,
    "disable_identity": false,
    "enable_identity": false,
    "contain_host": false,
    "uncontain_host": false,
    "reset_identity_password": false,
    "update_identity": false,
    "search_events": false,
    "execute_command_on_the_host": false,
    "download_file": false,
    "send_email": false,
    "search_email": false,
    "delete_email": false,
    "update_email": false,
    "submit_file": false,
    "send_message": false,
    "search_asset": false,
    "get_alert_information": false
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
  "ai_description": "Blocks a specific IP address on the target Firewall. This action initiates a state change on the external device to prevent network traffic to or from the specified entity.",
  "ai_short_description": "Blocks a specific IP address on the target Firewall.",
  "parameters_description": "| Parameter | Type | Mandatory | Description |\n| --- | --- | --- | --- |\n| api_key | String | Yes | API Key for Firewall |",
  "capabilities": {
    "reasoning": "The action performs a POST to a firewall to block an IP address. This directly aligns with the 'Block IP' expected outcome of isolating an endpoint.",
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
  },
  "outcome_categories": {
    "reasoning": "The action performs a POST to a firewall to block an IP address. This directly aligns with the 'Add IOC To Blocklist' expected outcome.",
    "enrich_ioc": false,
    "enrich_asset": false,
    "update_alert": false,
    "add_alert_comment": false,
    "create_ticket": false,
    "update_ticket": false,
    "add_ioc_to_blocklist": true,
    "remove_ioc_from_blocklist": false,
    "add_ioc_to_allowlist": false,
    "remove_ioc_from_allowlist": false,
    "disable_identity": false,
    "enable_identity": false,
    "contain_host": false,
    "uncontain_host": false,
    "reset_identity_password": false,
    "update_identity": false,
    "search_events": false,
    "execute_command_on_the_host": false,
    "download_file": false,
    "send_email": false,
    "search_email": false,
    "delete_email": false,
    "update_email": false,
    "submit_file": false,
    "send_message": false,
    "search_asset": false,
    "get_alert_information": false
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
  "ai_short_description": "Opens a new ticket in the ticket service.",
  "parameters_description": "| Parameter | Type | Mandatory | Description |\n| --- | --- | --- | --- |\n| title | String | Yes | Ticket Title |\n| description | String | Yes | Ticket Description |",
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
  },
  "outcome_categories": {
    "reasoning": "The action creates a new ticket in an external ticket service. This directly aligns with the 'Create Ticket' category.",
    "enrich_ioc": false,
    "enrich_asset": false,
    "update_alert": false,
    "add_alert_comment": false,
    "create_ticket": true,
    "update_ticket": false,
    "add_ioc_to_blocklist": false,
    "remove_ioc_from_blocklist": false,
    "add_ioc_to_allowlist": false,
    "remove_ioc_from_allowlist": false,
    "disable_identity": false,
    "enable_identity": false,
    "contain_host": false,
    "uncontain_host": false,
    "reset_identity_password": false,
    "update_identity": false,
    "search_events": false,
    "execute_command_on_the_host": false,
    "download_file": false,
    "send_email": false,
    "search_email": false,
    "delete_email": false,
    "update_email": false,
    "submit_file": false,
    "send_message": false,
    "search_asset": false,
    "get_alert_information": false
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

1. Analyze the code flow and settings.
2. Construct the Capability Summary JSON.
3. Ensure valid JSON syntax.
