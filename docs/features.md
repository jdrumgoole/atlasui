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
* **Delete Project**: Cascading deletion of projects with all associated clusters (includes automatic deletion of all associated clusters)

### Auto-Refresh on Completion

The UI automatically refreshes resource lists when operations complete:

* **Project creation**: When a project is successfully created, it automatically appears in the projects list
* **Cluster creation**: When a cluster is successfully created, it automatically appears in the clusters list
* **Project deletion**: Deleted projects are immediately removed from the list (optimistic update)
* **Cluster deletion**: Deleted clusters are immediately removed from the list (optimistic update)

This eliminates the need for manual page refreshes while maintaining a responsive user experience.

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

## Responsive UI

The interface is built with Bootstrap 5 and provides:

* Mobile-responsive design
* Real-time updates without page refreshes
* Modern modal dialogs for confirmations
* Clean, professional appearance
* Accessible navigation with icons and labels
