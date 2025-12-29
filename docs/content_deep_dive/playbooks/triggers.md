# Triggers

A trigger is the entry point of a playbook, defining the specific conditions under which the
playbook will be automatically executed. Each playbook has a single trigger defined in the
`trigger.yaml` file.

## What is a Trigger?

A trigger is essentially an event listener that starts a playbook workflow when a specific event
occurs in Google SecOps. The most common type of trigger is an **alert trigger**, which initiates a
playbook when a new alert is generated or an existing one is updated.

Triggers can be configured to be highly specific, ensuring that a playbook only runs on the intended
alerts. This is achieved by setting conditions based on various alert fields.
