# Deep Dive: Connectors

**Connector -** a Python script that runs continuously like a cron job. The main goal of the
connector is to ingest Alerts and Events from third party products into Google SecOps. Connectors
are
available under SOAR Settings → Ingestion → Connectors.

As part of the connector execution, you are going to build the Alert object, which is then processed
by the ETL. If everything is constructed correctly, the user will receive a new Alert inside the
Case Management.

It’s important to understand that the connector is designed to create Alerts and not Cases. Cases
are automatically created by the platform. Alerts might be grouped into existing cases if they
match certain conditions (time frame, similarity in affected entities)

**Connector Definition Example**

```yaml
name: Example Connector
parameters:
    -   name: Alert JSON to ingest
        # language=json
        default_value: |
            {
                "display_name": "display_name",
                "events": [
                    {"key1": "value1"}
                ]
            }
        type: string
        description: The event that would be ingested by the connector
        is_mandatory: true
        is_advanced: false
        mode: regular
description: Description
integration: IntegrationIdentifier
rules: [ ]
is_connector_rules_supported: true
creator: Admin
```

**Simple Connector Example**

```python
from __future__ import annotations

import uuid

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.base.connector import Connector
from TIPCommon.data_models import BaseAlert
from TIPCommon.extraction import extract_connector_param
from TIPCommon.validation import ParameterValidator


def main() -> None:
    ExampleConnector(script_name="Example Connector").start()


class ExampleConnector(Connector):
    def extract_params(self) -> None:
        self.params.alert_json = None
        self.params.alert_json_str = extract_connector_param(
            siemplify=self.siemplify,
            param_name="Alert JSON to ingest",
            is_mandatory=True,
            print_value=True,
        )

    def validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.siemplify)
        self.params.alert_json = validator.validate_json(
            param_name="Alert JSON to ingest",
            json_string=self.params.alert_json_str,
        )

        self._validate_alert_json()

    def _validate_alert_json(self) -> None:
        match self.params.alert_json:
            case {"display_name": _, "events": [*_, _]} as alert_json if alert_json:
                return

            case _:
                msg: str = (
                    "Alert JSON to ingest is not a valid Alert object. "
                    "Please provide a valid JSON object with the following structure: "
                    "{'display_name': 'display_name', 'events': [...]}"
                )
                raise ValueError(msg)

    def init_managers(self) -> None:
        """No API requests needed for the connector."""

    def get_alerts(self) -> list[BaseAlert]:
        alert: BaseAlert = BaseAlert(raw_data=self.params.alert_json, alert_id=uuid.uuid4())
        return [alert]

    def create_alert_info(self, alert: BaseAlert) -> AlertInfo:
        alert_info: AlertInfo = AlertInfo()

        alert_info.alert_id = alert.alert_id
        alert_info.display_id = alert.raw_data["display_name"]
        alert_info.events = alert.raw_data["events"]

        return alert_info


if __name__ == "__main__":
    main()

```

## Ontology & Mapping

Ontology is a mechanism used by the platform to automatically extract Entities and additional
metadata from the Alerts that are ingested by the connector. Ontology Mapping is available under
SOAR Settings → Ontology → Ontology Status.

The ontology has a 3-level hierarchy:

- Source
- Product
- Event

In general, the names of the levels don’t have any significant meaning behind them.
You need to look at it from the perspective that you can define mapping at different levels, and the
level below will inherit mapping from the level higher.

Inheritance is in the order: Source → Product → Event

This is what it looks like on the platform:

![ontology](/docs/resources/response_integrations/ontology.png)

The values for the ontology are attached to the Events that are associated with the Alert.

Ontology mapping can be provided with the Response integration. The best practice is to create the
ontology in a way that the "Product" level corresponds to the connector. This way, all the Alerts
that are ingested by that connector will have the same ontology applied to it, and it’s easier to
manage everything.

Out of all fields that are possible to map, the most critical are:

- Start Time
- End Time

If those fields are not mapped out, then the Alert grouping mechanism will not work.

Inside the Response integration structure, ontology mapping is in the *
*`integration_mapping_rules.yaml`** file.

When the integration has a connector, it also **MUST** have a mapping.

For more information about Ontology and
Mapping, [please refer to the official documentation.](https://cloud.google.com/chronicle/docs/soar/admin-tasks/ontology/ontology-overview)

