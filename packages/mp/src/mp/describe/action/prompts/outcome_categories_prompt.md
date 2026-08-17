**Input Data:**
I have provided the following files for a Google SecOps SOAR action:

1. `Script Code`: The Python execution script.
2. `Script Settings`: The YAML/JSON metadata containing action parameters, configuration, and simulation data.
3. `Manager Code`: The core Python manager class or API client files wrapping external service interactions.

**Objective:**
Classify the provided Google SecOps SOAR action into the official **Outcome Categories** (`outcome_categories`) taxonomy (27 categories) and construct a rigorous, step-by-step reasoning string grounded in physical Python API calls.

---

### Official Outcome Categories Taxonomy (27 Categories)

An action belongs to a category ONLY IF it demonstrably executes the expected outcome through physical Python API calls. If an action's operations do not strictly match any of the canonical 27 categories (such as performing technical DNS resolutions or workspace room management), all 27 boolean category flags must remain `false` (only the `reasoning` field is populated).

#### Group 1: Enrichment, Search & Context (Read-Only Operations)
- **`enrich_ioc`**: Returns reputation, prevalence, threat scores, malware family, attribution, or associated threat infrastructure (e.g., related malicious IPs, domains, hashes, campaigns, threat actors) for an indicator (hash, filename, IP, domain, URL, CVE, Threat Actor, Campaign). *(Technical DNS/IP/Whois lookups without reputation scoring or threat intelligence context are not enrichments and must leave all 27 category flags set to false).*
- **`enrich_asset`**: Returns contextual metadata (e.g., OS version, owner, department, MAC address, user profile details) for a specific user, hostname, device, or internal resource.
- **`search_asset`**: Queries directory services, CMDBs, device inventories, or workspace user stores to find users, hosts, devices, or group members matching search criteria or list filters (including querying hosts/devices associated with an IOC).
- **`search_events`**: Returns a collection of historical logs or telemetry data matching specific search parameters from SIEM, data lakes, firewall traffic logs, or endpoint telemetry repositories.
- **`search_email`**: Identifies and lists emails across the mail server based on criteria like sender, subject, date, or message ID (including polling mailboxes for user replies).
- **`get_alert_information`**: Fetches information about alerts, detections, or lists of open security incidents from a 3rd party product (read-only).

#### Group 2: Remediation & State Mutating Operations (External Write/State Mutation)
- **`create_ticket`**: Generates a new record in an external ITSM ticketing platform and returns the Ticket ID.
- **`update_ticket`**: Synchronizes status, priority, comments, notes, or field changes from SecOps to an external ITSM ticketing system, or uploads file attachments to an existing ticket.
- **`add_ioc_to_blocklist`**: Updates security controls (Firewall, EDR, Proxy, DNS filter, custom IOC watchlists, or mailbox blocked senders list) to prevent future interaction with the IOC.
- **`remove_ioc_from_blocklist`**: Restores connectivity or execution rights for an indicator by removing it from restricted lists, custom IOC watchlists, firewall rules, or mailbox blocked senders lists.
- **`add_ioc_to_allowlist`**: Marks an indicator as "known good" in security controls to prevent future security alerts or false positives (strictly when the action or policy explicitly designates allowlisting/whitelisting).
- **`remove_ioc_from_allowlist`**: Re-enables standard security monitoring and blocking for a previously trusted indicator (strictly when explicitly removing from an allowlist).
- **`disable_identity`**: Revokes active sessions and prevents a user or service account from authenticating to the network.
- **`enable_identity`**: Restores authentication capabilities and system access for a previously disabled account.
- **`reset_identity_password`**: Invalidates current credentials and triggers a password change or temporary password generation.
- **`update_identity`**: Modifies account metadata, group memberships, Organizational Units (OU), roles, permissions, or contact info in directory/IAM services.
- **`contain_host`**: Isolates an endpoint from the network via EDR, allowing communication only with the management console.
- **`uncontain_host`**: Removes network isolation and restores the endpoint's full communication capabilities.
- **`execute_command_on_the_host`**: Runs a script or system command on a remote endpoint and returns the standard output (STDOUT).
- **`send_email`**: Dispatches an outbound email notification or response to specified recipients.
- **`delete_email`**: Removes or purges a specific email or thread from one or more user mailboxes.
- **`update_email`**: Modifies the state of an email, such as moving it to quarantine, marking as read, applying labels, or unmarking junk.
- **`submit_file`**: Uploads a file or sample to a sandbox or analysis engine and returns a behavior report or threat score.

