**Input Data:**
I have provided the following files for a Google SecOps connector:

1. `Script Code`: The Python logic.
2. `Script Settings`: The JSON/YAML metadata containing parameters and configuration.

**Reference Documentation:**

* **SOAR SDK:** https://github.com/chronicle/soar-sdk/tree/main/src/soar_sdk
* **TIPCommon:** https://github.com/chronicle/content-hub/tree/main/packages/tipcommon/TIPCommon
* **SOAR SDK Docs:**
    * https://docs.cloud.google.com/chronicle/docs/soar/reference/siemplify-connectors-module

**Instructions:**

1. **Analyze the Description:** Synthesize the `Script Code` logic and `Script Settings` description to create a detailed AI description.
    * *Style:* Active voice. Concise yet informative.
    * *Content:* Explain the connector's purpose, what kind of data it pulls (e.g., alerts, logs, events), and from which external service.
    * *Sections:*
        * **General description**: A high-level overview of the connector's purpose and the service it integrates with.
        * **Parameters description**: A markdown table describing the configuration parameters (name, expected type, mandatory status, and description).
        * **Flow description**: A numbered or bulleted list describing the data ingestion flow (how it connects, what it fetches, how it filters, and how it creates cases/alerts in SOAR).

2. **Format the Output:** The result must be a JSON object with a single field `ai_description` containing the markdown-formatted description.

**Example Output:**

```json
{
    "ai_description": "### General Description\nThis connector fetches alerts from VirusTotal and creates cases in Google SecOps. It allows monitoring for malicious activity seen globally.\n\n### Parameters Description\n| Parameter | Type | Mandatory | Description |\n| :--- | :--- | :--- | :--- |\n| API Key | String | Yes | Your VirusTotal API key. |\n| Threshold | Integer | No | Minimum score to fetch. |\n\n### Flow Description\n1. Connects to VirusTotal API using the provided API Key.\n2. Queries for recent alerts matching the configured threshold.\n3. Maps each alert to a Google SecOps case format.\n4. Ingests cases into the system."
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
