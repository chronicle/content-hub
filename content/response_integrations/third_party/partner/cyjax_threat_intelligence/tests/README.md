# CYJAX Threat Intelligence - Test Suite

This directory contains the test suite for the CYJAX Threat Intelligence integration, following the patterns established in cyware_intel_exchange and greynoise integrations.

## Structure

```
tests/
├── __init__.py
├── README.md
├── config.json                 # Test configuration
├── common.py                   # Common test utilities and constants
├── conftest.py                 # Pytest fixtures and configuration
├── core/
│   ├── __init__.py
│   ├── product.py             # Mock product class
│   └── session.py             # Mock API session
├── mocks/
│   ├── __init__.py
│   └── mock_responses.json    # Mock API responses
└── test_actions/
    ├── __init__.py
    ├── test_ping.py
    ├── test_domain_monitor.py
    ├── test_enrich_iocs.py
    └── test_list_data_breaches.py
```

## Running Tests

### Prerequisites

- Python 3.x
- pytest
- integration_testing framework
- soar_sdk

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

## Test Structure

### Basic Test Pattern

```python
from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyjax_threat_intelligence.actions import your_action
from cyjax_threat_intelligence.tests.common import CONFIG_PATH, MOCK_YOUR_DATA
from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence
from cyjax_threat_intelligence.tests.core.session import CyjaxSession

DEFAULT_PARAMETERS = {
    "Parameter1": "value1",
    "Parameter2": "value2",
}

class TestYourAction:
    """Test class for Your Action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_your_action_success(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test successful operation."""
        cyjax.your_response = MOCK_YOUR_DATA
        
        your_action.main()
        
        assert len(script_session.request_history) >= 1
        assert "expected message" in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
```

### Testing with Entities

For actions that process entities (like Enrich IOCs):

```python
DEFAULT_ENTITIES = [
    {"identifier": "1.1.1.1", "entity_type": "ADDRESS", "additional_properties": {}},
    {"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}},
]

@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=DEFAULT_ENTITIES,
)
def test_with_entities(
    self,
    script_session: CyjaxSession,
    action_output: MockActionOutput,
    cyjax: CyjaxThreatIntelligence,
) -> None:
    """Test with entities."""
    cyjax.enrich_iocs_response = MOCK_ENRICH_IOCS_RESPONSE
    
    enrich_iocs.main()
    
    assert action_output.results.result_value is True
```

### Testing API Failures

```python
@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_api_failure(
    self,
    script_session: CyjaxSession,
    action_output: MockActionOutput,
    cyjax: CyjaxThreatIntelligence,
) -> None:
    """Test with API failure."""
    cyjax.should_fail_ping = True
    
    ping.main()
    
    assert action_output.results.result_value is False
    assert action_output.results.execution_state.value == 1
```

## Mock Framework

### Product Mock (core/product.py)

The `CyjaxThreatIntelligence` class holds mock response data:

```python
@dataclasses.dataclass(slots=True)
class CyjaxThreatIntelligence:
    ping_response: Optional[List[SingleJson]] = None
    domain_monitor_response: Optional[List[SingleJson]] = None
    enrich_iocs_response: Optional[SingleJson] = None
    list_data_breaches_response: Optional[List[SingleJson]] = None
    
    # Failure flags
    should_fail_ping: bool = False
    should_fail_domain_monitor: bool = False
    should_fail_enrich_iocs: bool = False
    should_fail_list_data_breaches: bool = False
```

### Session Mock (core/session.py)

The `CyjaxSession` class routes API requests to mock responses:

```python
@router.get(r"/indicator-of-compromise$")
def ping_endpoint(self, request: MockRequest) -> MockResponse:
    try:
        return MockResponse(content=self._product.get_ping(), status_code=200)
    except Exception as e:
        return MockResponse(content={"error": str(e)}, status_code=400)
```

## Adding New Tests

### 1. Add Mock Response Data

Add to `mocks/mock_responses.json`:

```json
{
  "your_endpoint": {
    "data": "sample response"
  }
}
```

### 2. Import in common.py

```python
MOCK_YOUR_ENDPOINT: SingleJson = MOCK_DATA.get("your_endpoint")
```

### 3. Add to Product Mock

In `core/product.py`:

```python
your_endpoint_response: Optional[SingleJson] = None
should_fail_your_endpoint: bool = False

def get_your_endpoint(self) -> SingleJson:
    if self.should_fail_your_endpoint:
        raise Exception("Failed to call your endpoint")
    if self.your_endpoint_response is not None:
        return self.your_endpoint_response
    return {}
```

### 4. Add Route Handler

In `core/session.py`:

```python
@router.get(r"/your-endpoint-path")
def your_endpoint(self, request: MockRequest) -> MockResponse:
    try:
        return MockResponse(content=self._product.get_your_endpoint(), status_code=200)
    except Exception as e:
        return MockResponse(content={"error": str(e)}, status_code=400)
```

### 5. Create Test File

Create `test_actions/test_your_action.py` following the pattern above.

## Test Coverage

Current test coverage includes:

- ✅ Ping (3 test cases)
  - Success
  - API failure
  - Empty response
  
- ✅ Enrich IOCs (5 test cases)
  - Success with multiple entities
  - No entities
  - API failure
  - Single entity
  - Empty response
  
- ✅ Domain Monitor (5 test cases)
  - Success
  - API failure
  - Without Since parameter
  - Empty response
  - With Until parameter
  
- ✅ List Data Breaches (6 test cases)
  - Success
  - API failure
  - Without Since parameter
  - Empty response
  - With Until parameter
  - Empty query

## Best Practices

1. **Use descriptive test names** - Test names should clearly indicate what is being tested
2. **Add docstrings** - Each test should have a docstring explaining its purpose
3. **Test both success and failure** - Always include positive and negative test cases
4. **Test edge cases** - Empty responses, missing parameters, etc.
5. **Use DEFAULT_PARAMETERS** - Define parameter sets at the class level for reusability
6. **Check request history** - Verify API calls were made: `assert len(script_session.request_history) >= 1`
7. **Verify execution state** - Check both result_value and execution_state.value
8. **Use meaningful assertions** - Assert on specific parts of the output message

## Fixtures

### cyjax
Returns a `CyjaxThreatIntelligence` instance for setting mock responses.

### script_session
Returns a `CyjaxSession` instance that intercepts HTTP requests.

### action_output
Returns a `MockActionOutput` instance containing the action's results.

## Configuration

Test configuration is stored in `config.json`:

```json
{
    "API Token": "test_api_token",
    "Verify SSL": "false"
}
```

## Troubleshooting

### ImportError: No module named 'integration_testing'

Ensure the integration_testing framework is installed in your environment.

### Tests not finding entities

Make sure entities are properly formatted with `identifier`, `entity_type`, and `additional_properties` fields.

### Mock responses not being used

Verify that you're setting the response on the `cyjax` fixture before calling the action's `main()` function.
