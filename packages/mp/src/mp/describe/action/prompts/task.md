**Input Data:**
I have provided the following files for a Google SecOps action:

1. `Script Code`: The Python logic.
2.

`Script Settings`: The JSON metadata containing parameters and simulation data. Important: Integration-level parameters are provided within this JSON solely for background context. You are strictly prohibited from extracting or documenting any integration-level parameters in the ParametersDescription field.

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
    * *Content:* Explain inputs, the external service interaction, and the resulting outputs (enrichment data, insights, etc.).
    * Produce three distinct fields:
        * `ai_description` (detailed, divided into 'General Description', 'Flow Description', and 'Additional Notes').
        * `ai_short_description` (concise summary).
        *
        `parameters_description` (markdown table showing action-specific parameters. If the action has no parameters, set this field to exactly: "There are no parameters for this action". Do NOT document integration-level/configuration parameters here, including parameters retrieved via `siemplify.extract_configuration_param` in code or found under integration configurations).
2. **Evaluate Risk & Asset Criticality:** Analyze the action logic, execution mode, and its expected response payload against the following operational parameters to determine the fields under `impact_analysis_actions_metadata`:

    * `reversibility_risk_score`: Assign a score of Low, Medium, or High assessing how easily a human operator can undo the action if the agent makes a mistake.
    * `reversibility_risk_reasoning`: Provide step-by-step reasoning assessing how easily the **exact previous state** can be restored.
        - **Low Risk (Symmetrically Reversible)**: Pure read-only operations, mutative actions that have a direct, single-step symmetrical inverse, OR creating empty entities/objects that can be simply deleted with no operational data loss. For **State Flags** (e.g., Force Password Reset, Unlock), focus on the immediate action to clear/reset the flag, ignoring downstream user actions. **Functional Equivalents** count (e.g., if there is no direct "Lock" command, Disabling is a valid functional equivalent for reversing an Unlock).
          * *Examples*: Disabling a user account (can be re-enabled), adding a user to a group (can be removed), creating a ticket/issue (can be closed/deleted), forcing password reset (flag can be cleared), or adding an IP to a block list (can be unblocked).
        - **Medium Risk (Manual/Asymmetric Effort)**: Actions that can be undone, but require non-trivial manual effort, administrative coordination, or restoring configurations from secondary backups. If reversing the action requires **referencing/knowing external state that was not recorded by the action itself** (e.g., knowing which OU a user belonged to before moving them), it is Medium.
          * *Examples*: Executing a VM patch job, rolling back custom detection rule changes, modifying cloud instance network interfaces, or moving an entity to a new container without logging the previous one.

        - **High Risk (Irreversible/Permanent Loss)**: Actions where the exact previous state is permanently destroyed or cannot be recalled.
          * *Examples*: Hard-deleting cloud IAM roles or infrastructure, permanently purging emails/files bypassing trash/retention, overwriting passwords (where the original secure string is lost), or detonating sensitive files in public third-party sandboxes.


    * `scope_risk_score`: Assign a score of Low, Medium, or High evaluating the breadth of the action's potential impact on the organization's infrastructure or information exposure.
    * `scope_risk_reasoning`: Provide step-by-step reasoning evaluating the breadth of the action's potential impact.
        - For **Mutative Actions**: Focus on the **Direct Footprint** (what the action itself modifies directly) rather than hypothetical downstream consequences (e.g., adding a user to a group is Low if it only modifies that one user's record, even if that group has broad permissions).
        - For **Read-Only Actions**: Assess **Information Exposure**. Single-entity lookups (e.g., one user, one file) are Low. Multi-entity retrievals or Arbitrary Queries are **Medium ONLY if they expose sensitive Identity/Access Configurations (Topology)** (like group members, privilege trees, or ACL bindings). Enumerating basic **Entity Inventory** (e.g., listing all users, listing all groups simply as objects without their bindings/members) is Low as it exposes what exists, not how it is secured.
        - **Low Risk (Single Entity / Read-Only Bounded / Target)**: Single-entity reads, reading non-sensitive telemetry/logs, basic inventory enumeration, OR actions that affect exactly ONE isolated user account, computer account, mailbox, case, or individual file. Also includes creating empty, unlinked containers or groups that do not inherently grant permissions or affect traffic.
          * *Examples*: Searching for a specific user, downloading a single email attachment, resetting a user's session, getting host details, listing all available policies/groups, setting group membership for a single user, or disabling a single computer account.
        - **Medium Risk (Whole Host Containment / Bounded Group / Multi-Entity Sensitive Read)**: Actions that perform **network containment/isolation or power state changes on a single host** (due to high operational impact), OR reading memberships of bounded groups/directories (exposing identities/ACL bindings), OR actions that impact **multiple** endpoints/computers simultaneously, OR modifying configurations of bounded department security groups/channels.
          * *Examples*: Isolating/Containing an endpoint on the network, stopping a VM instance, fetching members of a group, hiding a host from EDR, or changing permissions on a shared drive.
        - **High Risk (Control Plane / Global Posture)**: Modifies foundational control-plane configurations, organization-wide transport/mail routing rules, global identity boundaries, or fleet-wide sensor blocklists capable of widespread disruption. If an action can attach broad policies to broad roles/groups, it should be considered High.
          * *Examples*: Modifying domain DNS, pushing global firewall rules across all fabrics, attaching organization-wide SCPs/IAM policies, or globally altering mail routing rules.

    * `friction_risk_score`: Assign a score of Low, Medium, or High evaluating the extent to which an accidental execution stops people from doing their jobs or disrupts security operations.
    * `friction_risk_reasoning`: Provide step-by-step reasoning evaluating disruption to standard employee productivity AND Security Operations Center (SOC) workflows.
        - **Capability Principle**: For generic actions (e.g., "Update Attributes"), consider the **Capability** of the action to touch critical metadata. If the action can mutate arbitrary fields **that govern Authentication, Logon, or Network Access**, rate it assuming it can touch critical ones (Medium/High). If it only touches descriptive metadata (like comments), it is Low.
        - **Low Risk (Zero/Silent Disruption)**: Read-only operations, background data enrichment, or non-intrusive metadata updates (on specific, non-critical fields). **Removing a block or detection (degrading posture)** is also Low Friction *if* it does not interrupt business workflows (it may leave a security gap, but work continues).
          * *Examples*: Querying logs, adding an internal case comment, tagging an entity, or retrieving threat intel.


        - **Medium Risk (Workflow Obstruction / SOC Disruption)**: Non-lockout disruption to user correspondence, OR disruption to SOC investigation queues.
          * *Examples*: Moving an email to Junk/Trash, quarantining a file, or updating an incident/alert state (causing analysts to lose queue context).
        - **High Risk (Hard Lockout / Business Freeze)**: Complete loss of employee productivity, account lockouts, or blocking business-critical communications.
          * *Examples*: Disabling a user account completely, isolating an executive/critical host from the network, or blocking an active corporate domain.

    * `volume_risk_score`: Assign a score of Low, Medium, or High evaluating the physical scale of the deployment or execution.
    * `volume_risk_reasoning`: Provide step-by-step reasoning evaluating the scale of the deployment. Consider both **Input Cardinality** (how many targets are explicitly called) and **Output Cardinality** (how many records/entities are returned or processed in a batch).
        - **Low Risk (Single Target / Individual Query / Bounded Set)**: Actions executed against exactly ONE explicit target per invocation (single IP, single user, single host, single URL), OR iterating over a **small, bounded set of artifacts** directly linked to the current event (typically a handful of IPs/users). **Simple enumeration of the Directory Inventory** (listing available objects up to a standard page limit) is also Low volume as it is a bounded read query with no change impact.
          * *Examples*: Querying VirusTotal for a single IP/URL, disabling one user, listing available groups, or looping over the 3 external IPs found in the current alert. *(Crucial: Do NOT promote single-entity actions or inventory reads to Medium just because they query a cloud API).*
        - **Medium Risk (Batch / Broad Iterators / Subnet Scans)**: Actions designed to iterate across **large collections** of entities, fetch batches/lists of 50+ records up to a limit (even if the input query is a single group/table name), or scan an internal subnet range.
          * *Examples*: Fetching a batch of all directory users, retrieving members of a large group (batch return), scanning a /24 subnet, or listing events across an entire endpoint for the last 24 hours.
        - **High Risk (Fleet-Wide / Global Broadcast / Fabric Commits)**: Orchestrated broadcast execution across the entire enterprise fleet, global configuration commits, or bulk operations across all mailboxes. This applies to **Broadcast Effects** (e.g., deploying a policy/rule that applies to all endpoints/mailboxes automatically). Standard central directory mutations (e.g., adding a user to a group) are NOT High Volume unless they explicitly trigger a fleet-wide push.
          * *Examples*: Committing policy changes across an entire firewall fabric, uploading IOCs to a fleet-wide EDR blocklist, or applying a retention policy across all enterprise mailboxes.

    * `asset_criticality_relevance`: A Boolean indicator (`true` or `false`) stating whether the action's response payload yields data, metadata, or threat intelligence that helps classify an entity's risk, privilege level, or environmental criticality.
        - **Set to `true` ONLY if**: The action is a **strictly read-only / enrichment function** AND its response returns:
          1. **Structural Privileges / Boundaries**: Directory roles, administrative group memberships, IAM policies, or container hierarchy (e.g., AD Group Members, AWS IAM Policies, Azure AD Roles).
          2. **External Threat Intelligence / Reputation**: External risk scores, malware reports, threat actor links, or file hash analysis (e.g., VirusTotal scans, GTI IOC searches, Mandiant Threat Intel).
          3. **Security Finding / Detection Details**: Native alert metadata, finding severity, or EDR incident reports (e.g., Security Command Center findings, Cortex XDR incident details, Defender alerts).
          4. **Organizational Topology / Placement**: Directory paths, organizational units (OUs), or permission attachment counts that indicate where an asset sits in the hierarchy or how broadly a permission applies.
          5. **Basic Identity / Asset Inventory**: Enumeration of users, hosts, or accounts in a directory. Knowing the existence, types, and age of assets is foundational to criticality.

        - **Set to `false` if**:
          1. **Mutative Actions**: Any action that creates, updates, deletes, or modifies state is AUTOMATICALLY `false` (even if it returns threat intel or ticket IDs).
          2. **Generic Health / Simple Booleans**: Read-only actions that only return agent operational health, machine patch recommendations, ping status, or raw boolean checks of generic properties (e.g., "Is Online"). **Boolean checks of Group Membership in a directory** (e.g., "Is User in Group") are generally `false` UNLESS the action specifically and explicitly checks for a known high-privilege tier (e.g., "Is Domain Admin"), in which case it is `true`.



    * `asset_criticality_relevance_reasoning`: Provide a step-by-step rationale evaluating whether the response payload provides useful asset criticality/severity signals following this checklist:
        1. **Operation Type Check**: Is this a strictly read-only discovery/enrichment action? (If mutative -> immediately False).
        2. **Classification Signals**: Does the payload return administrative privilege blocks, external threat intelligence reputation, or security incident/finding severity?
        3. **Downstream Utility**: How does downstream logic utilize these specific signals to calculate the target's trust score, privilege tier, or environmental criticality?

    * `asset_criticality_categories`: When asset_criticality_relevance is enabled, map the operation to any of the following five classification buckets based on the returned metadata and environmental context. Multiple categories may be assigned for multi-faceted payloads. If relevance is false, return an empty array `[]`.
        - `"Enrichment: Asset Risk & Reputation"`: Retrieval of threat intelligence, historical reputation data, or risk scores for non-human indicators (e.g., File Hash, IP, Domain).
        - `"Enrichment: Identity & Organizational Context"`: Discovery of administrative privileges, directory roles, or business hierarchy (e.g., Executive status, Domain Admin rights). Targets: USER, EMAILADDRESS.
        - `"Enrichment: Organizational Network Context"`: Analysis of IAM policies, cloud-native permissions, and broad security configurations. Targets: USER, HOSTNAME.
        - `"Enrichment: Endpoint Telemetry & Vulnerability"`: Querying internal host states, process logs, OS versions, and patch levels. Targets: HOSTNAME, MACADDRESS.
        - `"Enrichment: External Network Routing"`: Collection of WHOIS records, DNS resolution, and global routing attributes. Targets: IP ADDRESS.

    * `asset_criticality_categories_reasoning`: Provide a concise, single-sentence rationale justifying the selected categories based on the function logic and expected response data. State "Not applicable as relevance is false" if relevance is disabled.
3. **Determine Capabilities:** Analyze the code and metadata to evaluate SOAR/system operations. You MUST provide step-by-step reasoning in the `reasoning` field of the
   `capabilities` object before setting boolean flags:
    * `fetches_data`: Set to true if the action requests/retrieves additional contextual data from an external tool or source (usually via HTTP GET).
    * `can_mutate_external_data`: Set to true if the action performs state-changing operations (POST/PUT/DELETE) on external systems (e.g., blocking an IP, disabling a user, creating a ticket).
    * `external_data_mutation_explanation`: If `can_mutate_external_data` is true, provide a brief explanation of how/why the data changes. Otherwise, set to `null`.
    * `can_mutate_internal_data`: Set to true if the action mutates internal data inside Google SecOps.
    * `internal_data_mutation_explanation`: If `can_mutate_internal_data` is true, provide a brief explanation. Otherwise, set to `null`.
    * `can_update_entities`: Set to true if the action updates/saves changes to entities (e.g., calling `siemplify.update_entities` or `update_entities`).
    * `can_create_insight`: Set to true if the action generates/attaches insights (e.g., calling `siemplify.add_entity_insight` or `create_insight`).
    * `can_modify_alert_data`: Set to true if the action modifies the alert metadata/data inside the platform.
    * `can_create_case_comments`: Set to true if the action creates new analyst/case comments (e.g., calling `siemplify.add_case_comment`).
4. **Extract Entity Scopes:** Analyze how the action uses target entities. You MUST write out your step-by-step reasoning in the `reasoning` field of the
   `entity_usage` object before setting boolean flags:
    * **Presence of Entities**: An action "runs on entities" if it iterates over
      `target_entities` or uses entity-specific identifiers. If it works only on static/general data sources without referencing specific entities, all entity type flags must be false.
    * **Specific Types**: If the code filters entities by type (e.g., `if entity.entity_type == EntityTypes.ADDRESS`), set only that specific type flag (e.g., `address`) to true.
    * **Unfiltered (Global) Scope**: If it processes the `target_entities` list without type-based filtering, it runs on all supported entity types; set all flags to true.
    * **Generic Type**: `generic` (GenericEntity) is a standalone type. Do not use it as a fallback for "all types"; only set it to true if explicitly filtered for, or if all flags are true.
    * **Filter Properties**: Populate boolean flags for how target entities are filtered:
        * `filters_by_identifier`: filters by entity identifier or original identifier.
        * `filters_by_creation_time` / `filters_by_modification_time`: filters by timestamp.
        * `filters_by_additional_properties`: filters by entity's `additional_properties` dictionary.
        * `filters_by_case_identifier` / `filters_by_alert_identifier`: filters by parent case/alert ID.
        * `filters_by_entity_type` / `filters_by_is_internal` / `filters_by_is_suspicious` / `filters_by_is_artifact` / `filters_by_is_vulnerable` / `filters_by_is_enriched` /
          `filters_by_is_pivot`: filters by the corresponding attribute of the entity.
5. **Outcome Categories & Reasoning:** You MUST write out your step-by-step reasoning in the `reasoning` field of the
   `outcome_categories` object BEFORE populating the boolean flags. Discuss why the action matches or fails to match specific categories based on the expected outcomes defined above.
6. **Strict Classification**: Only set a boolean flag to `true` under `capabilities` or
   `outcome_categories` if the script code explicitly and functionally implements that capability/action. Do not set flags to
   `true` based on potential capability, generic placeholder functions, or print logs.

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
  "impact_analysis_actions_metadata": {
    "volume_risk_reasoning": "Lookups are executed for localized IP entities within the alert.",
    "scope_risk_reasoning": "The query is limited to fetching threat reputation data for individual IP addresses.",
    "friction_risk_reasoning": "Background log analysis and reputation lookup create zero disruption to active employee workflows.",
    "reversibility_risk_reasoning": "The action performs read-only threat intelligence queries to VirusTotal, making execution fully reversible.",
    "asset_criticality_relevance": true,
    "asset_criticality_relevance_reasoning": "1. Operation Type Check: Read-only enrichment lookup (VirusTotal scan). 2. Asset or Group Identifier Presence: Returns IP address reputation metadata. 3. Discovery of Pre-existing Metadata/Scope Signals: Contains ASN, country, and threat score signals. 4. Downstream Utility: Threat scores and reputation help classify whether the IP belongs to a critical asset.",
    "volume_risk_score": "Low",
    "scope_risk_score": "Low",
    "friction_risk_score": "Low",
    "reversibility_risk_score": "Low",
    "asset_criticality_categories": [
      "Enrichment: Asset Risk & Reputation"
    ],
    "asset_criticality_categories_reasoning": "VirusTotal IP enrichment retrieves threat intelligence, reputation data, and risk scores for non-human IP indicators."
  },
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
  "impact_analysis_actions_metadata": {
    "volume_risk_reasoning": "Executed for a single target IP address.",
    "scope_risk_reasoning": "Modifies perimeter access control rules affecting corporate infrastructure.",
    "friction_risk_reasoning": "Blocking network traffic halts active user/employee connectivity if triggered on a false positive.",
    "reversibility_risk_reasoning": "Firewall block rules can be manually undone by removing the rule.",
    "asset_criticality_relevance": false,
    "asset_criticality_relevance_reasoning": "1. Operation Type Check: Mutative/operational action (POST to block IP on firewall). Fails rule: mutative actions do not qualify for asset criticality calculation. 2. Asset Identifier Presence: Operates on IP. 3. Discovery of Pre-existing Metadata/Scope Signals: Returns execution confirmation log. 4. Downstream Utility: Mutative action does not discover native pre-existing asset classification signals.",
    "volume_risk_score": "Low",
    "scope_risk_score": "High",
    "friction_risk_score": "High",
    "reversibility_risk_score": "Medium",
    "asset_criticality_categories": [],
    "asset_criticality_categories_reasoning": "Not applicable as relevance is false."
  },
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
  "impact_analysis_actions_metadata": {
    "volume_risk_reasoning": "Single ticket creation.",
    "scope_risk_reasoning": "Operation affects only a single ticket.",
    "friction_risk_reasoning": "Creating a ticket does not halt employee productivity.",
    "reversibility_risk_reasoning": "Ticket created in external ITSM can be closed or cancelled.",
    "asset_criticality_relevance": false,
    "asset_criticality_relevance_reasoning": "1. Operation Type Check: Mutative action (creates ticket). Fails rule: mutative actions do not qualify for asset criticality calculation. 2. Asset Identifier Presence: Operates on title/description parameters. 3. Discovery of Pre-existing Metadata/Scope Signals: Returns ticket ID. 4. Downstream Utility: Does not return asset criticality classification metadata.",
    "volume_risk_score": "Low",
    "scope_risk_score": "Low",
    "friction_risk_score": "Low",
    "reversibility_risk_score": "Medium",
    "asset_criticality_categories": [],
    "asset_criticality_categories_reasoning": "Not applicable as relevance is false."
  },
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
