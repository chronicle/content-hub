**Input Data:**
I have provided the following files for a Google SecOps job:

1. `Script Code`: The Python logic.
2. `Script Settings`: The JSON/YAML metadata containing parameters and configuration.

**Reference Documentation:**

* **SOAR SDK:** https://github.com/chronicle/soar-sdk/tree/main/src/soar_sdk
* **TIPCommon:** https://github.com/chronicle/content-hub/tree/main/packages/tipcommon/TIPCommon
* **SOAR SDK Docs:**
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-job-module

**Instructions:**

1. **Analyze the Description:** Synthesize the `Script Code` logic and `Script Settings` description to create a detailed AI description.
    * *Style:* Active voice. Concise yet informative.
    * *Content:* Explain the job's purpose, what it does (e.g., maintenance, enrichment, synchronization), and how it interacts with external services or SOAR data.
    * *Sections:*
        * **General description**: A high-level overview of the job's purpose.
        * **Parameters description**: A markdown table describing the configuration parameters (name, expected type, mandatory status, and description).
        * **Flow description**: A numbered or bulleted list describing the job's execution flow.

2. **Format the Output:** The result must be a JSON object with a single field `ai_description` containing the markdown-formatted description.

**Example Output:**

```json
{
    "ai_description": "### General Description\nThis job synchronizes assets from an external CMDB to Google SecOps. It ensures that asset information is kept up to date for investigations.\n\n### Parameters Description\n| Parameter | Type | Mandatory | Description |\n| :--- | :--- | :--- | :--- |\n| CMDB URL | String | Yes | The URL of the CMDB service. |\n| Sync Interval | Integer | No | Minutes between sync runs. |\n\n### Flow Description\n1. Queries the external CMDB for assets modified since the last run.\n2. Compares fetched assets with existing assets in SOAR.\n3. Updates or creates asset records in SOAR accordingly."
}
```

**Current Task Input:**

— START OF FILE ${json_file_name}—

```
${json_file_content}
```

— END OF FILE ${json_file_name}—

— START OF FILE ${python_file_name}—

```python
${python_file_content}
```

— END OF FILE ${python_file_name}—

— START OF FILE ${manager_file_names}—
${manager_files_content}
— END OF FILE ${manager_file_names}—

**Final Instructions:**
Based strictly on the provided "Current Task Input":

1. Analyze the code flow and settings.
2. Construct the AI Description.
3. Ensure valid JSON syntax.