#### Group 3: Platform Operations & Communication
- **`update_alert`**: Changes the status, severity, SLA, score, stage, custom fields, or assignee of an alert/case strictly **within the SecOps platform** (internal SOAR SDK calls: `siemplify.<method>`). Modifying, closing, or updating alerts/detections in external 3rd-party systems via manager API calls does NOT match `update_alert` and MUST leave all 27 category flags set to `false`.
- **`add_alert_comment`**: Appends analyst notes, comments, or automated log entries to the alert's activity timeline (applies to alert/detection comments in both internal SecOps and external security detection platforms).
- **`send_message`**: Sends a message, card, interactive question, or uploaded file to a communication app channel or user.
- **`download_file`**: Retrieves a specific file, report artifact (PDF/XML/CSV), or sandbox dump from a remote system for local forensic analysis or attaches it to the SOAR case via `siemplify.result.add_attachment`.

---

### Mandatory Evaluation Rules & Negative Constraints

1. **Physical API Call Traceability**: Set a boolean flag to `true` ONLY IF the Python code explicitly executes that capability via an executable API call. Never infer flags from action names, docstrings, or assumed playbook workflows.
2. **Read vs. Write State Mutation Boundary**: If the script only performs read/query operations (HTTP GET, LDAP query), ALL mutating categories (`contain_host`, `add_ioc_to_blocklist`, `disable_identity`, `update_alert`, `create_ticket`, `update_ticket`, `reset_identity_password`, `update_identity`, `enable_identity`, `uncontain_host`, `delete_email`, `update_email`) MUST be strictly `false`.
3. **Alert Operations Disambiguation**:
   * **`update_alert`**: Applies STRICTLY to operations modifying alerts/cases **within the Google SecOps platform** (`siemplify.<method>`). Mutating or closing alerts in external 3rd-party security platforms does not match `update_alert` and maps to `false` (`[]`).
   * **`add_alert_comment`**: Applies to adding analyst notes, comments, or log entries to an alert's activity timeline in internal SecOps OR in external security detection platforms.
   * **`get_alert_information`**: Applies to read-only queries fetching alert details or open incident queues from 3rd-party security products.
4. **IOC Management & Watchlists (Add vs. Delete vs. Allowlist)**:
   * Adding or uploading custom IOCs (IP, domain, hash, URL) to security controls or threat detection watchlists MUST be mapped strictly to `add_ioc_to_blocklist: true`.
   * Deleting or removing custom IOCs from security controls or watchlists MUST be mapped strictly to `remove_ioc_from_blocklist: true`. Do NOT flag `remove_ioc_from_allowlist` unless the action or parameters explicitly target allowlist/whitelist policies.
5. **Asset Queries by IOC**:
   * Actions that query endpoint inventories to find hosts or devices associated with an IOC (e.g., `Get Hosts by IOC`, `Search Devices by IP`) search device inventory matching criteria and MUST be mapped strictly to `search_asset: true`.
6. **Composite / Dual-Outcome Actions (Exhaustiveness)**: If an action executes multiple distinct capabilities, you MUST flag ALL executed categories as `true`:
   * Downloads a report/attachment artifact via `add_attachment` AND enriches entities with scan telemetry: `download_file: true` AND `enrich_asset: true`.
   * Asynchronously polls/searches a mailbox for replies AND downloads attachments into the case: `search_email: true` AND `download_file: true`.
   * Unblocks a sender in a mailbox AND restores/moves emails out of junk: `remove_ioc_from_blocklist: true` AND `update_email: true`.
7. **Ping & Connectivity Checks**: For health check, ping, or connection test actions, ALL 27 outcome categories boolean flags MUST be strictly `false`.
8. **Mandatory 3-Step Reasoning Protocol with Literal Method Citations**:
   The `reasoning` field MUST strictly follow this exact 3-step format and quote literal Python method calls (`manager.<method_name>(<args>)` or `siemplify.<method_name>(<args>)`):
   * **Step 1 (State Boundary & Action Classification)**: Explicitly state whether the action is read-only or state-mutating, identify the target object and API scope, and identify candidate category groups. If it is a ping/health check, state that all categories are false.
   * **Step 2 (Physical Code Evidence)**: Explicitly quote the literal Python method call(s) executed by the script (e.g., `manager.<method_name>(<args>)` or `siemplify.<method_name>(<args>)`), HTTP methods/endpoints, and data handlers.
   * **Step 3 (Taxonomy Mapping & Disambiguation)**: Map physical code evidence directly to the taxonomy definition for all `true` flags, and explicitly explain why adjacent/related categories are `false`.

