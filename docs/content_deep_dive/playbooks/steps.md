# Steps

Steps are the individual building blocks of a playbook, representing a single action or task to be
executed. When chained together, they form the automated workflow of the playbook. Each step is
defined in its own YAML file within the `steps/` directory of a playbook.

## What is a Step?

A step can be one of several types of actions:

* **Integration Action:** A call to an action from a response integration (e.g.,
  `VirusTotal_Enrich_IP`). This is the most common type of step and allows playbooks to interact
  with third-party tools.
* **Function:** A built-in playbook function to perform a specific task, such as setting a variable,
  adding a comment, or changing the case severity.
* **Condition:** A logical block that allows the playbook to branch based on the outcome of a
  previous step or the value of a variable. This enables dynamic and flexible workflows.
* **Block:** A call to another playbook, allowing for modular and reusable workflow components.
