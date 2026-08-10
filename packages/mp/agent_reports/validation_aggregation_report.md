# Agent Validation Metrics Aggregation Report
**Total Fields Generated (Across Actions):** 5

## Failure Summary by Rule
| Rule/Check ID | Total Failures | % of Runs Affected | Affected Actions |
| :--- | :--- | :--- | :--- |
| Rule/Check 4 | 1 | 20.0% | `Wait for Change Request Status Update` (parameters_description) |
| Rule/Check 7 | 2 | 40.0% | `Wait for Change Request Status Update` (parameters_description), `Allow IP` (parameters_description) |
| Rule/Check 8 | 1 | 20.0% | `Wait for Change Request Status Update` (parameters_description) |
| Rule/Check Uncategorized | 3 | 40.0% | `List Templates` (parameters_description), `Block IP` (parameters_description) |

## Detailed Failures by Rule
### Rule/Check 4
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `Wait for Change Request Status Update`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: 1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file? Yes.
2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)? Yes.
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file? Yes.
4. If the original action has zero parameters defined, did the AI output the exact string: 'There are no parameters for this action' instead of a table? N/A.
5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description |? Yes.
6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table? Yes.
7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column? No. The 'Status' parameter has a default value of 'resolved' defined in the JSON settings, but this is not explicitly stated in the Description column.
8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes? Yes.

