# Understand the Core Concepts

## Response Integrations

In Google SecOps, Response Integration consists of Python scripts that are designed to execute third
party API and use the information as part of the Security Operation Center workflows.

In the Platform Response Integrations are available under Content Hub → Response Integrations:

![response_integrations](/docs/resources/response_integrations/response_integrations.png)

Response Integration consists of the following script types:

- [Actions](/docs/response_integrations/content_deep_dive/actions.md)
- [Connectors](/docs/response_integrations/content_deep_dive/connectors.md)
- [Jobs](/docs/response_integrations/content_deep_dive/jobs.md)

**Action**—a Python script that is used to perform a simple activity. These scripts are then used
in playbooks to build an automated response. Key use cases are enrichment of Assets and IOCs,
performing triaging activities (Update Alert), remediation (Isolate Machines).

**Connector**—a Python script that runs continuously like a cron job. The main goal of the
connector is to ingest Alerts and Events from third party products into Google SecOps.

> **Note:** in Google SecOps you can also ingest data via SIEM Feed + Parser and in general, that’s
> the preferred method.

**Jobs**—a Python script that runs continuously, similar to the connector, but the use case for
this script is to synchronize information between Google SecOps and third Party Product. For
example,
if a comment was added to a Google SecOps Alert, to add the same comment to a third Party Alert.

You don’t need to have all script types inside the Response Integration for it to be considered
valid. As an example, in our official repository we have Response Integrations that only contain 2–3
actions and nothing else.

---

## Playbooks

Playbooks in Google SecOps are automated workflows that orchestrate and automate the response to
security incidents. Playbooks automate repetitive and manual tasks that are part of an incident
response process. This can include enriching alerts with threat intelligence, quarantining infected
devices, or creating tickets in an IT service management system. They are a series of actions and
decisions that are automatically executed when
a specific trigger is met, such as a new alert.

Core concepts of Google SecOps Playbooks:

**Triggers and Actions:** A playbook is initiated by a trigger, which can be a new alert, a change
in an entity's risk score, or a manual action by an analyst. Once triggered, the playbook executes a
series of actions, which are the individual steps in the workflow.

**Conditional Logic:** Playbooks can include conditional logic to make decisions based on the data
in an alert or the output of a previous action. This allows for the creation of dynamic and flexible
workflows that can adapt to different types of incidents.

**Blocks:** A playbook can include a series of blocks. Each block represents a single step in the
playbook's
workflow.

**Integration with Security Tools:** Playbooks integrate with a wide range of security tools and
technologies, including SIEMs, endpoint detection and response (EDR) solutions, and threat
intelligence platforms. This allows for the orchestration of a coordinated response across the
entire security infrastructure.

**Customization and Extensibility:** Playbooks can be customized to meet the specific needs of an
organization. They can also be extended with custom scripts and integrations to support new tools
and workflows.

By using playbooks, security teams can standardize their incident response processes, reduce
response times, and improve the overall effectiveness of their security operations.
