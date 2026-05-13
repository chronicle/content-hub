# Log File Structural Requirements

This document outlines the mandatory structural requirements for log files (`*_log.json`) used by the `run_parser_validations.py` script.

## Required Structure

All log files must follow the nested JSON format described below. This structure is required to support advanced validation features and metadata passing.

```json
{
  "create_time": "YYYY-MM-DDTHH:MM:SS.ssssssZ",
  "raw_logs": {
    "start_time": "YYYY-MM-DDTHH:MM:SS.ssssssZ",
    "entries": [
      {
        "data": "The actual raw log string",
        "collection_time": "YYYY-MM-DDTHH:MM:SS.ssssssZ" (optional)
      }
    ]
  }
}
```

### Field Definitions

*   **`create_time`** (Root): The timestamp indicating when the log batch was generated.
*   **`raw_logs.start_time`**: The start timestamp for the collection window of these logs.
*   **`raw_logs.entries`**: A list of objects containing the log data.
    *   **`data`**: **(Mandatory)** The raw string of the log message to be parsed.
    *   **`collection_time`**: (Optional) The specific timestamp when this individual log entry was collected.

---

## Fail-Fast Validation Policy

To ensure data integrity and immediate feedback, the validation script employs a strict **Fail-Fast** policy:

1.  **Strict Enforcement**: Every `*_log.json` file is validated against the above schema before any parsing occurs.
2.  **Immediate Termination**: If a file is missing required fields (like `create_time` or `raw_logs.entries`) or has an invalid structure, the script will log a specific error and **exit immediately** with code `1`.
3.  **Process Halt**: The script uses `os._exit()` to bypass all standard exception handling, ensuring no partial results are shown and the user is forced to correct the data before proceeding.

---

## Troubleshooting Structural Errors

If the script fails with a structural error, refer to the table below for common fixes:

| Error Message | Solution |
| :--- | :--- |
| `Missing 'create_time' at the root` | Add a `"create_time"` key at the top level of your JSON file. |
| `Missing 'raw_logs' at the root` | Ensure your logs are nested under a `"raw_logs"` key. |
| `'raw_logs' is missing 'entries'` | Ensure the `"raw_logs"` object contains the `"entries"` list. |
| `Entry at index X is missing 'data' field` | Check that every object in the `"entries"` list has a `"data"` key with the log string. |
