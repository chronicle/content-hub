**Input Data:**
I have provided the following files for a Google SecOps SOAR action:

1. `Script Code`: The Python execution script.
2. `Script Settings`: The YAML/JSON metadata containing action parameters, configuration, and simulation data.
3. `Manager Code`: The core Python manager class or API client files wrapping external service interactions.

**Objective:**
Classify the provided Google SecOps SOAR action into the official **Outcome Categories** (`outcome_categories`) taxonomy (27 categories) and construct a rigorous, step-by-step reasoning string grounded in physical Python API calls.

---

### Official Outcome Categories Taxonomy (27 Categories)

An action belongs to a category ONLY IF it demonstrably executes the expected outcome through physical Python API calls. If an action's operations do not strictly match any of the canonical 27 categories (such as updating alerts in 3rd-party external platforms, performing technical DNS resolutions, administrative operations, or utility checks), all 27 boolean category flags must remain `false` (only the `reasoning` field is populated).

#### Group 1: Enrichment, Search & Context (Read-Only Operations)
- **`enrich_ioc`**: Queries external threat intelligence to retrieve reputation, threat scores, malware family, or context for external indicators (IP, domain, URL, hash, CVE). *(Technical DNS/IP lookups without reputation scoring are not enrichments and must leave all 27 category flags set to false).*
- **`enrich_asset`**: Queries internal inventory, CMDB, or vulnerability databases to return contextual metadata, configuration, or vulnerability insights for specific internal entities (hosts, users, internal IPs).
- **`search_asset`**: Queries directory services (LDAP/Active Directory), CMDBs, or device search engines to find users, hosts, devices, or group members matching search criteria or group filters.
- **`search_events`**: Queries SIEM logs, data lakes, firewall traffic/threat logs, or endpoint telemetry repositories to return a collection of historical logs or events.
- **`search_email`**: Searches mailbox servers or email archives across mailboxes based on sender, recipient, subject, or attachment criteria.
- **`get_alert_information`**: Fetches alert details, detections, or lists/queues of open incidents/alerts from external security platforms (read-only).

#### Group 2: Remediation & State Mutating Operations (External Write/State Mutation)
- **`create_ticket`**: Generates a new issue/incident record in an external ITSM ticketing platform (e.g., Jira, ServiceNow, Freshservice).
- **`update_ticket`**: Updates status, priority, comments, notes, or fields of an existing ticket in an external ITSM ticketing platform.
- **`add_ioc_to_blocklist`**: Adds an indicator (IP, domain, URL, hash) to security control blocklists/policies (firewall, proxy, DNS filter, EDR blocklist).
- **`remove_ioc_from_blocklist`**: Removes an indicator from security control blocklists to restore connectivity or execution rights.
- **`add_ioc_to_allowlist`**: Adds an indicator to security control allowlists / trusted lists to prevent alerts.
- **`remove_ioc_from_allowlist`**: Removes an indicator from security control allowlists to re-enable monitoring/blocking.
- **`disable_identity`**: Revokes active sessions and prevents a user or service account from authenticating.
- **`enable_identity`**: Restores authentication capabilities and system access for a disabled account.
- **`reset_identity_password`**: Invalidates credentials and triggers a password change or temporary password generation.
- **`update_identity`**: Modifies account metadata, group memberships, roles, permissions, or contact info in directory/IAM services.
- **`contain_host`**: Isolates an endpoint from the network via EDR agent (allowing communication only with management console).
- **`uncontain_host`**: Lifts network isolation on an endpoint via EDR agent.
- **`execute_command_on_the_host`**: Runs a script or system command on a remote endpoint/VM and returns output (STDOUT).
- **`send_email`**: Dispatches an outbound email notification or response to specified recipients.
- **`delete_email`**: Removes or purges specific emails or threads from user mailboxes.
- **`update_email`**: Modifies email state (e.g., moving to quarantine, marking as read, applying labels).
- **`submit_file`**: Uploads a file or sample to an external sandbox or analysis engine for dynamic detonation/scanning.

#### Group 3: Platform Operations & Communication
- **`update_alert`**: Modifies the status, severity, or assignee of an alert/case strictly within the Google SecOps platform (e.g., using Siemplify internal alert/case manipulation methods). Actions updating alerts/issues/incidents in external 3rd-party security platforms (e.g., Azure Security Center, Defender, Sentinel, Orca, Wiz) do NOT match `update_alert` and must leave all 27 outcome category boolean flags set to `false`.
- **`add_alert_comment`**: Appends analyst notes or comments to the alert activity timeline in SecOps or external security platform.
- **`send_message`**: Dispatches a notification, card, or message to a chat/collaboration platform (e.g., Slack, Teams, Google Chat).
- **`download_file`**: Retrieves any file, report artifact (PDF/XML/CSV), or sandbox dump from an external system and downloads/attaches it to the SOAR case via `siemplify.result.add_attachment` or file save.

---

### Mandatory Evaluation Rules & Negative Constraints

