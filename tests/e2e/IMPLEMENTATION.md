# E2E Test Implementation Guide

This document explains how the E2E tests were implemented for the Zscaler MCP Server, based on the Zscaler MCP pattern.

## Architecture Overview

### Key Components

1. **BaseE2ETest Class** (`tests/e2e/utils/base_e2e_test.py`)
   - Provides shared infrastructure for all E2E tests
   - Manages MCP server lifecycle
   - Handles LangChain integration
   - Implements retry logic and success thresholds

2. **SharedTestServer Singleton**
   - Manages a single MCP server instance across all tests
   - Handles environment setup and cleanup
   - Provides mock API responses

3. **Test Modules** (`tests/e2e/modules/`)
   - Individual test files for each Zscaler service (ZIA, ZPA, etc.)
   - Follow consistent naming pattern: `Test{Service}ModuleE2E`
   - Use async test logic and assertion functions

## Implementation Details

### LangChain Integration

The E2E tests use LangChain to create AI agents that interact with the MCP server:

```python
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

# Initialize LLM
self.llm = ChatOpenAI(model=model_name, temperature=0.7)

# Create MCP agent
self.agent = MCPAgent(
    llm=self.llm,
    client=self.client,
    max_steps=20,
    verbose=verbose_mode,
    use_server_manager=True,
    memory_enabled=False,
)
```

### Mock API Strategy

Instead of making real API calls, the tests mock the Zscaler client:

```python
# Mock the Zscaler client
self.patchers["api"] = patch("zscaler_mcp.client.get_zscaler_client")
mock_client_class = self.patchers["api"].start()

# Create mock instance
self.patchers["mock_api_instance"] = MagicMock()
mock_client_class.return_value = self.patchers["mock_api_instance"]

# Set up mock responses
self._mock_api_instance.cloud_applications.return_value = mock_response
```

### Test Structure Pattern

Each test follows this pattern:

```python
def test_functionality(self):
    async def test_logic():
        # 1. Set up mock responses
        mock_response = {"data": "test_data"}
        self._mock_api_instance.method.return_value = mock_response
        
        # 2. Define prompt
        prompt = "Your test prompt here"
        
        # 3. Run agent
        return await self._run_agent_stream(prompt)

    def assertions(tools, result):
        # 4. Verify results
        self.assertGreaterEqual(len(tools), 1)
        # Add specific assertions

    # 5. Run with retries
    self.run_test_with_retries(
        "test_name",
        test_logic,
        assertions,
    )
```

### Multi-Model Testing

Tests run against multiple LLM models to ensure robustness:

```python
# Default models
DEFAULT_MODELS_TO_TEST = ["gpt-4o-mini", "gpt-4o"]

# Configurable via environment
MODELS_TO_TEST = os.getenv("MODELS_TO_TEST", ",".join(DEFAULT_MODELS_TO_TEST)).split(",")
```

### Success Thresholds

Tests use success thresholds to account for LLM variability:

```python
# Default 70% success rate required
DEFAULT_SUCCESS_THRESHOLD = 0.7
SUCCESS_THRESHOLD = float(os.getenv("SUCCESS_THRESHOLD", str(DEFAULT_SUCCESS_THRESHOLD)))

# Assert success rate
success_rate = success_count / total_runs
self.assertGreaterEqual(success_rate, SUCCESS_THRESHOLD)
```

## Configuration Options

### Environment Variables

- `OPENAI_API_KEY`: Required for LangChain
- `OPENAI_BASE_URL`: Optional custom OpenAI endpoint
- `MODELS_TO_TEST`: Comma-separated list of models
- `RUNS_PER_TEST`: Number of test runs (default: 2)
- `SUCCESS_THRESHOLD`: Success rate threshold (default: 0.7)

### Dependencies

Added to `pyproject.toml`:

```toml
[project.optional-dependencies]
e2e = [
    "pytest-asyncio>=0.21.0",
    "langchain-openai>=0.3.28",
    "mcp-use[search]>=1.3.7"
]
```

## Running Tests

### Basic Usage

```bash
# Install E2E dependencies
pip install -e ".[e2e]"

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key"

# Run all E2E tests
pytest tests/e2e/ -m e2e -v

# Run specific module
pytest tests/e2e/modules/test_zia.py -m e2e -v
```

### Using the Runner Script

