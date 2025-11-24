# Cluster Lifecycle Tests

This document describes the Playwright tests for full cluster lifecycle operations with polling.

## Tests

### test_cluster_lifecycle.py

Three comprehensive tests that validate complete cluster lifecycle including creation and deletion polling:

1. **test_m0_cluster_lifecycle**
   - Creates a project
   - Creates an M0 (Free Tier) cluster in US_EAST_1
   - Polls every 10s until cluster reaches IDLE state (max 10 minutes)
   - Deletes the cluster
   - Polls every 10s until cluster is removed from list (max 10 minutes)
   - Deletes the project

2. **test_flex_cluster_lifecycle**
   - Creates a project
   - Creates a Flex cluster (pay-per-use) in US_EAST_1
   - Polls every 10s until cluster reaches IDLE state (max 10 minutes)
   - Deletes the cluster
   - Polls every 10s until cluster is removed from list (max 10 minutes)
   - Deletes the project

3. **test_m10_cluster_lifecycle**
   - Creates a project
   - Creates an M10 (Dedicated) cluster in US_EAST_1
   - Polls every 10s until cluster reaches IDLE state (max 10 minutes)
   - Deletes the cluster
   - Polls every 10s until cluster is removed from list (max 10 minutes)
   - Deletes the project

## Prerequisites

1. **AtlasUI Server Running**
   ```bash
   uv run atlasui start
   # or
   inv start
   ```

2. **Atlas API Credentials Configured**
   - Set environment variables or .env file:
     ```bash
     ATLAS_PUBLIC_KEY=your_public_key
     ATLAS_PRIVATE_KEY=your_private_key
     ```
   - Or for service account:
     ```bash
     ATLAS_AUTH_METHOD=service_account
     ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE=/path/to/credentials.json
     ```

3. **Playwright Browsers Installed**
   ```bash
   playwright install chromium
   ```

## Running the Tests

### Run All Three Tests
```bash
# Run all lifecycle tests with verbose output
uv run pytest tests/test_cluster_lifecycle.py -v -s -m integration

# Or using the direct script
python tests/test_cluster_lifecycle.py
```

### Run Individual Tests
```bash
# M0 cluster lifecycle only
uv run pytest tests/test_cluster_lifecycle.py::test_m0_cluster_lifecycle -v -s

# Flex cluster lifecycle only
uv run pytest tests/test_cluster_lifecycle.py::test_flex_cluster_lifecycle -v -s

# M10 cluster lifecycle only
uv run pytest tests/test_cluster_lifecycle.py::test_m10_cluster_lifecycle -v -s
```

### Run in Headed Mode (Show Browser)
```bash
uv run pytest tests/test_cluster_lifecycle.py -v -s --headed
```

### Run with Slow Motion (Debug)
```bash
uv run pytest tests/test_cluster_lifecycle.py -v -s --headed --slowmo 1000
```

## Expected Duration

Each test takes approximately:
- Project creation: ~5 seconds
- Cluster creation initiation: ~10 seconds
- **Cluster creation polling: 5-10 minutes** (polls every 10s until IDLE)
- Cluster deletion initiation: ~5 seconds
- **Cluster deletion polling: 2-5 minutes** (polls every 10s until removed)
- Project deletion: ~5 seconds

**Total per test: 10-20 minutes**

## Test Output

The tests provide detailed console output:

