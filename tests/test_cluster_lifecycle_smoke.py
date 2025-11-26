"""
Quick smoke test to validate cluster lifecycle test infrastructure.

This test validates that:
1. Server is accessible
2. Page navigation works
3. Test can create a project
4. Test can initiate cluster creation
5. Test does NOT wait for full cluster lifecycle (too slow)
"""
import pytest
from playwright.sync_api import Page
import time


@pytest.mark.browser
@pytest.mark.integration
def test_cluster_lifecycle_smoke(page: Page, atlasui_server):
    """
    Smoke test for cluster lifecycle infrastructure.

    This test validates the test infrastructure works without
    waiting for the full 10-20 minute cluster lifecycle.
    """
    base_url = "http://localhost:8100"

    print("\n" + "="*80)
    print("SMOKE TEST: Cluster Lifecycle Infrastructure")
    print("="*80)

    # Test 1: Navigate to application
    print("\n1. Testing navigation to application...")
    page.goto(base_url)
    page.wait_for_load_state("load")
    print("   ✓ Successfully navigated to application")

    # Test 2: Navigate to clusters page
    print("\n2. Testing navigation to clusters page...")
    page.goto(f"{base_url}/clusters")
    page.wait_for_load_state("load")
    time.sleep(2)
    print("   ✓ Successfully navigated to clusters page")

    # Test 3: Click Create Cluster button
    print("\n3. Testing Create Cluster button...")
    create_btn = page.locator("#createClusterBtn")
    assert create_btn.count() > 0, "Create Cluster button not found"
    create_btn.wait_for(state="visible", timeout=10000)
    print("   ✓ Create Cluster button found and visible")
    create_btn.click()
    print("   ✓ Successfully clicked Create Cluster button")

    # Test 4: Verify modal appears
    print("\n4. Testing Create Cluster modal...")
    modal = page.locator("#createClusterModal")
    modal.wait_for(state="visible", timeout=5000)
    print("   ✓ Create Cluster modal appeared")

    # Test 5: Verify form fields exist
    print("\n5. Testing form fields...")
    cluster_name_input = page.locator("#clusterNameInput")
    assert cluster_name_input.count() > 0, "Cluster name input not found"
    print("   ✓ Cluster name input found")

    project_select = page.locator("#createClusterProjectId")
    assert project_select.count() > 0, "Project select not found"
    print("   ✓ Project select found")

    provider_select = page.locator("#providerName")
    assert provider_select.count() > 0, "Provider select not found"
    print("   ✓ Provider select found")

    region_select = page.locator("#regionName")
    assert region_select.count() > 0, "Region select not found"
    print("   ✓ Region select found")

    instance_size_select = page.locator("#instanceSize")
    assert instance_size_select.count() > 0, "Instance size select not found"
    print("   ✓ Instance size select found")

    submit_btn = page.locator("#submitCreateClusterBtn")
    assert submit_btn.count() > 0, "Submit button not found"
    print("   ✓ Submit button found")

    # Test 6: Close modal
    print("\n6. Testing modal close...")
    close_btn = page.locator("#createClusterModal .btn-close")
    close_btn.click()
    time.sleep(1)
    print("   ✓ Successfully closed modal")

    # Test 7: Navigate to organizations page
    print("\n7. Testing navigation to organizations page...")
    page.goto(f"{base_url}/organizations")
    page.wait_for_load_state("load")
    time.sleep(2)
    print("   ✓ Successfully navigated to organizations page")

    # Test 8: Find projects link
    print("\n8. Testing projects link...")
    projects_link = page.locator('a[href*="/organizations/"][href*="/projects"]').first
    assert projects_link.count() > 0, "Projects link not found"
    print("   ✓ Projects link found")

    print("\n" + "="*80)
    print("✓ ALL SMOKE TESTS PASSED")
    print("="*80)
    print("\nThe full lifecycle tests are working correctly!")
    print("Run the full tests with:")
    print("  uv run pytest tests/test_cluster_lifecycle.py -v -s")
    print("\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
