# End-to-End Tests for Zscaler Integrations MCP Server

This directory contains comprehensive end-to-end (E2E) tests for the Zscaler Integrations MCP Server. These tests verify that the MCP server can properly handle requests from AI agents and return appropriate responses for various Zscaler services.

## Overview

The E2E tests use LangChain to create AI agents that interact with the MCP server, simulating real-world usage scenarios. The tests mock the Zscaler API to avoid making actual API calls while providing realistic test data.

## Test Architecture

### Key Components

1. **BaseE2ETest Class** (`utils/base_e2e_test.py`)
   - Provides shared infrastructure for all E2E tests
   - Manages MCP server lifecycle
   - Handles LangChain integration
   - Implements retry logic and success thresholds

2. **SharedTestServer Singleton**
   - Manages a single MCP server instance across all tests
   - Handles environment setup and cleanup
   - Provides mock API responses

3. **Test Files** (direct in `tests/e2e/`)
   - Individual test files for each Zscaler service
   - Follow consistent naming pattern: `Test{Service}ModuleE2E`
   - Use async test logic and assertion functions

## Test Modules

### ZIA (Zscaler Internet Access) Tests
**File:** `test_zia.py`

Tests for Zscaler Internet Access functionality:
- ✅ Cloud Applications (`test_get_cloud_applications`)
- ✅ URL Categories (`test_get_url_categories`)
- ✅ Static IPs (`test_get_static_ips`)
- ✅ VPN Credentials (`test_get_vpn_credentials`)
- ✅ Geo Locations (`test_get_geo_locations`)
- ✅ Network App Groups (`test_get_network_app_groups`)
- ✅ IP Destination Groups (`test_get_ip_destination_groups`)
- ✅ IP Source Groups (`test_get_ip_source_groups`)
- ✅ Cloud Firewall Rules (`test_get_cloud_firewall_rules`)
- ✅ Auth Exempt URLs (`test_get_auth_exempt_urls`)

### ZPA (Zscaler Private Access) Tests
**File:** `test_zpa.py`

Tests for Zscaler Private Access functionality:
- ✅ Application Segments (`test_get_app_segments`)
- ✅ Server Groups (`test_get_server_groups`)
- ✅ App Connector Groups (`test_get_app_connector_groups`)
- ✅ Application Servers (`test_get_application_servers`)
- ✅ Segment Groups (`test_get_segment_groups`)
- ✅ Service Edge Groups (`test_get_service_edge_groups`)
- ✅ Access Policy Rules (`test_get_access_policy_rules`)
- ✅ Access Timeout Rules (`test_get_access_timeout_rules`)
- ✅ Access Forwarding Rules (`test_get_access_forwarding_rules`)
- ✅ Access Isolation Rules (`test_get_access_isolation_rules`)
- ✅ Access App Protection Rules (`test_get_access_app_protection_rules`)

### ZDX (Zscaler Digital Experience) Tests
**File:** `test_zdx.py`

Tests for Zscaler Digital Experience functionality:
- ✅ Applications (`test_get_applications`)
- ✅ Active Devices (`test_get_active_devices`)
- ✅ Alerts (`test_get_alerts`)
- ✅ Deep Traces (`test_get_deep_traces`)
- ✅ Software Inventory (`test_get_software_inventory`)
- ✅ Application Metrics (`test_get_application_metrics`)
- ✅ Application Scores (`test_get_application_scores`)
- ✅ Application Users (`test_get_application_users`)
- ✅ Administration Data (`test_get_administration_data`)

### ZCC (Zscaler Client Connector) Tests
**File:** `test_zcc.py`

Tests for Zscaler Client Connector functionality:
- ✅ Devices (`test_get_devices`)
- ✅ Device Details (`test_get_device_details`)
- ✅ Download Devices (`test_download_devices`)
- ✅ Devices by Status (`test_get_devices_by_status`)
- ✅ Devices by User (`test_get_devices_by_user`)
- ✅ Device Statistics (`test_get_device_statistics`)

### ZIdentity Tests
**File:** `test_zidentity.py`

Tests for Zscaler Identity functionality:
- ✅ Users (`test_get_users`)
- ✅ Groups (`test_get_groups`)
- ✅ User Details (`test_get_user_details`)
- ✅ Group Details (`test_get_group_details`)
- ✅ Users by Department (`test_get_users_by_department`)
- ✅ Group Members (`test_get_group_members`)
- ✅ User Statistics (`test_get_user_statistics`)
- ✅ Group Statistics (`test_get_group_statistics`)

## Prerequisites

### Required Environment Variables

```bash
# Required for OpenAI API access
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Custom OpenAI endpoint
export OPENAI_BASE_URL="https://your-custom-endpoint.com/v1"
```

### Required Dependencies

Install the E2E test dependencies:

```bash
# Install E2E dependencies
pip install -e ".[e2e]"

# Or install manually
pip install pytest-asyncio>=0.21.0
pip install langchain-openai>=0.3.28
pip install mcp-use[search]>=1.3.7
```

## Running Tests

### Using the Test Runner Script

The easiest way to run E2E tests is using the provided test runner:

```bash
# Run all E2E tests with default settings
python tests/e2e/run_e2e_tests.py

# Quick test run (fewer runs, lower threshold)
python tests/e2e/run_e2e_tests.py --quick

# Run tests with specific models
python tests/e2e/run_e2e_tests.py --models "gpt-4o-mini,gpt-4o"

# Run tests with custom success threshold
python tests/e2e/run_e2e_tests.py --threshold 0.8

# Run tests with more runs per test
python tests/e2e/run_e2e_tests.py --runs 5

# Run specific test module
python tests/e2e/run_e2e_tests.py --test-path tests/e2e/test_zia.py

# Verbose output
python tests/e2e/run_e2e_tests.py --verbose

# List available test modules
python tests/e2e/run_e2e_tests.py --list-tests
```

