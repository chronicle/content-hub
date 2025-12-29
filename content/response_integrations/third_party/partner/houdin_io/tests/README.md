# Houdin.io Integration Tests

This directory contains comprehensive tests for the Houdin.io integration, focusing on the scan and polling functionality. Tests are based on the actual Houdin API response format as shown in the `Scan Artifact.yaml` file.

## Test Files

### `test_houdin_manager.py`
Comprehensive unit tests for the `HoudinManager` class covering:

#### Core Functionality Tests:
- **Initialization**: Testing proper setup of the HoudinManager
- **cleanScanOn Method**: Input validation and cleaning for scanner selection
- **launch_scan Method**: Testing scan initiation with various parameters
- **poll_scan_result Method**: Testing result polling with different scenarios

#### Scan Launch Tests:
- ✅ Successful scan launch with basic parameters
- ✅ Scan launch with specific scanner selection (`scanOn` parameter)
- ✅ Handling of empty or invalid `scanOn` parameters
- ✅ Server error retry logic (500 errors)
- ✅ Error handling for missing scan IDs
- ✅ Network and HTTP error handling

#### Polling Tests:
- ✅ Successful result retrieval
- ✅ Handling of pending status (202) with retries
- ✅ Custom retry parameters (max_retries, retry_interval)
- ✅ Maximum retries exceeded scenarios
- ✅ Network and HTTP error handling during polling

#### Integration Workflow Tests:
- ✅ Complete scan workflow (launch → poll → result)
- ✅ Threat detection scenarios using real response format
- ✅ Mixed scanner results
- ✅ Real Houdin response structures from YAML examples

### `test_demo_scenarios.py`
Practical demonstration tests using the `test.com` artifact with **real Houdin API format**:

#### Realistic Scenarios:
- ✅ Basic scan workflow with `test.com` using actual response structure
- ✅ VT-only scanning demonstrating scanner selection
- ✅ Malicious result detection using `malicious.com` example from YAML
- ✅ Scanner validation with all available scanners

#### Real Response Structure:
Tests demonstrate the actual Houdin response format including:
```json
{
  "scanID": "houdin-12345678-abcd-4321-test-com",
  "clientID": "demo_client_id", 
  "status": "Done",
  "artifact": "test.com",
  "scanOn": ["vt", "urlscan"],
  "scanResults": {
    "vt": {
      "result": {
        "data": {
          "attributes": {
            "last_analysis_stats": {
              "malicious": 0,
              "harmless": 85
            },
            "reputation": 0
          }
        }
      }
    },
    "urlscan": {
      "result": {
        "results": [{
          "page": {
            "domain": "test.com",
            "status": "200"
          }
        }]
      }
    }
  },
  "scanTime": "2025-08-01T10:00:00Z"
}
```

## Available Scanners

Based on the YAML configuration, the integration supports:
- `vt` - VirusTotal
- `urlscan` - URLScan.io  
- `alienvault` - AlienVault OTX
- `abuseipdb` - AbuseIPDB
- `triage` - Triage Malware Analysis
- `mesmer` - Mesmer Intelligence
- `servicenow` - ServiceNow
- `custom_*` - Custom scanners (any scanner name starting with "custom_")

## Running the Tests

```bash
# Run all tests
python -m pytest tests/test_houdin_manager.py tests/test_demo_scenarios.py -v

# Run just HoudinManager tests
python -m pytest tests/test_houdin_manager.py -v

# Run demo scenarios with test.com
python -m pytest tests/test_demo_scenarios.py -v

# Run specific test
python -m pytest tests/test_houdin_manager.py::TestHoudinManager::test_launch_scan_success -v

# Run with coverage
python -m pytest tests/test_houdin_manager.py --cov=core.Houdin
```

## Key Test Features

✅ **Real API Format**: Tests use the actual Houdin response structure from production examples  
✅ **Concise & Focused**: Streamlined tests based on the real YAML examples  
✅ **Complete Coverage**: All major functionality tested with realistic scenarios  
✅ **Error Handling**: Comprehensive error and edge case testing  
✅ **Scanner Validation**: Tests all available scanners from the YAML configuration  

## Test Coverage

The tests cover:
- ✅ **API Integration**: Mocked HTTP requests matching real Houdin API
- ✅ **Error Handling**: Network errors, HTTP errors, API errors
- ✅ **Retry Logic**: Server errors, polling delays, timeouts
- ✅ **Input Validation**: Parameter cleaning and validation
- ✅ **Response Parsing**: Real JSON structures from Houdin API
- ✅ **Edge Cases**: Empty responses, missing fields, invalid data

## Test Artifacts

### Primary Test Artifact
- **test.com**: Used as the primary test domain for clean scanning scenarios
  - Known safe domain for testing
  - Produces realistic clean results across scanners
  - Used in YAML configuration as default value

### Additional Test Scenarios
- **malicious.com**: Used for threat detection testing (from YAML example)
  - Realistic malicious results with multiple scanner detections
  - Demonstrates Mesmer tagging and VT reputation scoring
  - Shows real-world threat intelligence response structure

## Example Usage

The tests demonstrate the exact Houdin API usage:

```python
# Initialize the manager
manager = HoudinManager(api_key="your_api_key")

# Launch a scan (returns real Houdin scanID format)
scan_id, status = manager.launch_scan("test.com", ["vt", "urlscan"])

# Poll for results (returns real Houdin response structure)
result = manager.poll_scan_result(scan_id)

# Access results using real API format
vt_malicious = result["scanResults"]["vt"]["result"]["data"]["attributes"]["last_analysis_stats"]["malicious"]
urlscan_domain = result["scanResults"]["urlscan"]["result"]["results"][0]["page"]["domain"]
scan_status = result["status"]  # "Done" when complete
```

## Response Format Validation

All tests validate against the real Houdin API response format including:
- Proper `scanResults` structure with nested `result` objects
- Correct scanner-specific response formats (VT, URLScan, Mesmer, etc.)
- Real scanID formats (e.g., `houdin-12345678-abcd-4321-test-com`)
- Actual status values (`"Done"` for completed scans)
- Proper timestamp formats and field names
