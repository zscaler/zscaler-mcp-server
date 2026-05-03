# Zscaler MCP Server Tests

This directory contains the test suite for the Zscaler MCP Server, organized by testing layer and service.

## 📁 Directory Structure

```text
tests/
├── conftest.py              # Pytest configuration and fixtures
├── test_server.py           # Server initialization tests
├── test_logging.py          # Logging functionality tests
├── test_registry.py         # Service registry tests
├── test_streamable_http_transport.py  # Transport layer tests
│
├── e2e/                     # End-to-End tests (require --run-e2e flag)
│   ├── test_zia.py
│   ├── test_zpa.py
│   ├── test_zdx.py
│   ├── test_zcc.py
│   └── test_zidentity.py
│
└── [service]/               # Unit tests organized by service
    ├── zia/                 # ZIA unit tests
    │   └── test_rule_labels.py
    ├── zpa/                 # ZPA unit tests
    ├── zdx/                 # ZDX unit tests
    ├── zcc/                 # ZCC unit tests
    ├── ztw/                 # ZTW unit tests
    └── zid/                 # ZID unit tests
```

## 🧪 Test Layers

Following the test pyramid approach:

### 1. Unit Tests (Most) - `tests/[service]/`

- **Purpose**: Test individual tool functions in isolation
- **Speed**: Fast (< 1s per test)
- **Mocking**: Full - no real API calls
- **Run**: Automatically on every code change
- **Example**: `tests/zia/test_rule_labels.py`

```bash
# Run all unit tests
pytest tests/zia tests/zpa tests/zdx tests/zcc tests/ztw tests/zid -v

# Run specific service unit tests
pytest tests/zia/ -v
```

### 2. Integration Tests (Moderate) - Top level tests

- **Purpose**: Test multiple components working together
- **Speed**: Moderate (1-5s per test)
- **Mocking**: Partial - some real components
- **Run**: Before commits
- **Example**: `tests/test_server.py`

```bash
# Run integration tests
pytest tests/test_*.py -v
```

### 3. End-to-End Tests (Few) - `tests/e2e/`

- **Purpose**: Test complete workflows with real APIs
- **Speed**: Slow (5-30s per test)
- **Mocking**: None - requires real credentials
- **Run**: Before releases (manual)
- **Example**: `tests/e2e/test_zia.py`

```bash
# Run E2E tests (requires credentials)
pytest tests/e2e/ --run-e2e -v
```

## 🚀 Running Tests

### Quick Start

```bash
# Run all unit and integration tests (fast)
pytest tests/ -v

# Run only unit tests for a specific service
pytest tests/zia/ -v

# Run E2E tests (requires API credentials)
pytest tests/e2e/ --run-e2e -v
```

### Test Selection

```bash
# Run specific test file
pytest tests/zia/test_rule_labels.py -v

# Run specific test class
pytest tests/zia/test_rule_labels.py::TestZiaListRuleLabels -v

# Run specific test function
pytest tests/zia/test_rule_labels.py::TestZiaListRuleLabels::test_list_labels_success -v

# Run tests matching a pattern
pytest tests/ -k "rule_label" -v
```

### Coverage Reports

```bash
# Run with coverage
pytest tests/ --cov=zscaler_mcp --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 📝 Writing Unit Tests

### Template for New Unit Tests

When creating unit tests for a new tool, follow this structure:

```python
"""
Unit tests for [Service] [Resource] tools.
"""

import pytest
from unittest.mock import MagicMock, patch
from zscaler_mcp.tools.[service].[tool_file] import (
    [service]_list_[resource],
    [service]_get_[resource],
    [service]_create_[resource],
    [service]_update_[resource],
    [service]_delete_[resource],
)


# Fixtures
@pytest.fixture
def mock_client():
    """Create a mock Zscaler client."""
    client = MagicMock()
    client.[service].[resource] = MagicMock()
    return client


# Test Classes (one per function)
class TestListResource:
    """Test cases for list operation."""
    
    @patch("zscaler_mcp.tools.[service].[tool_file].get_zscaler_client")
    def test_list_success(self, mock_get_client, mock_client):
        """Test successful listing."""
        # Setup → Execute → Verify
        pass


class TestGetResource:
    """Test cases for get operation."""
    pass


class TestCreateResource:
    """Test cases for create operation."""
    pass


class TestUpdateResource:
    """Test cases for update operation."""
    pass


class TestDeleteResource:
    """Test cases for delete operation."""
    pass


class TestWorkflow:
    """Test cases for complete CRUD workflow."""
    pass
```

### Test Coverage Requirements

Each tool function should have tests for:

- ✅ **Success case** - Normal operation with valid inputs
- ✅ **Error handling** - API errors and exceptions
- ✅ **Input validation** - Missing or invalid parameters
- ✅ **Edge cases** - Empty results, None values, etc.

### Example: Complete Test Coverage

See `tests/zia/test_rule_labels.py` for a complete example:

- **23 tests** covering all 5 CRUD operations
- **100% code coverage** of the tool functions
- **All edge cases** handled

## 🎯 Test Naming Conventions

```python
# Class naming
class TestZia[Action][Resource]:  # e.g., TestZiaListRuleLabels

# Method naming
def test_[action]_[scenario]:  # e.g., test_list_labels_success
def test_[action]_with_[condition]:  # e.g., test_list_labels_with_error
def test_[action]_[validation]:  # e.g., test_create_label_missing_name
```

## 🔧 Debugging Tests

```bash
# Run with verbose output
pytest tests/ -vv

# Run with print statements visible
pytest tests/ -s

# Run with pdb on failure
pytest tests/ --pdb

# Run last failed tests only
pytest tests/ --lf
```

## 📊 Current Test Status

| Service | Unit Tests | Coverage | Status |
|---------|------------|----------|--------|
| ZCC | `test_zcc_tools.py` (27 tests) | 100% | ✅ Complete |
| ZDX | `test_zdx_tools.py` (42 tests) | 100% | ✅ Complete |
| ZIA | `test_rule_labels.py` (23 tests) | 100% | ✅ Complete |
| ZTW | `test_ztw_tools.py` (36 tests) | 100% | ✅ Complete |
| ZPA | - | - | 🚧 Pending |
| ZIdentity | - | - | 🚧 Pending |

**Total: 128 unit tests passing** 🎉

## 🤝 Contributing

When adding new tools, please:

1. Create unit tests in the appropriate service folder
2. Ensure 100% code coverage for the new tool
3. Follow the test structure and naming conventions
4. Run tests locally before committing: `pytest tests/`

---

For more information, see:

- [Test Pyramid Best Practices](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Contributing Guide](../CONTRIBUTING.md)
