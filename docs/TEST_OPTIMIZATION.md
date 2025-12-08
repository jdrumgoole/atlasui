# Test Optimization Guide

This document outlines strategies to reduce test execution time while maintaining coverage.

## Quick Reference: Test Suites

AtlasUI has three test suite commands optimized for different workflows:

| Command | Time | Coverage | Use Case |
|---------|------|----------|----------|
| `inv test-dev` | ~11 min | M0/Flex + Async | **Development**: Fast iteration |
| `inv m10-test` | ~20 min | M10 only | **M10 Features**: Pause/resume testing |
| `inv test-release` | ~20-25 min | Complete | **Release/CI**: Full coverage |

**Parallel execution is enabled by default. Use `--no-parallel` to disable.**

### Quick Start

```bash
# Development (excludes M10) - ✅ RECOMMENDED for daily work
inv test-dev

# Test M10 features (pause/resume)
inv m10-test

# Before release/merge to main
inv test-release
```

## Important: Running Async and Browser Tests

**Async integration tests and browser tests must be run separately** to avoid event loop conflicts.

```bash
# Run async integration tests separately
uv run pytest tests/test_integration.py -v

# Run browser tests separately
uv run pytest tests/ -m "browser and not m10" -v

# Or use the convenience commands which handle this automatically
inv test-dev        # Development tests (excludes M10)
inv test-release    # Full test suite
```

The reason is that Playwright browser tests use their own event loop, and pytest-asyncio's async fixtures conflict when run in the same session. This is documented in `tests/conftest.py`.

## Current Performance Baseline

**Browser Tests (Full Suite):**
- Total time: ~20 minutes (1214s)
- Cluster creation: ~10 minutes (M10: 9 min, Flex: 31s, M0: 16s)
- Test execution: ~8 minutes
- Cleanup: ~2.5 minutes

**Async Tests:**
- Unit tests: ~5-10 seconds
- Integration tests: ~20-30 seconds
- Total: ~30-40 seconds

## Optimization Strategies

### 1. Run Async and Browser Tests in Parallel ⚡

**Time Savings:** ~10-15 minutes (async tests complete while browser tests are still running)

**Implementation:**
```bash
# Run both test suites in parallel (default behavior)
inv test-dev

# Sequential execution (if needed)
inv test-dev --no-parallel
```

**How it works:** Browser tests take 20 minutes, async tests take 30 seconds. Running in parallel means total time = max(20 min, 30s) = 20 min instead of 20.5 min.

**Trade-offs:**
- ✅ Significant time savings
- ✅ No coverage impact
- ⚠️ More complex output (both streams mixed)
- ⚠️ Harder to debug failures

### 2. Conditional Cluster Creation by Test Selection

**Time Savings:** Up to 9 minutes if M10 tests are skipped

**Implementation:**
Add pytest hooks to detect which cluster types are needed:

```python
# In conftest.py
def pytest_collection_modifyitems(config, items):
    """
    Only create clusters that are actually needed for selected tests.
    """
    needs_m0 = any("m0" in item.keywords for item in items)
    needs_m10 = any("m10" in item.keywords for item in items)
    needs_flex = any("flex" in item.keywords for item in items)

    # Store in config for fixtures to access
    config.needs_m0 = needs_m0
    config.needs_m10 = needs_m10
    config.needs_flex = needs_flex
```

**Usage:**
```bash
# Run only M0 and Flex tests (skip 9-minute M10 creation)
pytest -m "browser and (m0 or flex) and not m10"

# Run only smoke tests (lightweight)
pytest -m "browser and not (m0 or m10 or flex)"
```

**Trade-offs:**
- ✅ Massive time savings when not testing M10
- ✅ Good for development workflows
- ⚠️ Must remember to run full suite before merging

### 3. Use Pytest-xdist for Parallel Browser Tests

**Time Savings:** 30-50% reduction in browser test time