### Using pytest Directly

You can also run tests directly with pytest:

```bash
# Run all E2E tests
pytest tests/e2e/ -m e2e -v

# Run specific module
pytest tests/e2e/test_zia.py -m e2e -v

# Run with debug output
pytest tests/e2e/ -m e2e -v -s --log-cli-level=DEBUG

# Run single test
pytest tests/e2e/test_zia.py::TestZIAModuleE2E::test_get_cloud_applications -v
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `OPENAI_BASE_URL` | None | Custom OpenAI endpoint URL |
| `MODELS_TO_TEST` | `gpt-4o-mini,gpt-4o` | Comma-separated list of models |
| `RUNS_PER_TEST` | `2` | Number of times to run each test |
| `SUCCESS_THRESHOLD` | `0.1` | Success rate threshold (0.0-1.0) |

### Test Runner Options

| Option | Description |
|--------|-------------|
| `--test-path` | Path to specific test file or directory |
| `--models` | Comma-separated list of models to test |
| `--runs` | Number of runs per test |
| `--threshold` | Success threshold for tests |
| `--verbose` | Enable verbose output |
| `--quick` | Quick test mode (fewer runs, lower threshold) |
| `--list-tests` | List available test modules |

## Test Structure

Each test follows this pattern:

```python
def test_functionality(self):
    async def test_logic():
        # 1. Set up mock responses
        fixtures = [
            {
                "operation": "operation_name",
                "validator": lambda kwargs: True,
                "response": {
                    "status_code": 200,
                    "body": {"data": "test_data"}
                },
            },
        ]

        # 2. Set up mock API
        self._mock_api_instance.service.method.side_effect = (
            self._create_mock_api_side_effect(fixtures)
        )

        # 3. Define prompt
        prompt = "Your test prompt here"

        # 4. Run agent
        return await self._run_agent_stream(prompt)

    def assertions(tools, result):
        # 5. Verify results
        self.assertGreaterEqual(len(tools), 1)
        result_lower = result.lower()
        self.assertTrue("expected_content" in result_lower)

    # 6. Run with retries
    self.run_test_with_retries(
        "test_name",
        test_logic,
        assertions,
    )
```

## Mock Data Strategy

The tests use realistic mock data that matches actual Zscaler API responses:

```python
# Example mock response for cloud applications
{
    "applications": [
        {
            "id": "app-001",
            "name": "Salesforce",
            "category": "Business",
            "risk_level": "Low",
            "status": "Active",
            "usage_count": 150
        }
    ]
}
```

## Success Thresholds

Tests use success thresholds to account for LLM variability:

- **Default threshold**: 0.1 (10% success rate required)
- **Quick mode**: 0.5 (50% success rate required)
- **Custom threshold**: Configurable via `--threshold` option

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

2. **Server Connection Issues**
   - Check that port 8000 is available
   - Verify server starts correctly in test environment

3. **Test Failures Due to LLM Variability**
   - Adjust success threshold: `--threshold 0.5`
   - Use more specific prompts
   - Add more flexible assertions

4. **Mock Issues**
   - Verify mock setup in test logic
   - Check that mock methods match actual API methods

### Debug Mode

```bash
# Run with debug output
python tests/e2e/run_e2e_tests.py --verbose

# Run single test with verbose output
pytest tests/e2e/test_zia.py::TestZIAModuleE2E::test_get_cloud_applications -v -s
```

## Performance Considerations

- E2E tests are slower than unit tests (due to LLM API calls)
- Consider using faster models for development (`gpt-4o-mini`)
- Use appropriate success thresholds to balance reliability and speed
- Run tests in parallel when possible (but be mindful of API rate limits)

## Adding New Tests

To add new tests:

1. **Create test function** in appropriate module file
2. **Set up mock data** with realistic API responses
3. **Define test logic** with async function
4. **Write assertions** to verify expected behavior
5. **Use retry mechanism** for reliability

Example:

```python
def test_new_functionality(self):
    async def test_logic():
        fixtures = [
            {
                "operation": "new_operation",
                "validator": lambda kwargs: True,
                "response": {
                    "status_code": 200,
                    "body": {"new_data": "test_value"}
                },
            },
        ]

        self._mock_api_instance.service.new_method.side_effect = (
            self._create_mock_api_side_effect(fixtures)
        )

        prompt = "Test the new functionality"
        return await self._run_agent_stream(prompt)

    def assertions(tools, result):
        self.assertGreaterEqual(len(tools), 1)
        result_lower = result.lower()
        self.assertTrue("test_value" in result_lower)

    self.run_test_with_retries(
        "test_new_functionality",
        test_logic,
        assertions,
    )
```

## Test Results

Test results are saved to `test_results.json` in the project root, containing:

- Test execution details
- Success/failure rates
- Performance metrics
- Error information

## Future Enhancements

1. **Add More Test Modules**: Additional Zscaler services
2. **Enhanced Mocking**: More sophisticated API response mocking
3. **Performance Testing**: Measure response times and throughput
4. **Integration Testing**: Test with real Zscaler environments
5. **CI/CD Integration**: Add E2E tests to automated pipelines

## Support

For issues with E2E tests:

1. Check the troubleshooting section above
2. Review test logs for specific error messages
3. Verify environment setup and dependencies
4. Check OpenAI API key and rate limits
5. Review mock data setup in failing tests