1. **Physical API Call Traceability**: Set a boolean flag to `true` ONLY IF the Python code explicitly executes that capability via an executable API call. Never infer flags from action names, docstrings, or assumed playbook workflows.
2. **Read vs. Write State Mutation Boundary**: If the script only performs read/query operations (HTTP GET, LDAP query), ALL mutating categories (`contain_host`, `add_ioc_to_blocklist`, `disable_identity`, `update_alert`, `create_ticket`, `update_ticket`, `reset_identity_password`, `update_identity`, `enable_identity`, `uncontain_host`, `delete_email`, `update_email`) MUST be strictly `false`.
3. **Composite / Dual-Outcome Actions (Exhaustiveness)**: If an action executes multiple distinct capabilities (e.g., downloads a report artifact via `add_attachment` AND enriches host entities with scan telemetry / `siemplify.update_entities` / `is_enriched = True`), you MUST flag ALL executed categories as `true` (e.g., `download_file: true` AND `enrich_asset: true`).
4. **Ping & Connectivity Checks**: For health check, ping, or connection test actions, ALL 27 outcome categories boolean flags MUST be strictly `false`.
5. **Mandatory 3-Step Reasoning Protocol with Literal Method Citations**:
   The `reasoning` field MUST strictly follow this exact 3-step format and quote literal Python method calls (`manager.<method_name>(<args>)` or `siemplify.<method_name>(<args>)`):
   * **Step 1 (State Boundary & Action Classification)**: Explicitly state whether the action is read-only or state-mutating, and identify candidate category groups. If it is a ping/health check, state that all categories are false.
   * **Step 2 (Physical Code Evidence)**: Explicitly quote the literal Python method call(s) executed by the script (e.g., `manager.<method_name>(<args>)`), HTTP methods/endpoints, and data handlers.
   * **Step 3 (Taxonomy Mapping & Disambiguation)**: Map physical code evidence directly to the taxonomy definition for all `true` flags, and explicitly explain why adjacent/related categories are `false`.

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

#### Example 2: External Security Alert Status Update vs. Internal SecOps Alert Update
*Code Snippet:*
```python
manager = SecurityAlertPlatformManager(client_id=client_id, secret=secret)
manager.update_alert_status(alert_id=alert_id, status="Resolved", comment="Closed via SOAR")
siemplify.result.add_result_json({"status": "success", "alert_id": alert_id})
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action executes an external state-mutating POST/PATCH operation to update the status of an alert in an external 3rd-party security platform (not internal Google SecOps). Step 2 (Physical Code Evidence): Calls `manager.update_alert_status(alert_id=alert_id, status=\"Resolved\", comment=\"Closed via SOAR\")` on the external platform API. Step 3 (Taxonomy Mapping & Disambiguation): Does not match 'Update Alert' because `update_alert` is strictly reserved for updating alerts within the Google SecOps platform itself. Does not match 'Update Ticket' (external system is a security platform, not an ITSM platform). All outcome categories are false."
  }
}
```

#### Example 3: Directory / LDAP Asset Search Query
*Code Snippet:*
```python
manager = DirectoryClient(server=server, credentials=credentials)
users = manager.search_directory(search_filter=query_filter, attributes=["mail", "memberOf"])
siemplify.result.add_result_json(users)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is read-only (queries directory objects matching a search filter without modifying records), so evaluate Group 1 (Enrichment & Search). Step 2 (Physical Code Evidence): Calls `manager.search_directory(search_filter=query_filter, attributes=[\"mail\", \"memberOf\"])` to search the directory service for user/host objects matching specific parameters. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Search Asset' because it searches a directory inventory for entities matching criteria. Does not match 'Update Identity' (no account mutation occurs) or 'Enrich IOC' (target is internal directory entities, not external threat indicators).",
    "search_asset": true
  }
}
```

#### Example 4: Historical Telemetry Log Query
*Code Snippet:*
```python
manager = NetworkTelemetryManager(host=host, api_key=api_key)
events = manager.get_traffic_logs(query=filter_str, start_time=start_time, end_time=end_time)
siemplify.result.add_result_json(events)
```
*Expected Output:*
```json
{
  "outcome_categories": {
    "reasoning": "Step 1 (State Boundary & Action Classification): The action is read-only (retrieves historical network traffic telemetry logs without altering firewall policies), so evaluate Group 1 (Enrichment & Search). Step 2 (Physical Code Evidence): Calls `manager.get_traffic_logs(query=filter_str, start_time=start_time, end_time=end_time)` to query historical traffic flow events. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Search Events' because it queries a repository of raw historical telemetry logs. Does not match 'Add IOC To Blocklist' (no policy or rule mutation occurs) or 'Get Alert Information' (retrieves raw event streams, not alert records).",
    "search_events": true
  }
}
```

#### Example 5: ITSM Ticket Creation
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
    "reasoning": "Step 1 (State Boundary & Action Classification): The action performs an external state-mutating POST request to create an incident record in an external ITSM ticketing platform, so evaluate Group 2 (Remediation & State Mutation). Step 2 (Physical Code Evidence): Calls `manager.create_incident(title=title, description=description, priority=priority)` to create a new ticket record. Step 3 (Taxonomy Mapping & Disambiguation): Matches 'Create Ticket' because it generates a new record in an external ITSM ticketing system. Does not match 'Update Ticket' (generates a new record rather than modifying an existing one) or 'Update Alert' (targets ITSM tickets, not security alerts).",
    "create_ticket": true
  }
}
```

#### Example 6: Ping / Health Check Action
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
