# Deep Dive: Actions

**Action**—a Python script that is used to perform a simple activity. These scripts are then used
in playbooks to build an automated response. Key use cases are enrichment of Assets and IOCs,
performing triaging activities (Update Alert), remediation (Isolate Machines).

## Action Structure

**Action Definition Example**

```yaml
name: Load JSON String to Object
description: Loads a JSON string into an object
integration_identifier: YourIntegrationIdentifier
parameters:
    -   name: Json String
        default_value: '{}'
        type: string
        description: 'A JSON string to load as an object'
        is_mandatory: true
dynamic_results_metadata:
    -   result_name: JsonResult
        show_result: true
        result_example_path: './resources/load_json_string_to_object_JsonResult_example.json'
creator: Your Name
script_result_name: is_success
```

**Simple Action Example**

```python
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator


if TYPE_CHECKING:
    from TIPCommon.base.interfaces import ApiClient
    from TIPCommon.types import JSON, Contains

SCRIPT_NAME: str = "Load JSON String to Object"


def main() -> None:
    LoadJsonStringToObject(name=SCRIPT_NAME).run()


class LoadJsonStringToObject(Action):
    def _extract_action_parameters(self) -> None:
        self.params.json_string = extract_action_param(
            siemplify=self.soar_action,
            param_name="Json String",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator: ParameterValidator = ParameterValidator(self.soar_action)
        validator.validate_json(param_name="Json String", json_string=self.params.json_string)

    def _init_api_clients(self) -> Contains[ApiClient]:
        """Since there are no API requests here, we can skip this stage."""

    def _perform_action(self, _: None = None) -> None:
        json_results: JSON = json.loads(self.params.json_string)
        self.json_results = json_results


if __name__ == "__main__":
    main()

```

## Action Inputs

Actions support the following types of input:

* via [Entities](/docs/response_integrations/content_deep_dive/entities.md) (example, VirusTotal Action “Enrich IP”)
* via Input Parameters (example, VirusTotal Action “Enrich IOCs”)
* Combined (example, Microsoft Teams action “Send User Message”)

## Action Outputs

Actions support the following main types of outputs:

* Script Result
* JSON Result
* Entity Enrichment Table (not necessarily an output, but actions can set custom properties for
  Entities)
* Predefined Widget

## Predefined Widget

**Predefined Widget**—is an HTML widget that is bound to an action and rendered using information
from JSON Result. It's provided as part of the integration content.

Here is an example of a Predefined Widget from MITRE ATT&CK integration:

![soar_widget](/docs/resources/response_integrations/soar_widget.png)

Predefined widgets are added to the Alert view via Playbooks. For more information
refer [to this post.](https://www.googlecloudcommunity.com/gc/SecOps-SOAR/Everything-you-need-to-know-about-Predefined-Widgets/m-p/862070#M3426)

**Predefined Widget Definition Example**

```yaml
action_identifier: Mock Integration Action
condition_group:
    logical_operator: and
    conditions:
        -   field_name: '[{stepInstanceName}.JsonResult]'
            match_type: not_contains
            value: '{stepInstanceName}'
data_definition:
    html_height: 400
    safe_rendering: false
    type: html
    widget_definition_scope: both
default_size: half_width
description: widget description
scope: alert
title: Mock Integration - Widget
type: html
```