Actionable steps to fix:
- Update the Description column for the 'Status' parameter to explicitly include its default value (e.g., append 'Default value: resolved.').
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. Default value: resolved. |
```
---
### Rule/Check 7
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `Wait for Change Request Status Update`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: 1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file? Yes.
2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)? Yes.
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file? Yes.
4. If the original action has zero parameters defined, did the AI output the exact string: 'There are no parameters for this action' instead of a table? N/A.
5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description |? Yes.
6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table? Yes.
7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column? No. The 'Status' parameter has a default value of 'resolved' defined in the JSON settings, but this is not explicitly stated in the Description column.
8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes? Yes.

Actionable steps to fix:
- Update the Description column for the 'Status' parameter to explicitly include its default value (e.g., append 'Default value: resolved.').
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. Default value: resolved. |
```
---
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `Allow IP`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: Check 1: Passed. The table exclusively lists action-specific parameters.
Check 2: Passed. No integration-level parameters are leaked.
Check 3: Passed. All listed parameters exist in the JSON settings.
Check 4: Passed. N/A as there are parameters.
Check 5: Passed. The table is formatted correctly with the required headers.
Check 6: Passed. All action-specific parameters are documented.
Check 7: Failed. The default values for several parameters are defined in the JSON settings but are not explicitly stated in the Description column. Specifically, you must add 'Default: Standard' to the 'Template' description, 'Default: all' to the 'Source' description, and 'Default: ALL' to the 'Service' description.
Check 8: Passed. No conditional dependencies to document.
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Template | String | Yes | Specify the template for the change request. |
| Source | String | Yes | Specify a comma-separated list of sources for the allow rule. It can be an IP address, IP Set or special keyword like (all). |
| Service | String | Yes | Specify a comma-separated list of services that needs to be allowed. Values can have a look of {TCP/UDP}/{port} (tcp/80) or special reserved keyword (all). |
| Subject | String | No | Specify the subject for the change request. If nothing is provided action will put "Siemplify Allow IP request" in the subject. |
| Owner | String | No | Specify who should be the owner of the change request. If nothing is provided, the user that created the ticket will be the owner. |
| Due Date | String | No | Specify the due date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Expiration Date | String | No | Specify the expiration date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Custom Fields | String | No | Specify a JSON object containing information about all of the fields that need to be added to the change request. Note: this parameter has a priority over other fields |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Template | String | Yes | Specify the template for the change request. Default: Standard. |
| Source | String | Yes | Specify a comma-separated list of sources for the allow rule. It can be an IP address, IP Set or special keyword like (all). Default: all. |
| Service | String | Yes | Specify a comma-separated list of services that needs to be allowed. Values can have a look of {TCP/UDP}/{port} (tcp/80) or special reserved keyword (all). Default: ALL. |
| Subject | String | No | Specify the subject for the change request. If nothing is provided action will put "Siemplify Allow IP request" in the subject. |
| Owner | String | No | Specify who should be the owner of the change request. If nothing is provided, the user that created the ticket will be the owner. |
| Due Date | String | No | Specify the due date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Expiration Date | String | No | Specify the expiration date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Custom Fields | String | No | Specify a JSON object containing information about all of the fields that need to be added to the change request. Note: this parameter has a priority over other fields. |
```
---
### Rule/Check 8
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `Wait for Change Request Status Update`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: 1. Does the parameters table exclusively list the action-specific parameters defined in the JSON file? Yes.
2. Does the AI successfully avoid leaking any Integration-level parameters (like API, base URL or others)? Yes.
3. For every single parameter listed in the generated markdown table, does an exact, corresponding parameter definition exist in the provided JSON settings file? Yes.
4. If the original action has zero parameters defined, did the AI output the exact string: 'There are no parameters for this action' instead of a table? N/A.
5. Is the parameters description formatted precisely as a Markdown table with exactly these four column headers: | Parameter | Type | Mandatory | Description |? Yes.
6. Does the parameters description table document every single action-specific parameter declared in the provided JSON settings file, ensuring that zero required or optional action parameters are omitted from the Markdown table? Yes.
7. For every parameter listed in the Markdown table where the underlying JSON settings file or Python script defines a default value, enum choices, or specific formatting rules (such as CSV lists or integer ranges), are those default values and constraints explicitly stated in the Description column? No. The 'Status' parameter has a default value of 'resolved' defined in the JSON settings, but this is not explicitly stated in the Description column.
8. If the Python script or parameter metadata enforces conditional dependencies between parameters (e.g. 'Either Parameter A or Parameter B must be configured'), is this dependency explicitly documented within the specific parameter row description or notes? Yes.

Actionable steps to fix:
- Update the Description column for the 'Status' parameter to explicitly include its default value (e.g., append 'Default value: resolved.').
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Request ID | String | Yes | Specify the id of the request for which action needs to check the status. |
| Status | String | Yes | Specify a comma-separated list of change request statuses for which action should wait. Possible values: resolved, reconcile, open, check, implementation plan, implement, validate. Default value: resolved. |
```
---
### Rule/Check Uncategorized
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `Block IP`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: Check 7 failed. The default values for 'Template' (Standard), 'Source' (all), and 'Service' (ALL) are defined in the JSON settings but are not explicitly stated in the Description column of the drafted table. Please update the descriptions to include these default values (e.g., 'Default value is Standard.').
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Template | string | True | Specify the template for the change request. |
| Source | string | True | Specify a comma-separated list of sources for the block rule. It can be an IP address, IP Set or special keyword like (all). |
| Service | string | True | Specify a comma-separated list of services that needs to be blocked. Values can have a look of {TCP/UDP}/{port} (tcp/80) or special reserved keyword (all). |
| Subject | string | False | Specify the subject for the change request. If nothing is provided action will put “Siemplify Block IP request” in the subject. |
| Owner | string | False | Specify who should be the owner of the change request. If nothing is provided, the user that created the ticket will be the owner. |
| Due Date | string | False | Specify the due date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Expiration Date | string | False | Specify the expiration date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Custom Fields | string | False | Specify a JSON object containing information about all of the fields that need to be added to the change request. Note: this parameter has a priority over other fields |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| --- | --- | --- | --- |
| Template | string | True | Specify the template for the change request. Default value is Standard. |
| Source | string | True | Specify a comma-separated list of sources for the block rule. It can be an IP address, IP Set or special keyword like (all). Default value is all. |
| Service | string | True | Specify a comma-separated list of services that needs to be blocked. Values can have a look of {TCP/UDP}/{port} (tcp/80) or special reserved keyword (all). Default value is ALL. |
| Subject | string | False | Specify the subject for the change request. If nothing is provided action will put “Siemplify Block IP request” in the subject. |
| Owner | string | False | Specify who should be the owner of the change request. If nothing is provided, the user that created the ticket will be the owner. |
| Due Date | string | False | Specify the due date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Expiration Date | string | False | Specify the expiration date for the change request. Format: ISO 8601. Example: 2021-08-13T08:16:10Z. |
| Custom Fields | string | False | Specify a JSON object containing information about all of the fields that need to be added to the change request. Note: this parameter has a priority over other fields |
```
---
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `List Templates`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 1 Failure: Question 1: Passed. The table exclusively lists action-specific parameters.
Question 2: Passed. No integration-level parameters are leaked.
Question 3: Passed. All parameters in the table exist in the JSON settings.
Question 4: Passed. N/A as there are parameters.
Question 5: Passed. The table is formatted correctly with the required headers.
Question 6: Passed. All action-specific parameters are documented.
Question 7: Failed. The 'Filter Logic' parameter has a default value ('Equal') and enum choices ('Equal', 'Contains') defined in the JSON settings, but these are not explicitly stated in its Description column. Please update the description to include these details (e.g., 'Specify what filter logic should be applied. Available options: Equal, Contains. Default: Equal.').
Question 8: Passed. No conditional dependencies are enforced.
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Filter Logic | Drop-down | False | Specify what filter logic should be applied. |
| Filter Value | String | False | Specify what value should be used in the filter. If "Equal" is selected, action will try to find the exact match among record types and if "Contains" is selected, action will try to find items that contain that substring. If nothing is provided in this parameter, the filter will not be applied. |
| Max Templates To Return | String | False | Specify how many templates to return. Default: 50. |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Filter Logic | Drop-down | False | Specify what filter logic should be applied. Available options: Equal, Contains. Default: Equal. |
| Filter Value | String | False | Specify what value should be used in the filter. If "Equal" is selected, action will try to find the exact match among record types and if "Contains" is selected, action will try to find items that contain that substring. If nothing is provided in this parameter, the filter will not be applied. |
| Max Templates To Return | String | False | Specify how many templates to return. Must be greater than 0. Default: 50. |
```
---
**Integration:** `/usr/local/google/home/hmaor/develop/content-hub/content/response_integrations/google/algo_sec`  
**Action:** `List Templates`  
**Field:** `parameters_description`  
#### Validation Feedback Log:
```text
Attempt 2 Failure: Question 1: Passed. The table exclusively lists action-specific parameters.
Question 2: Passed. No integration-level parameters are leaked.
Question 3: Passed. All parameters in the table exist in the JSON settings.
Question 4: Passed. N/A as there are parameters.
Question 5: Passed. The table is formatted correctly with the required headers.
Question 6: Passed. All action-specific parameters are documented.
Question 7: Failed. The 'Max Templates To Return' parameter has a constraint defined in the Python script (it must be greater than 0), but this integer range constraint is not explicitly stated in its Description column. Please update the description to include this detail (e.g., 'Specify how many templates to return. Must be greater than 0. Default: 50.').
Question 8: Passed. No conditional dependencies are enforced.
```
#### Value Before (Failed Draft):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Filter Logic | Drop-down | False | Specify what filter logic should be applied. |
| Filter Value | String | False | Specify what value should be used in the filter. If "Equal" is selected, action will try to find the exact match among record types and if "Contains" is selected, action will try to find items that contain that substring. If nothing is provided in this parameter, the filter will not be applied. |
| Max Templates To Return | String | False | Specify how many templates to return. Default: 50. |
```
#### Value After (Corrected Output):
```text
| Parameter | Type | Mandatory | Description |
| :--- | :--- | :--- | :--- |
| Filter Logic | Drop-down | False | Specify what filter logic should be applied. Available options: Equal, Contains. Default: Equal. |
| Filter Value | String | False | Specify what value should be used in the filter. If "Equal" is selected, action will try to find the exact match among record types and if "Contains" is selected, action will try to find items that contain that substring. If nothing is provided in this parameter, the filter will not be applied. |
| Max Templates To Return | String | False | Specify how many templates to return. Must be greater than 0. Default: 50. |
```
---