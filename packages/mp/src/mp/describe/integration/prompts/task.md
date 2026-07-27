**Input Data:**
I have provided the following information for a Google SecOps integration:

1. `Integration Name`: The name of the integration.
2. `Integration Description`: The original description of the integration.
3. `Actions AI Descriptions`: A collection of AI-generated descriptions for all actions in this integration.
4. `Connectors AI Descriptions`: A collection of AI-generated descriptions for all connectors in this integration.
5. `Jobs AI Descriptions`: A collection of AI-generated descriptions for all jobs in this integration.

**Integration Product Categories Definitions:**
Review these categories carefully. An integration can belong to multiple categories if its actions/connectors fulfill the criteria.
- **SIEM**: Use when you need to find the activity related to Assets, Users or see if an IOC has been seen globally across your logs in the last 90 days. Expected Outcome: Returns a timeline of activity, lists all internal assets that touched an IOC, and identifies source of the suspicious activity.
- **EDR**: Use when the investigation involves a specific host (workstation/server) and you need to see deep process-level activity. Expected Outcome: Returns the process tree (Parent/Child), retrieves suspicious files for analysis, or contains the host by isolating it from the network.
- **Network Security**: Use when an internal asset is communicating with a known malicious external IP or to verify if a web-based attack was blocked. Expected Outcome: Returns firewall/WAF permit/deny logs and allows the agent to block malicious IPs/URLs at the gateway.
- **Threat Intelligence**: Use as the first step of enrichment for any external indicator (IP, Hash, URL) to determine its reputation. Expected Outcome: Returns risk scores, malware family names, and historical "last seen" data to confirm if an alert is a True Positive.
- **Email Security**: Use when the alert involves a phishing report, a suspicious attachment, or a link delivered via email. Expected Outcome: Returns a list of all affected users who received the same email and allows the agent to manage emails in all inboxes.
- **IAM & Identity Management**: Use when a user account is showing suspicious behavior and you want to manage identity. Expected Outcome: Returns user or identity group/privilege levels and allows the agent to suspend accounts, force password resets, reset service accounts.
- **Cloud Security**: Use for alerts involving cloud-native resources GCP/AWS/Azure. Expected Outcome: Returns resource configuration states, findings and identifies rogue cloud instances or API keys.
- **ITSM**: Use to document the investigation, assign tasks to other teams. Expected Outcome: Creates/updates tickets, assigns tasks to specific departments.
- **Vulnerability Management**: Use to verify if a targeted asset is actually susceptible to the exploit seen in the alert. Expected Outcome: Returns CVE information and a list of missing patches on the target host to determine if the attack had a high probability of success.
- **Asset Inventory**: Use when you want to get more information about an internal asset. Expected Outcome: Returns the asset owner, department, business criticality, and whether the device is managed by IT.
- **Collaboration**: Use when an automated action requires a "Human-in-the-Loop" approval or when the SOC needs to be notified of a critical find. Expected Outcome: Sends interactive alerts to Slack/Teams for manual approval and notifies stakeholders of critical findings.

**Instructions:**
Analyze the provided information and determine the product categories that best describe the integration's capabilities.
Connectors are especially important for determining if the integration is a SIEM or EDR, as they handle the data ingestion.
**Reasoning First:** You MUST write out your step-by-step reasoning in the `reasoning` field before populating the boolean flags. Discuss why the integration matches or fails to match specific categories based on the definitions provided above.

**Current Task Input:**

Integration Name: ${integration_name}
Integration Description: ${integration_description}

Actions AI Descriptions:
${actions_ai_descriptions}

Connectors AI Descriptions:
${connectors_ai_descriptions}

Jobs AI Descriptions:
${jobs_ai_descriptions}

**Final Instructions:**
Based on the input data, return an IntegrationAiMetadata object containing the product categories.
A category should be marked as true if the integration has capabilities that match its "When to Use" and "Expected Outcome" descriptions.
Many integrations will have multiple categories.
If no categories match, all should be false.
Provide your response in JSON format matching the IntegrationAiMetadata schema.
