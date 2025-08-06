# End-to-End Tests for Zscaler MCP Server

This directory contains end-to-end (E2E) tests for the Zscaler MCP Server that use LangChain and AI agents to test the server's functionality in a realistic manner.

## Overview

The E2E tests simulate real-world usage scenarios where an AI agent interacts with the Zscaler MCP Server to perform various operations. These tests verify that:

1. The MCP server responds correctly to agent requests
2. Tools are properly registered and accessible
3. The agent can successfully complete tasks using the available tools
4. Responses contain expected information

## Architecture

### Base Test Class (`base_e2e_test.py`)

The `BaseE2ETest` class provides:

- **Shared Server Management**: A singleton `SharedTestServer` that manages a single MCP server instance across all tests
- **LangChain Integration**: Uses `langchain_openai` and `mcp-use` for AI agent testing
- **Mock API**: Mocks the Zscaler API to avoid real API calls during testing
- **Multi-Model Testing**: Tests against different LLM models (GPT-4o-mini, GPT-4o)
- **Success Thresholds**: Requires 70% success rate across multiple runs
- **Retry Logic**: Runs each test multiple times to account for LLM variability
- **Direct Server Testing**: Tests that bypass the agent to avoid pickle limitations

### Test Structure

Each test module follows this pattern:

```python
@pytest.mark.e2e
class TestZIAModuleE2E(BaseE2ETest):
    def test_get_cloud_applications(self):
        async def test_logic():
            # Mock API responses
            # Set up test data
            prompt = "List the top 3 cloud applications"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            # Verify expected behavior
            self.assertGreaterEqual(len(tools), 1)
            # Check result content

        self.run_test_with_retries(
            "test_get_cloud_applications",
            test_logic,
            assertions,
        )
```

## Setup

### Prerequisites

1. Install the E2E dependencies:
   ```bash
   pip install -e ".[e2e]"
   ```

2. **For Testing Without API Key (Mock LLM):**
   ```bash
   # Run E2E tests with mock LLM (no API key required)
   pytest --run-e2e tests/e2e/
   ```

3. **For Full E2E Tests (Requires OpenAI API Key):**
   ```bash
   # Set up environment variables
   export OPENAI_API_KEY="your-openai-api-key"
   export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional
   ```

### Configuration

You can configure the E2E tests using environment variables:

- `MODELS_TO_TEST`: Comma-separated list of models to test (default: "gpt-4o-mini,gpt-4o")
- `RUNS_PER_TEST`: Number of times to run each test (default: 2)
- `SUCCESS_THRESHOLD`: Success rate threshold (default: 0.7)
- `OPENAI_BASE_URL`: Base URL for OpenAI API (optional)

## Running Tests

### Direct Server Tests (No API Key Required)

For development and testing without requiring a real OpenAI API key:

```bash
# Run direct server tests
pytest --run-e2e tests/e2e/modules/test_zpa.py::TestZPAModuleE2E::test_server_connectivity -v
pytest --run-e2e tests/e2e/modules/test_zpa.py::TestZPAModuleE2E::test_mock_api_functionality -v
pytest --run-e2e tests/e2e/modules/test_zpa.py::TestZPAModuleE2E::test_minimal_server -v
```

These tests verify:
- Server initialization and connectivity
- Mock API functionality
- Minimal server creation without pickle issues

### Full E2E Tests (Requires OpenAI API Key)

For complete E2E testing with real AI agents:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key"

# Run all E2E tests
pytest --run-e2e tests/e2e/
```

**Note**: Full E2E tests with agents may encounter pickle issues due to async objects in the MCP server. This is a known limitation of mcp-use with async objects.

### Run Specific Module Tests

```bash
# Run only ZIA tests
pytest --run-e2e tests/e2e/modules/test_zia.py

