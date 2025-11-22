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

* **Create Cluster**: Creating new MongoDB clusters (M0, M10, M30, etc.)
* **Delete Cluster**: Removing clusters from a project
* **Delete Project**: Cascading deletion of projects with all associated clusters

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

## Exit Server Button

The web interface includes a convenient exit button in the navigation bar that:

* Safely shuts down the AtlasUI server
* Closes all active MongoDB sessions
* Displays a shutdown confirmation page
* Asks for confirmation before shutting down

This eliminates the need to find and kill the server process manually.

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