```
================================================================================
TEST: M0 Cluster Full Lifecycle
================================================================================

================================================================================
Creating New Project
================================================================================
1. Navigating to organizations page
2. Navigating to projects page
   Organization: 507f1f77bcf86cd799439011
3. Clicking Create Project button
4. Waiting for Create Project modal
5. Creating project: test-lifecycle-1234567890
6. Waiting for project creation to complete...
✓ Project 'test-lifecycle-1234567890' created successfully

================================================================================
Creating M0 Cluster
================================================================================
  Name: m0-test-1234567890
  Project: test-lifecycle-1234567890
  Provider: AWS
  Region: US_EAST_1
  Type: REPLICASET

1. Navigating to clusters page
2. Clicking Create Cluster button
3. Waiting for Create Cluster modal
4. Selecting project: test-lifecycle-1234567890
   Found project: test-lifecycle-1234567890 (OrgName)
5. Filling cluster details
6. Submitting cluster creation form
7. Waiting for creation to initiate...
  ✓ Cluster creation initiated

  ⏳ Waiting for cluster 'm0-test-1234567890' to reach IDLE state...
     This may take 5-10 minutes. Polling every 10 seconds (timeout: 600s)
     Attempt 1 (0s elapsed)...
     Status: CREATING
     Attempt 2 (10s elapsed)...
     Status: CREATING
     ...
     Attempt 35 (340s elapsed)...
     Status: IDLE
  ✓ Cluster 'm0-test-1234567890' is now IDLE (ready)

================================================================================
Deleting Cluster: m0-test-1234567890
================================================================================
1. Navigating to clusters page
2. Finding cluster 'm0-test-1234567890'
3. Clicking delete button
4. Waiting for delete confirmation modal
5. Typing cluster name to confirm deletion
6. Clicking delete confirmation button
7. Waiting for deletion progress...
8. Monitoring deletion progress in modal...
  ✓ Deletion progress UI displayed
  ✓ Deletion success message displayed in modal
  ✓ Deletion initiated

  ⏳ Waiting for cluster 'm0-test-1234567890' deletion to complete...
     Polling every 10 seconds until cluster disappears (timeout: 600s)
     Attempt 1 (0s elapsed)...
     Status: DELETING (still deleting...)
     Attempt 2 (10s elapsed)...
     Status: DELETING (still deleting...)
     ...
     Attempt 15 (140s elapsed)...
  ✓ Cluster 'm0-test-1234567890' has been deleted (no longer in list)

================================================================================
Deleting Project: test-lifecycle-1234567890
================================================================================
1. Navigating to organizations page
2. Navigating to projects page
3. Finding project 'test-lifecycle-1234567890'
4. Clicking delete button
5. Waiting for delete confirmation modal
6. Typing project name to confirm deletion
7. Clicking delete confirmation button
8. Waiting for project deletion to complete...
  ✓ Project deletion completed

================================================================================
✓ M0 Cluster Lifecycle Test Completed Successfully
================================================================================
```

## Assertions

Each test includes assertions to ensure operations complete:

1. **Cluster Creation**:
   ```python
   assert creation_success, f"Cluster '{cluster_name}' did not reach IDLE state within timeout"
   ```

2. **Cluster Deletion**:
   ```python
   assert deletion_success, f"Cluster '{cluster_name}' was not deleted within timeout"
   ```

If any assertion fails, the test will fail with a clear error message.

## Troubleshooting

### Test Times Out During Cluster Creation
- Atlas cluster provisioning can take 5-10 minutes
- Check the Atlas Console to see cluster status
- Increase timeout if needed (default 600s = 10 minutes)

### Test Times Out During Cluster Deletion
- Cluster deletion typically takes 2-5 minutes
- The test polls the cluster list, not the deletion API
- Check console output to see which poll attempt failed

### "Cluster not found in list" Error
- The cluster may have been deleted by another process
- Check the Atlas Console for actual cluster status
- Verify credentials have permission to list clusters

### Browser Closes Too Quickly
- Use `--headed` flag to see the browser
- Use `--slowmo 1000` to slow down operations
- Uncomment `page.pause()` at end of test to inspect manually

## Notes

- These tests make real API calls to MongoDB Atlas
- They create and delete actual resources (though cleaned up automatically)
- Tests are marked with `@pytest.mark.integration`
- Only ONE M0 cluster is allowed per project (Atlas limitation)
- Flex clusters use the new shared infrastructure model (replaced Serverless)
- All tests clean up after themselves (delete cluster and project)