**Setup:**
```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Run browser tests with 2 workers
pytest tests/ -m browser -n 2

# Auto-detect CPU count
pytest tests/ -m browser -n auto
```

**Configuration for Playwright:**
```python
# In conftest.py
@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    """Configure browser context for parallel execution."""
    return {
        **browser_context_args,
        # Each worker gets isolated storage
        "storage_state": None,
    }
```

**Trade-offs:**
- ✅ 30-50% time reduction
- ✅ Better CPU utilization
- ⚠️ Each worker creates own clusters (unless using class-scoped fixtures)
- ⚠️ More complex to debug
- ⚠️ Potential race conditions with shared resources

### 4. Use Lighter Test Clusters (Development Mode)

**Time Savings:** ~9 minutes for M10 → M0 substitution

**Implementation:**
```python
# Add environment variable for development mode
USE_LIGHT_CLUSTERS = os.getenv("ATLASUI_TEST_LIGHT_CLUSTERS", "false").lower() == "true"

if USE_LIGHT_CLUSTERS:
    # Use M0 for all tests instead of M10
    M10_CLUSTER_NAME = "m0-cluster-dev"
    SKIP_M10_CREATION = True
```

**Usage:**
```bash
# Run with lightweight clusters
ATLASUI_TEST_LIGHT_CLUSTERS=true pytest tests/ -m browser
```

**Trade-offs:**
- ✅ Significant time savings in development
- ✅ Still tests UI functionality
- ⚠️ Reduced coverage (M10-specific features not tested)
- ⚠️ Must run full suite in CI/CD

### 5. Reuse Persistent Test Clusters

**Time Savings:** ~10 minutes per run after first run

**Implementation:**
Create a separate "persistent" mode that reuses existing clusters:

```python
# In conftest.py
PERSISTENT_MODE = os.getenv("ATLASUI_TEST_PERSISTENT", "false").lower() == "true"
PERSISTENT_PROJECT_NAME = "atlasui-test-persistent"

@pytest.fixture(scope="session")
def test_project(atlasui_server):
    if PERSISTENT_MODE:
        # Try to find existing project
        existing_id = _find_existing_project(PERSISTENT_PROJECT_NAME)
        if existing_id:
            log("Using persistent test project")
            yield {"project_id": existing_id, ...}
            # Don't delete on teardown
            return

    # Normal behavior: create and delete
    ...
```

**Usage:**
```bash
# First run: creates clusters (20 min)
ATLASUI_TEST_PERSISTENT=true pytest tests/ -m browser

# Subsequent runs: reuses clusters (10 min)
ATLASUI_TEST_PERSISTENT=true pytest tests/ -m browser

# Cleanup when done
inv cleanup-tests
```

**Trade-offs:**
- ✅ 50% time reduction after first run
- ✅ Great for iterative development
- ⚠️ Clusters accumulate if not cleaned up
- ⚠️ Potential state pollution between runs
- ⚠️ Must manually clean up
- ⚠️ NOT suitable for CI/CD

### 6. Test Pyramid: More Unit Tests, Fewer Browser Tests

**Time Savings:** Varies based on test conversion

**Strategy:**
- Browser test: ~2-3 minutes (including cluster creation overhead)
- API integration test: ~5-10 seconds
- Unit test: ~0.1 seconds

**Conversion candidates:**
1. **Replace UI assertions with API checks** where UI is not critical:
   ```python
   # Before (browser test)
   def test_cluster_visible(page):
       page.goto("/clusters")
       assert page.locator(f'tr[data-cluster-name="{name}"]').count() > 0

   # After (API test)
   @pytest.mark.integration
   async def test_cluster_visible(atlas_client):
       clusters = await atlas_client.list_clusters(project_id)
       assert any(c.name == name for c in clusters)
   ```

2. **Mock Atlas API responses** for UI rendering tests:
   ```python
   # Test UI rendering with mocked data (unit test)
   def test_cluster_table_rendering(mock_atlas_client):
       mock_atlas_client.list_clusters.return_value = [mock_cluster]
       # Test UI rendering logic
   ```

