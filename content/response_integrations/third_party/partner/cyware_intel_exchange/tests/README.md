# Cyware Intel Exchange Integration Tests

This directory contains integration tests for the Cyware Intel Exchange integration, following the standard integration testing framework pattern.

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py                 # Pytest configuration and fixtures
├── common.py                   # Common test utilities and constants
├── config.json                 # Test configuration (credentials, URLs)
├── core/                       # Core test infrastructure
│   ├── __init__.py
│   ├── product.py             # CywareIntelExchange product mock
│   └── session.py             # Mock session for API routing
├── mocks/                      # Mock data
│   ├── __init__.py
│   └── mock_responses.json    # Mock API responses
├── test_actions/              # Action tests
│   ├── __init__.py
│   ├── test_ping.py
│   ├── test_add_iocs_to_allowed_list.py
│   ├── test_remove_iocs_from_allowed_list.py
│   ├── test_get_allowed_iocs.py
│   ├── test_add_note_to_iocs.py
│   ├── test_create_intel_in_cyware_intel_exchange.py
│   ├── test_get_ioc_details.py
│   ├── test_manage_tags_in_iocs.py
│   └── test_mark_iocs_false_positive.py
└── test_defaults/             # Default parameter tests
    └── __init__.py
```

## Test Framework

### Core Components

#### `core/product.py`
Defines the `CywareIntelExchange` dataclass that manages mock responses for different API endpoints. Each action can set specific response data through this class.

#### `core/session.py`
Implements `CywareSession` which extends `MockSession` to route API requests to appropriate mock handlers. Uses decorators to define endpoint patterns and responses.

#### `conftest.py`
Contains pytest fixtures:
- `cyware`: Returns a `CywareIntelExchange` instance for configuring mock responses
- `script_session`: Mocks the HTTP session for API calls
- `sdk_session`: Mocks the SDK session

#### `common.py`
Provides common utilities:
- Path constants for configuration and mock files
- Pre-loaded mock data from `mock_responses.json`

### Mock Data

The `mocks/mock_responses.json` file contains sample API responses for all endpoints:
- `bulk_lookup`: IOC lookup responses
- `add_allowed_iocs`: Add IOCs to allowlist responses
- `remove_allowed_iocs`: Remove IOCs from allowlist responses
- `get_allowed_iocs`: Get allowed IOCs responses
- `add_note`: Add note to IOC responses
- `create_intel`: Create intel responses
- `quick_intel_status`: Quick intel status responses
- `get_ioc_details`: Get IOC details responses
- `add_tags`: Add tags responses
- `remove_tags`: Remove tags responses
- `mark_false_positive`: Mark false positive responses

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_actions/test_ping.py
```

### Run Specific Test
```bash
pytest tests/test_actions/test_ping.py::TestPing::test_ping_success
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Live API (if configured)
```bash
USE_LIVE_API=true pytest tests/
```

## Writing New Tests

### Basic Test Structure

```python
from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyware_intel_exchange.actions import Your_Action
from cyware_intel_exchange.tests.common import CONFIG_PATH, MOCK_YOUR_DATA
from cyware_intel_exchange.tests.core.product import CywareIntelExchange
from cyware_intel_exchange.tests.core.session import CywareSession

DEFAULT_PARAMETERS = {
    "Parameter1": "value1",
    "Parameter2": "value2",
}


class TestYourAction:
    @set_metadata(integration_config_file_path=CONFIG_PATH, parameters=DEFAULT_PARAMETERS)
    def test_your_action_success(
        self,
        script_session: CywareSession,
        action_output: MockActionOutput,
        cyware: CywareIntelExchange,
    ) -> None:
        # Set mock response
        cyware.your_response = MOCK_YOUR_DATA
        
        # Execute action
        Your_Action.main()
        
        # Assertions
        assert len(script_session.request_history) >= 1
        assert "expected message" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
```

### Adding New Mock Responses

1. Add the mock data to `mocks/mock_responses.json`
2. Import it in `common.py`
3. Add a property to `CywareIntelExchange` in `core/product.py`
4. Add a route handler in `CywareSession` in `core/session.py`

## Test Coverage

Current test coverage includes:
- ✅ Ping
- ✅ Add IOCs to Allowed List
- ✅ Remove IOCs from Allowed List
- ✅ Get Allowed IOCs
- ✅ Add Note to IOCs
- ✅ Create Intel in Cyware Intel Exchange
- ✅ Get IOC Details
- ✅ Manage Tags in IOCs
- ✅ Mark IOCs False Positive

## Configuration

The `config.json` file contains test configuration:
```json
{
    "Base URL": "https://test.cyware.com",
    "Access ID": "test_access_id_12345",
    "Secret Key": "test_secret_key_67890",
    "Verify SSL": "false"
}
```

**Note**: These are test credentials and should not be used in production.

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Mock Data**: Use realistic mock data that represents actual API responses
3. **Assertions**: Verify both success and failure scenarios
4. **Request History**: Check that the correct API endpoints were called
5. **Output Validation**: Validate output messages, result values, and execution states
6. **Parameters**: Use `DEFAULT_PARAMETERS` for common test parameters
7. **Naming**: Follow the naming convention `test_<action_name>_<scenario>`

## Troubleshooting

### Tests Failing with Import Errors
Ensure the integration is properly installed and the Python path includes the integration directory.

### Mock Responses Not Working
Check that:
1. The endpoint pattern in `session.py` matches the actual API call
2. The mock data is properly loaded in `common.py`
3. The fixture is setting the response correctly

### Request History Empty
Verify that:
1. The `script_session` fixture is being used
2. The action is actually making HTTP requests
3. The session mocking is properly configured in `conftest.py`