```bash
# Quick test run
python tests/e2e/run_e2e_tests.py --quick

# Custom configuration
python tests/e2e/run_e2e_tests.py \
    --models "gpt-4o-mini" \
    --runs 3 \
    --threshold 0.8 \
    --test-path tests/e2e/modules/test_zia.py
```

## Test Examples

### ZIA Module Test

```python
def test_get_cloud_applications(self):
    async def test_logic():
        mock_response = {
            "applications": [
                {"id": "app-001", "name": "Salesforce", "risk_level": "Low"},
                {"id": "app-002", "name": "Slack", "risk_level": "Medium"}
            ]
        }
        self._mock_api_instance.cloud_applications.return_value = mock_response
        
        prompt = "List the top 3 cloud applications and their risk levels"
        return await self._run_agent_stream(prompt)

    def assertions(tools, result):
        self.assertGreaterEqual(len(tools), 1)
        result_lower = result.lower()
        self.assertTrue("salesforce" in result_lower or "slack" in result_lower)
        self.assertTrue("risk" in result_lower)

    self.run_test_with_retries("test_get_cloud_applications", test_logic, assertions)
```

### ZPA Module Test

```python
def test_get_app_segments(self):
    async def test_logic():
        mock_response = {
            "segments": [
                {"id": "seg-001", "name": "Web Applications", "type": "WEB"},
                {"id": "seg-002", "name": "Database Applications", "type": "DB"}
            ]
        }
        self._mock_api_instance.app_segments.return_value = mock_response
        
        prompt = "List all application segments and their types"
        return await self._run_agent_stream(prompt)

    def assertions(tools, result):
        self.assertGreaterEqual(len(tools), 1)
        result_lower = result.lower()
        self.assertTrue("web applications" in result_lower or "database applications" in result_lower)

    self.run_test_with_retries("test_get_app_segments", test_logic, assertions)
```

## Best Practices

### 1. Mock Realistic Data

Use realistic test data that matches actual API responses:

```python
mock_response = {
    "applications": [
        {
            "id": "app-001",
            "name": "Salesforce",
            "category": "Business",
            "risk_level": "Low",
            "status": "Active"
        }
    ]
}
```

### 2. Comprehensive Assertions

Check both tool usage and result content:

```python
def assertions(tools, result):
    # Check tool usage
    self.assertGreaterEqual(len(tools), 1)
    
    # Check result content
    result_lower = result.lower()
    self.assertTrue("expected_content" in result_lower)
    
    # Check specific tool names if needed
    tool_names = [tool["input"]["tool_name"] for tool in tools]
    self.assertIn("expected_tool_name", tool_names)
```

### 3. Handle LLM Variability

Use flexible assertions that account for different LLM responses:

```python
# Instead of exact string matching
self.assertIn("exact_string", result)

# Use flexible matching
result_lower = result.lower()
self.assertTrue(
    "keyword1" in result_lower or "keyword2" in result_lower,
    f"Expected keywords in result: {result}"
)
```

### 4. Descriptive Test Names

Use clear, descriptive test names:

```python
def test_get_cloud_applications(self):  # Good
def test_cloud_apps(self):             # Too vague
```

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
   - Adjust success threshold: `SUCCESS_THRESHOLD=0.5`
   - Use more specific prompts
   - Add more flexible assertions

4. **Mock Issues**
   - Verify mock setup in test logic
   - Check that mock methods match actual API methods

### Debug Mode

```bash
# Run with debug output
pytest tests/e2e/ -m e2e -v -s --log-cli-level=DEBUG

# Run single test with verbose output
pytest tests/e2e/modules/test_zia.py::TestZIAModuleE2E::test_get_cloud_applications -v -s
```

## Performance Considerations

- E2E tests are slower than unit tests (due to LLM API calls)
- Consider using faster models for development (`gpt-4o-mini`)
- Use appropriate success thresholds to balance reliability and speed
- Run tests in parallel when possible (but be mindful of API rate limits)

## Future Enhancements

1. **Add More Test Modules**: ZDX, ZCC, ZIdentity
2. **Enhanced Mocking**: More sophisticated API response mocking
3. **Performance Testing**: Measure response times and throughput
4. **Integration Testing**: Test with real Zscaler environments
5. **CI/CD Integration**: Add E2E tests to automated pipelines 