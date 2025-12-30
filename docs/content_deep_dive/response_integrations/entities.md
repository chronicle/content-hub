# Deep Dive: Entities

Entities - is a special concept in Google SecOps that describes IOCs and Assets associated with an
Alert.

**Note:** Entities in SIEM and entities in SOAR component have slight differences in terms of how
they work. Everything in this page refers to SOAR Entities.

Entities are a key part of Google SecOps Case Management. Here is an example of Entities:

![entities_example](/docs/resources/response_integrations/entities_example.png)

Entities are automatically extracted from the data ingested into SecOps via Connectors.
Actions can be designed to run in a way where entities are used as input.

For example, if you want to automatically enrich a hash associated with the alert, then the best
practice is to take the value from File Hash instead of having a separate input parameter.

Entities have their own metadata and properties that can be extended as part of Actions execution.

![detailed_entity_example](/docs/resources/response_integrations/detailed_entity_example.png)

In general, actions that are working with Entities will have in the description a reference to it,
which is considered the best practice:

![supports_entities_description](/docs/resources/response_integrations/supports_entities_description.png)