9. **Network Security Policies & Firewall Rule Modifications**:
   Modifying network security controls (Firewalls, Security Groups, Access Control Lists, Proxy policies) by adding or removing network indicators (IPs, CIDRs, domains) represents direct remediation on a security control policy.
   * When an action adds IP ranges or indicators to a firewall rule or security policy, map it to `add_ioc_to_blocklist: true`.
   * When an action removes IP ranges or indicators from a firewall rule or security policy, map it to `remove_ioc_from_blocklist: true` (and `remove_ioc_from_allowlist: true` if rule policy is bidirectional).

10. **ITSM & Ticketing Platforms (Ticket Queries vs. Mutations & Attachments)**:
   * **Read-Only Ticket Queries**: Actions that fetch or query tickets/incidents from external ITSM platforms (e.g., `Get Incident`, `Get Ticket`, `Get Record Details`) perform read operations on ticketing systems. They do NOT match `get_alert_information` (which is strictly reserved for security detection/alert feeds from 3rd party security products). All 27 category flags MUST remain `false` (`[]`).
   * **Ticket Mutations & File Attachments**: Actions that create tickets map to `create_ticket: true`. Actions that update ticket fields, add notes/comments, or upload file attachments to an existing ticket/record (e.g., `Add Attachment`, `Upload Attachment`) MUST be mapped to `update_ticket: true`. (Do NOT map to `submit_file`, which is strictly for sandbox detonation).

11. **Asset & Identity Entities — Direct Lookup vs. Filter Search**:
   * **Direct Entity Profile / CI Lookup by ID**: Actions that query a repository (directory, CMDB, user profile store, or workspace) for a specific user, host, or device by a unique identifier (e.g., Email, Username, User ID, Sys ID, Device ID) to retrieve contextual metadata, attributes, or profile information MUST be mapped to `enrich_asset: true`.
   * **Filter Search / Listing**: Actions that search a repository, directory, CMDB, or workspace using search criteria, queries, or list multiple records matching parameters (e.g., `List Users`, `List CMDB Records`, `Search Assets`) MUST be mapped to `search_asset: true`.

12. **Communication & Collaboration Platforms (Messages vs. Container Administration)**:
    * **Messages, Notifications & File Uploads**: Sending text messages, interactive cards, replies, or uploading files/attachments to channels or users (e.g., `Send Message`, `Send Chat Message`, `Upload File`, `Ask Question`) represents dispatching communication content to recipients and MUST be mapped to `send_message: true`.
    * **Channel & Chat Container Administration**: Creating, deleting, renaming channels or managing channel membership (e.g., `Create Channel`, `Delete Channel`, `Add Users To Channel`, `Remove Users From Channel`, `List Channels`) modifies application-level collaboration rooms. All 27 category flags MUST remain `false` (`[]`).

13. **Threat Intelligence vs. Technical Lookups**:
    * `enrich_ioc`: Applies to threat intelligence reputation queries, threat scoring, attribution, threat campaigns, or queries retrieving related threat infrastructure indicators.
    * Technical DNS/Whois/IP lookups without threat intelligence context or reputation scoring do NOT match `enrich_ioc` and MUST leave all 27 category flags set to `false`.

---

### Generic Archetype Examples (Compact Format)