# Run only ZPA tests
pytest --run-e2e tests/e2e/modules/test_zpa.py
```

### Run with Different Models

```bash
MODELS_TO_TEST="gpt-4o-mini" pytest --run-e2e tests/e2e/
```

### Run with Higher Verbosity

```bash
pytest --run-e2e tests/e2e/ -v -s
```

## Test Modules

### ZIA Module Tests (`test_zia.py`)

Tests for Zscaler Internet Access functionality:

- `test_get_cloud_applications`: Tests cloud application retrieval
- `test_get_url_categories`: Tests URL category retrieval
- `test_get_static_ips`: Tests static IP address retrieval

### ZPA Module Tests (`test_zpa.py`)

Tests for Zscaler Private Access functionality:

- `test_get_app_segments`: Tests application segment retrieval
- `test_get_server_groups`: Tests server group retrieval
- `test_get_app_connector_groups`: Tests app connector group retrieval

## Adding New Tests

### 1. Create a New Test Module

Create a new file in `tests/e2e/modules/` following the naming convention `test_<module>.py`.

### 2. Define Test Class

```python
@pytest.mark.e2e
class TestNewModuleE2E(BaseE2ETest):
    def test_new_functionality(self):
        async def test_logic():
            # Mock API responses
            fixtures = [
                {
                    "operation": "some_operation",
                    "validator": lambda kwargs: True,
                    "response": {
                        "status_code": 200,
                        "body": {"data": "test_data"}
                    },
                },
            ]
            
            self._mock_api_instance.some_method.side_effect = (
                self._create_mock_api_side_effect(fixtures)
            )
            
            prompt = "Your test prompt here"
            return await self._run_agent_stream(prompt)

        def assertions(tools, result):
            # Verify expected behavior
            self.assertGreaterEqual(len(tools), 1)
            # Add specific assertions

        self.run_test_with_retries(
            "test_new_functionality",
            test_logic,
            assertions,
        )
```

### 3. Mock API Responses

Use the `self._create_mock_api_side_effect` method to mock Zscaler API responses:

```python
fixtures = [
    {
        "operation": "method_name",
        "validator": lambda kwargs: True,  # or specific validation logic
        "response": {
            "status_code": 200,
            "body": {"key": "value", "data": [...]}
        },
    },
]

self._mock_api_instance.method_name.side_effect = (
    self._create_mock_api_side_effect(fixtures)
)
```

### 4. Write Assertions

Assertions should verify:

- Tool calls were made (`len(tools) >= 1`)
- Expected content in results
- Correct tool names were used
- Response format is correct

## Best Practices

1. **Use Descriptive Test Names**: Test names should clearly describe what functionality is being tested
2. **Mock Realistic Data**: Use realistic test data that matches the expected API responses
3. **Comprehensive Assertions**: Check both tool usage and result content
4. **Handle LLM Variability**: Use retry logic and success thresholds to account for LLM response variations
5. **Isolate Tests**: Each test should be independent and not rely on other tests
6. **Use Synchronous Approach**: All test logic should be synchronous to avoid pickle issues
7. **Test Direct Server Functionality**: Include tests that bypass the agent to avoid pickle limitations

## Troubleshooting

### Common Issues

1. **OpenAI API Key Not Set**: Tests will automatically use mock LLM if no valid API key is available
2. **Server Connection Issues**: Check that the MCP server starts correctly on port 8000
3. **Test Failures**: Check the success threshold and consider adjusting for LLM variability
4. **Mock Issues**: Verify that API mocks are set up correctly for each test
5. **Pickle Errors**: This is a known limitation of mcp-use with async objects. Use direct server tests instead.

### Known Limitations

- **Pickle Issues with Agents**: mcp-use cannot pickle async objects from the MCP server
- **Async Object Serialization**: The Zscaler SDK creates async objects that can't be serialized
- **Agent Testing**: Full agent testing requires a real OpenAI API key and may encounter pickle issues

### Debug Mode

Run tests with higher verbosity to see detailed output:

```bash
pytest --run-e2e tests/e2e/ -v -s --log-cli-level=DEBUG
```

## Performance Considerations

- E2E tests are slower than unit tests due to LLM API calls
- Tests run multiple times to ensure reliability
- Consider using faster models (like GPT-4o-mini) for development
- Use appropriate success thresholds to balance reliability and speed
- Mock LLM is used when no API key is available, making tests faster and more reliable
- Direct server tests avoid pickle issues and run much faster 