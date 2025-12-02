# Features

## Operation Queue System

AtlasUI includes a sophisticated operation queue system that manages long-running Atlas operations efficiently.

### Overview

Many MongoDB Atlas operations (cluster creation, deletion, project deletion) can take several minutes to complete. The operation queue system:

* Queues all operations for sequential processing
* Returns control to the UI immediately after initiating operations
* Provides real-time progress updates in a status panel
* Tracks operation history for the current session
* Handles errors gracefully with detailed error messages

### Operation Status Panel

The operation status panel appears at the bottom of the screen and displays:

* **Queued operations**: Operations waiting to be processed
* **In-progress operations**: Currently executing operations with progress updates
* **Completed operations**: Successfully finished operations
* **Failed operations**: Operations that encountered errors

The panel automatically expands when new operations are added and can be manually collapsed or expanded by clicking on it.

### Supported Operations

The following long-running operations are managed through the queue:

* **Create Project**: Creating new MongoDB Atlas projects within an organization
* **Create Cluster**: Creating new MongoDB clusters (M0, Flex, M10, M30, etc.)
* **Delete Cluster**: Removing clusters from a project
* **Delete Project**: Cascading deletion of projects with all associated clusters (includes automatic deletion of all associated clusters, both regular and Flex clusters)

### Auto-Refresh on Completion

The UI automatically refreshes resource lists when operations complete:

* **Project creation**: When a project is successfully created, it automatically appears in the projects list
* **Cluster creation**: When a cluster is successfully created, it automatically appears in the clusters list
* **Project deletion**: Deleted projects are immediately removed from the list (optimistic update)
* **Cluster deletion**: Deleted clusters are immediately removed from the list (optimistic update)

This eliminates the need for manual page refreshes while maintaining a responsive user experience.

## Cluster Pause/Resume

AtlasUI allows you to pause and resume dedicated clusters (M10+) to save costs when they are not in use.

### How It Works

Pausing a cluster stops the compute resources while preserving your data:

* **Data Preserved**: All your databases, collections, and indexes remain intact
* **Cost Savings**: You only pay for storage while the cluster is paused
* **Quick Resume**: Resume the cluster when you need it again

### Pause Restrictions

Not all clusters can be paused:

* **M0 (Free Tier)**: Cannot be paused (always running)
* **Flex Clusters**: Cannot be paused (managed automatically)
* **Dedicated (M10+)**: Full pause/resume support

### Status-Based State Transitions

When pausing or resuming a cluster, the UI waits for the actual state change before updating the button:

* **Pausing**: After clicking Pause, the status shows "PAUSING" and the button shows a spinner. The UI polls the cluster API every 5 seconds until the cluster reaches the PAUSED state, then switches the button to "Resume".
* **Resuming**: After clicking Resume, the status shows "RESUMING" and the button shows a spinner. The UI polls the cluster API every 5 seconds until the cluster reaches the IDLE state, then shows the countdown timer.

This ensures the UI accurately reflects the actual cluster state rather than assuming the operation completed immediately.

### 60-Minute Cooldown

After resuming a cluster, MongoDB Atlas enforces a 60-minute cooldown period before you can pause it again. AtlasUI tracks this cooldown:

* A countdown timer replaces the Pause button after resume (once IDLE state is confirmed)
* The timer shows MM:SS format with "Until next pause" label (e.g., "59:45" / "Until next pause")
* The countdown persists across page refreshes (stored in localStorage)
* Once the timer reaches zero, the Pause button becomes available again

### Usage

1. Navigate to the All Clusters page
2. Find the cluster you want to pause (must be M10 or larger)
3. Click the **Pause** button (yellow outline)
4. Wait for the cluster status to change to **PAUSED** (status shows PAUSING during transition)
5. The button changes to **Resume** once the cluster is fully paused
6. Click **Resume** when you need the cluster again
7. Wait for the cluster status to change to **IDLE** (status shows RESUMING during transition)
8. The countdown timer appears with "Until next pause" label
9. Wait for the 60-minute cooldown to pause again

### API Endpoints

The following REST API endpoints are available:

* `POST /api/clusters/{project_id}/{cluster_name}/pause` - Pause a cluster
* `POST /api/clusters/{project_id}/{cluster_name}/resume` - Resume a cluster
* `GET /api/clusters/{project_id}/{cluster_name}` - Get cluster status for polling

