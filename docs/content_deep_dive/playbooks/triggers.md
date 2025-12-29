# Deep Dive: Playbook Triggers

A trigger is the entry point of a playbook, defining the specific conditions under which the playbook will be executed. Each playbook has a single trigger defined in the `trigger.yaml` file. Triggers are essential for automating responses and ensuring that playbooks run in the correct context.

For more detailed information on playbook triggers in Google Security Operations, you can refer to the official documentation:
[Google Cloud: Using triggers in playbooks](https://docs.cloud.google.com/chronicle/docs/soar/respond/working-with-playbooks/using-triggers-in-playbooks)

## What is a Trigger?

A trigger is an event listener that starts a playbook workflow when a specific event occurs in Google SecOps. When a trigger's conditions are met, it initiates the playbook and passes the relevant event data (like an alert or entity) to the playbook's first step.

There are three main types of triggers:

### 1. Alert Trigger
The most common type of trigger. It activates a playbook in response to the creation or update of an alert. Alert triggers are highly configurable and can be set to run only on alerts that match specific criteria.

**Use Case:** Automatically enrich a newly detected phishing alert with information about the sender's IP address.

### 2. Entity Trigger
This trigger activates a playbook when a specific type of entity (e.g., a user, IP address, or file hash) is created or updated.

**Use Case:** When a new user entity is created, automatically check if that username has appeared in recent threat intelligence reports.

### 3. Manual Trigger
A manual trigger allows a security analyst to start a playbook with a single click from an alert, case, or entity view. This provides the analyst with control over when to initiate an automated workflow.

**Use Case:** An analyst is investigating a suspicious host and wants to run a playbook to isolate it from the network and collect forensic data.

## Trigger Conditions

Triggers use conditions to ensure that a playbook only runs on the intended events. These conditions are defined in the `trigger.yaml` file and can be based on various fields of the trigger event (e.g., alert name, severity, or entity type).

You can create complex logic by combining multiple conditions using `AND` and `OR` operators. This allows for precise control over when a playbook is executed.

## The `trigger.yaml` file

The `trigger.yaml` file is the heart of the playbook's trigger. It defines:
- The **trigger type** (Alert, Entity, or Manual).
- The **conditions** that must be met for the trigger to fire.
- The **version** and other metadata of the trigger.

Here is a conceptual example of what a `trigger.yaml` for an alert trigger might look like:

```yaml
id: "b1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6"
name: "High Priority Phishing Alert Trigger"
version: 1.0
trigger_type: "alert"
conditions:
  - operator: "AND"
    rules:
      - field: "alert.name"
        operator: "contains"
        value: "Phishing"
      - field: "alert.severity"
        operator: "equals"
        value: "High"
```
This example defines a trigger that will start a playbook only when a **High** severity alert with "Phishing" in its name is detected.
