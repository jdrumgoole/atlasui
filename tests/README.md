# AtlasUI Tests

This directory contains the test suite for AtlasUI, including both unit tests and integration tests.

## Test Types

### Unit Tests
Unit tests use mocked Atlas API responses and don't require real credentials:
- `test_client.py` - Tests for the Atlas API client with mocked responses
- `test_api.py` - Tests for web API endpoints with mocked data
- `test_config.py` - Tests for configuration management
- `test_service_account.py` - Tests for service account authentication

### Integration Tests
Integration tests make real API calls to MongoDB Atlas and require valid credentials:
- `test_integration.py` - Tests for Atlas API client operations
- `test_api_integration.py` - Tests for web API endpoints with real Atlas data

### Browser Tests
Browser tests use Playwright to test the web UI and require a running server:
- `test_cluster_lifecycle_smoke.py` - Smoke tests for cluster lifecycle UI
- `test_create_cluster_ui.py` - Tests for cluster creation UI

**Important:** Browser tests should be run separately from async tests to avoid event loop conflicts. See "Running Tests" section below.

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -e ".[dev]"
```

2. For integration tests, configure Atlas API credentials:
```bash
# Create .env file with your credentials
cp .env.example .env

# Edit .env and add:
ATLAS_AUTH_METHOD=api_key
ATLAS_PUBLIC_KEY=your_public_key
ATLAS_PRIVATE_KEY=your_private_key
```

### Run All Tests (Recommended Approach)

Due to event loop conflicts between browser tests and async tests, it's recommended to run them separately:

```bash
# Run async tests (unit + integration, excluding browser)
uv run pytest tests/ -m "not browser" -v

# Run browser tests separately
uv run pytest tests/ -m browser -v
```

Alternatively, you can run all tests together (may experience event loop conflicts):

```bash
# Run all tests (may have event loop conflicts)
pytest

# Or using invoke
inv test
```

### Run Only Unit Tests

```bash
# Skip integration and browser tests
pytest -m "not integration and not browser"

# Or simpler: skip integration tests only
pytest -m "not integration"
```

### Run Only Integration Tests

```bash
# Run only integration tests (excluding browser)
pytest -m "integration and not browser"

# Run specific integration test file
pytest tests/test_integration.py -v

# Run specific test class
pytest tests/test_integration.py::TestProjects -v

# Run specific test
pytest tests/test_integration.py::TestProjects::test_list_projects -v
```

### Run Only Browser Tests

```bash
# Run browser tests (requires running server)
pytest -m browser

# Or with full path
uv run pytest tests/ -m browser -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=atlasui --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Credential Validation

Integration tests automatically validate that:
1. Atlas API credentials are configured
2. The credentials are valid and can authenticate

If validation fails, integration tests will be automatically skipped with a clear message:

```
⚠️  Atlas API keys not configured. Skipping integration tests.
   Set ATLAS_PUBLIC_KEY and ATLAS_PRIVATE_KEY environment variables.
```

or

```
⚠️  Atlas API credentials validation failed: <error message>
   Please check your API keys or service account credentials.
```

## Test Organization

Tests are organized by functionality:

- **API Root Tests** (`test_integration.py::TestAtlasAPIRoot`) - Basic connectivity and authentication
- **Organization Tests** (`test_integration.py::TestOrganizations`) - Organization operations
- **Project Tests** (`test_integration.py::TestProjects`) - Project CRUD operations
- **Cluster Tests** (`test_integration.py::TestClusters`) - Cluster management operations
- **Error Handling Tests** (`test_integration.py::TestErrorHandling`) - Error scenarios
- **Web API Tests** (`test_api_integration.py`) - FastAPI endpoint testing

## Writing New Tests

### Unit Tests

For unit tests, use the `mock_atlas_client` fixture:

```python
def test_my_feature(mock_atlas_client):
    """Test my feature with mocked API."""
    mock_response = Mock()
    mock_response.json.return_value = {"result": "data"}
    mock_atlas_client.return_value.request.return_value = mock_response

    # Your test code here
```

### Integration Tests

For integration tests, use the `atlas_client` fixture and mark with `@pytest.mark.integration`:

```python
@pytest.mark.integration
def test_my_feature(atlas_client):
    """Test my feature with real API."""
    result = atlas_client.some_operation()
    assert result is not None
```

The `atlas_client` fixture automatically:
- Validates credentials before running
- Skips the test if credentials are invalid
- Creates and manages the client connection

## Continuous Integration

In CI/CD environments without Atlas credentials, integration tests will be automatically skipped.
Only unit tests will run, ensuring the pipeline can still validate code quality.

To run integration tests in CI, configure the appropriate secrets:
- `ATLAS_PUBLIC_KEY`
- `ATLAS_PRIVATE_KEY`

## Debugging Tests

Run tests with verbose output and show print statements:

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Both verbose and show prints
pytest -v -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

## Test Data

Integration tests use real Atlas resources and won't create or modify any resources unless explicitly designed to do so. They primarily test read operations:
- Listing organizations, projects, clusters
- Getting details of existing resources
- Testing pagination and filtering

Destructive operations (create, update, delete) are tested separately and would require explicit setup.