Both pause/resume endpoints return the updated cluster details.

## Flex Cluster Support

AtlasUI supports MongoDB Atlas's new Flex tier, which replaces the deprecated Serverless tier.

### What is Flex?

Flex clusters provide:

* **Pay-per-use pricing**: Only pay for the operations and storage you actually use
* **Auto-scaling**: Automatically scales resources based on workload demands
* **Shared infrastructure**: Runs on TENANT provider with shared resources
* **Cost-effective**: Ideal for development, testing, and variable workloads

### Configuration

Flex clusters use a specific configuration format:

```json
{
    "name": "cluster-name",
    "clusterType": "REPLICASET",
    "providerSettings": {
        "providerName": "TENANT",
        "backingProviderName": "AWS",  // or GCP, AZURE
        "regionName": "EU_WEST_1",
        "instanceSizeName": "FLEX"
    }
}
```

### Creating Flex Clusters

1. Navigate to the Clusters page
2. Click "Create Cluster"
3. Select a project
4. Choose "Flex" from the instance size dropdown (under "Flex (Shared Tier)")
5. Select your cloud provider (AWS, GCP, or Azure)
6. Choose your region
7. Select cluster type (REPLICASET or SHARDED)
8. Click "Create Cluster"

The cluster will be created using the TENANT provider model with the FLEX instance size.

### Migration from Serverless

If you were previously using Serverless clusters:

* Flex provides the same pay-per-use model
* Configuration format has changed from `serverlessSpec` to standard `providerSettings`
* All Serverless references in AtlasUI have been updated to Flex
* Tests and documentation reflect the new Flex tier

## Status-Based Polling

AtlasUI uses intelligent status-based polling for cluster deletion operations, providing more accurate and reliable deletion tracking.

### How It Works

When deleting a project with clusters:

1. **Initiate deletions**: All clusters in the project are deleted sequentially
2. **Track by status**: Each cluster is monitored individually via its `stateName` field
3. **Poll for completion**: The system polls each cluster's API endpoint every 5 seconds
4. **Detect completion**: A cluster is considered deleted when:
   - The API returns 404 (cluster no longer exists), OR
   - The cluster disappears from the project's cluster list
5. **Verify all deleted**: Only after all clusters are confirmed deleted, the project deletion proceeds

### Advantages Over Timeout-Based Polling

Traditional timeout-based polling simply waits a fixed amount of time and hopes the operation completes. Status-based polling:

* **More accurate**: Monitors actual cluster state (`DELETING`, `IDLE`, etc.)
* **Faster**: Proceeds as soon as deletion completes, not after arbitrary timeout
* **More reliable**: Detects actual deletion via 404 responses
* **Better feedback**: Shows specific status of each cluster being deleted
* **Safety timeout**: Still includes a 10-minute maximum wait as a safety measure

### Progress Updates

During project deletion, you'll see detailed progress messages like:

```
Deleting cluster: cluster-name-1...
Deleting cluster: cluster-name-2...
Waiting for 2 cluster(s) to be deleted: cluster-name-1, cluster-name-2 (15s elapsed)
Waiting for 1 cluster(s) to be deleted: cluster-name-2 (47s elapsed)
All clusters have been deleted successfully
Deleting project...
```

### Error Handling

If a cluster deletion takes longer than 10 minutes, the system will:

1. Report which clusters are still being deleted
2. Throw an error with specific cluster names
3. Suggest waiting a few more minutes before retrying
4. Provide clear guidance on how to proceed

## Exit Server Modal

The web interface includes a convenient exit button in the navigation bar with an integrated shutdown confirmation modal:

### Features

* **Bootstrap Modal Confirmation**: Clean, professional modal dialog instead of browser alerts
* **Detailed Information**: Clear explanation of what will happen during shutdown:
  - Stop the web server
  - Close all active MongoDB Atlas sessions
  - Terminate all background operations
* **Warning Design**: Red header with warning icon to indicate the serious action
* **Visual Feedback**: Beautiful shutdown screen with gradient background and animations
* **Smooth Transitions**: Graceful progression from "Shutting Down..." to "Server Stopped"

### User Experience

1. Click the Exit button in the navigation bar
2. Modal appears with detailed shutdown information
3. Choose to cancel or confirm shutdown
4. On confirmation, see a purple gradient shutdown screen with spinner
5. After shutdown completes, green checkmark confirms success
6. Clean message indicates it's safe to close the browser window