#### Example 1: Composite Vulnerability Scan & Report Download
*Code Snippet:*
```python
manager = SecurityScannerManager(api_key=api_key)
scan_id = manager.launch_scan(target=entity.identifier)
report_bytes = manager.download_report(scan_id=scan_id, format="pdf")
siemplify.result.add_attachment(title=f"Scan_{scan_id}.pdf", filename="report.pdf", file_contents=report_bytes)
entity.additional_properties["vulnerabilities"] = manager.get_scan_results(scan_id)
entity.is_enriched = True
siemplify.update_entities([entity])
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs a composite workflow: it launches a scan, fetches vulnerability telemetry to enrich an entity, and downloads a binary report file to attach to the SOAR case. Step 2 (Physical Code Evidence): Calls `manager.launch_scan(target=entity.identifier)`, `manager.download_report(scan_id=scan_id, format=\"pdf\")`, `siemplify.result.add_attachment(...)` to attach the report PDF, and `siemplify.update_entities([entity])` with `is_enriched = True`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Download File' because it retrieves a report artifact from an external system and attaches it to the case. Matches 'Enrich Asset' because it retrieves vulnerability telemetry for an internal entity and enriches the SOAR asset. All other remediation categories are false.",
    "download_file": true,
    "enrich_asset": true
  }
}
```

#### Example 2: Internal SecOps Platform Alert Status / SLA Update
*Code Snippet:*
```python
siemplify = SiemplifyAction()
siemplify.set_case_stage(case_id=case_id, stage="Investigation")
siemplify.pause_alert_sla(alert_id=alert_id)
siemplify.end("Successfully updated alert status and SLA", True)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action modifies the stage and pauses the SLA timer for an alert/case within the Google SecOps platform using internal SDK methods, so evaluate Group 3 (Platform Operations & Communication). Step 2 (Physical Code Evidence): Calls internal SDK methods `siemplify.set_case_stage(case_id=case_id, stage=\"Investigation\")` and `siemplify.pause_alert_sla(alert_id=alert_id)`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Update Alert' because it modifies the status, stage, and SLA of the alert strictly within the SecOps platform. (External 3rd-party alert modifications do not match update_alert).",
    "update_alert": true
  }
}
```

#### Example 3: External Security Platform Alert Comment
*Code Snippet:*
```python
manager = SecurityAlertPlatformManager(credentials=credentials)
manager.add_comment_to_alert(alert_id=alert_id, comment=comment_text)
siemplify.result.add_result_json({"status": "success"})
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs a state-mutating POST operation adding a comment to an alert in a security platform, so evaluate Group 3 (Platform Operations & Communication). Step 2 (Physical Code Evidence): Calls `manager.add_comment_to_alert(alert_id=alert_id, comment=comment_text)`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Add Alert Comment' because it appends analyst notes or comments to an alert's activity timeline. Does not match 'Update Alert' (which is strictly for internal SecOps alert status/severity modifications) or 'Update Ticket' (targets security alerts, not ITSM tickets).",
    "add_alert_comment": true
  }
}
```

#### Example 4: User Profile & Asset Search Query
*Code Snippet:*
```python
manager = WorkspaceManager(server=server, credentials=credentials)
users = manager.list_users(query_filter=query_filter, max_results=50)
siemplify.result.add_result_json(users)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is read-only (queries users matching search filter criteria without modifying records), so evaluate Group 1 (Enrichment & Search). Step 2 (Physical Code Evidence): Calls `manager.list_users(query_filter=query_filter, max_results=50)` to search user records matching specific parameters. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Search Asset' because it queries a user repository/workspace for entities matching criteria. Does not match 'Update Identity' (no account mutation occurs) or 'Enrich IOC' (target is internal user entities, not external threat indicators).",
    "search_asset": true
  }
}
```

#### Example 5: Threat Intelligence Infrastructure & Campaign Relationships
*Code Snippet:*
```python
manager = ThreatIntelManager(api_key=api_key)
related_infra = manager.get_related_domains(indicator=entity.identifier)
entity.additional_properties["related_domains"] = related_infra
entity.is_enriched = True
siemplify.update_entities([entity])
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is read-only, retrieving relationship threat intelligence and associated threat infrastructure for an indicator without mutating state, so evaluate Group 1 (Enrichment & Search). Step 2 (Physical Code Evidence): Calls `manager.get_related_domains(indicator=entity.identifier)`, sets `entity.additional_properties["related_domains"]`, and enriches the entity via `siemplify.update_entities([entity])`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Enrich IOC' because it queries a threat intelligence platform to retrieve associated threat infrastructure and indicator relationships to enrich the IOC entity. All other categories are false.",
    "enrich_ioc": true
  }
}
```

#### Example 6: ITSM Ticket Creation
*Code Snippet:*
```python
manager = ITSMServiceManager(domain=domain, api_key=api_key)
ticket = manager.create_incident(title=title, description=description, priority=priority)
siemplify.result.add_result_json(ticket)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs an external state-mutating POST request to create an incident record in an external ITSM ticketing platform, so evaluate Group 2 (Remediation & State Mutation). Step 2 (Physical Code Evidence): Calls `manager.create_incident(title=title, description=description, priority=priority)` to create a new ticket record. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Create Ticket' because it generates a new record in an external ITSM ticketing system. Does not match 'Update Ticket' (generates a new record rather than modifying an existing one) or 'Update Alert' (targets ITSM tickets, not internal SecOps alerts).",
    "create_ticket": true
  }
}
```

#### Example 7: Ping / Health Check Action
*Code Snippet:*
```python
manager = ApiClient(api_key=api_key)
manager.test_connectivity()
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is a connectivity test / health check that validates API credentials without fetching telemetry or mutating state. All outcome categories are false. Step 2 (Physical Code Evidence): Calls `manager.test_connectivity()` to validate authentication and connection status. Step 3 (Taxonomy Mapping & Disambiguation): Health checks and connectivity tests do not map to any functional security outcome category, so all 27 boolean flags are strictly false."
  }
}
```

#### Example 8: Firewall Rule IP Range Modification
*Code Snippet:*
```python
manager = FirewallManager(credentials=credentials)
rule = manager.get_firewall_rule(rule_name=rule_name)
rule.extend_ip_ranges(ip_ranges=ip_ranges)
manager.patch_firewall_rule(rule_name=rule_name, firewall=rule)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs an external state-mutating operation modifying network security control policies by adding IP ranges to a firewall rule, so evaluate Group 2 (Remediation & State Mutation). Step 2 (Physical Code Evidence): Calls `manager.get_firewall_rule(rule_name=rule_name)`, `rule.extend_ip_ranges(ip_ranges=ip_ranges)`, and `manager.patch_firewall_rule(rule_name=rule_name, firewall=rule)` to apply policy changes to the firewall. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Add IOC to Blocklist' because updating a firewall rule with IP ranges is the standard security control mechanism to block network traffic for IOCs. All other categories are false.",
    "add_ioc_to_blocklist": true
  }
}
```

#### Example 9: ITSM Ticket Attachment
*Code Snippet:*
```python
manager = ITSMServiceManager(domain=domain, api_key=api_key)
manager.upload_attachment(table_name="incident", record_sys_id=sys_id, file_path=file_path)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs an external state-mutating operation by uploading a file attachment to an existing record in an ITSM ticketing platform, so evaluate Group 2 (Remediation & State Mutation). Step 2 (Physical Code Evidence): Calls `manager.upload_attachment(table_name=\"incident\", record_sys_id=sys_id, file_path=file_path)`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Update Ticket' because attaching a file modifies the state and content of an existing ticket in an external ITSM platform. Does not match 'Submit File' (uploaded to ITSM, not a dynamic sandbox analysis engine).",
    "update_ticket": true
  }
}
```

#### Example 10: Communication File Upload & Dispatch
*Code Snippet:*
```python
manager = CommunicationManager(api_token=api_token)
manager.upload_file(channel_id=channel_id, file_path=file_path, comment="Incident summary report")
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs an external state-mutating operation by uploading and posting a file/content to a communication channel, so evaluate Group 3 (Platform Operations & Communication). Step 2 (Physical Code Evidence): Calls `manager.upload_file(channel_id=channel_id, file_path=file_path, comment=\"Incident summary report\")` to send file content to the target channel. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Send Message' because dispatching a file with comments to a communication channel delivers communication content to recipients. Does not match 'Submit File' (sent to a communication channel, not a sandbox detonation engine).",
    "send_message": true
  }
}
```

#### Example 11: Specific User Profile Direct Lookup by ID
*Code Snippet:*
```python
manager = DirectoryClient(server=server, credentials=credentials)
user_profile = manager.get_user_profile(user_id=user_id)
siemplify.result.add_result_json(user_profile)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is read-only, retrieving contextual profile metadata for a specific user entity by identifier without mutating state, so evaluate Group 1 (Enrichment & Search). Step 2 (Physical Code Evidence): Calls `manager.get_user_profile(user_id=user_id)` and outputs user details via `siemplify.result.add_result_json(...)`. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Enrich Asset' because it performs a direct lookup of a specific internal user asset by ID to retrieve contextual profile metadata (e.g., department, contact info, status). Does not match 'Search Asset' (direct identifier lookup rather than filter query across inventory). All state-mutating categories are false.",
    "enrich_asset": true
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
1. Analyze script code, settings, and manager methods.
2. Formulate the mandatory 3-step reasoning quoting exact Python method calls (`manager.<method_name>(<args>)` or `siemplify.<method_name>(<args>)`).
3. Set all applicable outcome category boolean flags accurately (unmatched categories default to false).