**Trade-offs:**
- ✅ Massive time savings (minutes → seconds)
- ✅ Faster feedback loop
- ⚠️ Reduced integration coverage
- ⚠️ May miss UI-specific bugs
- ✅ Maintain critical happy-path browser tests

### 7. Smart Test Selection Based on Changes

**Time Savings:** 50-90% when testing specific changes

**Tools:**
- `pytest-testmon`: Only run tests affected by code changes
- `pytest-picked`: Run tests for changed files

**Setup:**
```bash
uv pip install pytest-testmon pytest-picked

# Run only tests affected by changes
pytest --testmon

# Run tests for git-changed files
pytest --picked
```

**Usage Patterns:**
```bash
# Development: Quick iteration
pytest --testmon -m "not browser"

# Pre-commit: Affected tests only
pytest --picked

# CI/CD: Full suite
pytest tests/
```

**Trade-offs:**
- ✅ 50-90% time reduction during development
- ✅ Faster iteration cycles
- ⚠️ May miss indirect test failures
- ⚠️ Still need full suite runs periodically

## Recommended Workflow

### Development (Fast Iteration)
```bash
# Fast development suite - excludes M10 tests (~11 min) ✅ RECOMMENDED
inv test-dev                  # Runs in parallel by default
inv test-dev --no-parallel    # Sequential execution if needed

# Quick unit tests only (~10 seconds)
pytest -m "not integration and not browser"

# With affected tests only (~30 seconds)
pytest --testmon -m "not browser"

# Run specific test file
pytest tests/test_specific.py -v
```

### Testing M10 Features (Pause/Resume)
```bash
# M10 tests only (~20 minutes)
inv m10-test

# Or directly with pytest
pytest -m "browser and m10" -v
```

### Pre-Commit (Confidence Check)
```bash
# Development tests (no M10) - parallel by default
inv test-dev

# Sequential execution if needed
inv test-dev --no-parallel
```

### Release / CI/CD (Full Coverage)
```bash
# Complete test suite including M10 (~20-25 min) - parallel by default
inv test-release

# Sequential execution if needed
inv test-release --no-parallel
```

### Long-Running Test Development
```bash
# Use persistent clusters
ATLASUI_TEST_PERSISTENT=true pytest tests/ -m browser

# Skip expensive M10 tests during development (built into test-dev)
pytest -m "browser and not m10"

# Clean up when done
inv cleanup-tests
```

## Summary: Expected Time Savings

| Optimization | Time Saved | Coverage Impact | Effort |
|-------------|------------|-----------------|--------|
| Parallel async + browser | ~10-15 min | None | Low (✅ Done) |
| Conditional cluster creation | Up to 9 min | None (if all clusters tested eventually) | Medium |
| Pytest-xdist (browser) | ~6-10 min | None | Medium |
| Light clusters (dev mode) | ~9 min | Reduced (M10 features) | Low |
| Persistent clusters | ~10 min | None (cleanup risk) | Low |
| Test pyramid (more unit) | Varies | None (if well designed) | High |
| Smart test selection | ~50-90% | None (full suite still runs in CI) | Low |

## Best Quick Wins (Implemented)

1. ✅ **Parallel async + browser tests** - `inv test-dev` (enabled by default)
   - Time: 20 min → 20 min (async runs during browser setup)
   - No coverage impact
   - Easy to use

2. ⚡ **Skip M10 tests during development** - `pytest -m "browser and not m10"`
   - Time: 20 min → 11 min
   - Test M10 before commit

3. ⚡ **Use pytest-testmon for iteration** - `pytest --testmon -m "not browser"`
   - Time: 30s → 5-10s
   - Great for TDD

## Measurement

Track test performance over time:

```bash
# Generate timing report
pytest --durations=20 --durations-min=1.0

# Profile test execution
pytest --profile

# Monitor over time
pytest --benchmark-only
```