This eliminates the need to find and kill the server process manually while providing a polished, integrated user experience.

## Database-Themed Favicon

AtlasUI features a custom MongoDB-themed favicon with:

* MongoDB's signature green gradient color scheme
* Three-tier database stack icon design
* SVG format for crisp display at any size
* Support for both light and dark browser themes

## Project-Based Filtering

AtlasUI provides powerful filtering capabilities to help you focus on specific projects when viewing all clusters.

### Excel-Style Column Filter

The All Clusters page includes an Excel-style filter for the Project column:

* **Filter Icon**: Click the funnel icon next to "Project" in the table header
* **Dropdown Menu**: Opens a searchable list of all projects with checkboxes
* **Select/Clear All**: Quickly select or deselect all projects
* **Search Box**: Filter the project list by typing
* **Visual Indicator**: The funnel icon turns blue when a filter is active
* **Multiple Selection**: Choose multiple projects to view their clusters simultaneously

### URL-Based Filtering

When clicking a cluster count badge on the Projects page:

* **Automatic Navigation**: Takes you to the All Clusters page
* **Pre-Applied Filter**: Automatically filters to show only that project's clusters
* **URL Parameter**: Uses `?project=ProjectName` in the URL for bookmarkable filters
* **Filter State**: The project filter dropdown reflects the active selection
* **Quick Context Switching**: Easily see all clusters for a specific project

### Using the Filter

1. Navigate to the All Clusters page
2. Click the funnel icon next to "Project"
3. Use the search box to find specific projects (optional)
4. Check/uncheck projects to filter the cluster list
5. Click outside the dropdown to close it
6. Click "Select All" to see all clusters again

Alternatively, from the Projects page:
1. Find a project with clusters
2. Click the blue cluster count badge
3. View filtered clusters for that project only

## IP Access List Management

AtlasUI provides a convenient interface for managing IP access lists (whitelists) for your MongoDB Atlas projects directly from the Projects page.

### Overview

MongoDB Atlas requires IP addresses to be whitelisted before they can connect to clusters. The IP Access List Management feature allows you to:

* View all IP addresses and CIDR blocks currently allowed for a project
* Add new IP addresses or CIDR blocks to the access list
* Remove IP addresses from the access list
* Add optional comments to identify the purpose of each entry

### How to Use

1. Navigate to the Projects page
2. Find the project you want to manage
3. Click the **Manage IP** button (blue shield icon) in the Actions column
4. A modal dialog opens showing the IP management interface

### Adding IP Addresses

In the "Add IP Address" section:

1. Enter an IP address (e.g., `192.168.1.1`) or CIDR block (e.g., `10.0.0.0/24`)
2. Optionally add a comment to describe the entry (e.g., "Office network")
3. Click **Add** to add the entry to the access list

**Note**: Use `0.0.0.0/0` to allow access from anywhere (not recommended for production).

### Removing IP Addresses

In the "Current Access List" section:

1. Find the IP address you want to remove
2. Click the red trash icon in the Actions column
3. Confirm the deletion when prompted

### API Endpoints

The following REST API endpoints are available:

* `GET /api/projects/{project_id}/access-list` - Get all IP access list entries
* `POST /api/projects/{project_id}/access-list` - Add a new IP address or CIDR block
* `DELETE /api/projects/{project_id}/access-list/{entry}` - Remove an IP address

### Request Format (POST)

```json
{
    "ip_address": "192.168.1.1",
    "comment": "Office IP"
}
```

Or for CIDR blocks:

```json
{
    "cidr_block": "10.0.0.0/24",
    "comment": "VPN network"
}
```

### Testing

The IP Access List Management feature includes comprehensive Playwright browser tests in `tests/test_ip_management_ui.py`:

* Modal opening and form element verification
* IP access list loading and display
* Adding IP addresses via the UI
* Deleting IP addresses
* Form validation
* Project name display in modal title

Run the tests with:
```bash
uv run pytest tests/test_ip_management_ui.py -v -s
```

## Responsive UI

The interface is built with Bootstrap 5 and provides:

* Mobile-responsive design
* Real-time updates without page refreshes
* Modern modal dialogs for confirmations
* Clean, professional appearance
* Accessible navigation with icons and labels
