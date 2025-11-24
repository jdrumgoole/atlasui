/**
 * Backend Operation Stream Manager
 * Connects to SSE stream and displays real-time operation updates
 */

class SSEOperationManager {
    constructor() {
        this.operations = new Map();
        this.listeners = [];
        this.eventSource = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.currentReconnectDelay = this.reconnectDelay;
        this.isConnected = false;
    }

    /**
     * Connect to the SSE stream
     */
    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        console.log('Connecting to operation stream...');

        this.eventSource = new EventSource('/api/operations/stream');

        // Handle initial state
        this.eventSource.addEventListener('init', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('init', operation);
        });

        // Handle queued events
        this.eventSource.addEventListener('queued', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('queued', operation);
        });

        // Handle started events
        this.eventSource.addEventListener('started', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('started', operation);
        });

        // Handle progress events
        this.eventSource.addEventListener('progress', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('progress', operation);
        });

        // Handle completed events
        this.eventSource.addEventListener('completed', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('completed', operation);
        });

        // Handle failed events
        this.eventSource.addEventListener('failed', (event) => {
            const operation = JSON.parse(event.data);
            this.operations.set(operation.id, operation);
            this.notifyListeners('failed', operation);
        });

        // Handle connection open
        this.eventSource.onopen = () => {
            console.log('Connected to operation stream');
            this.isConnected = true;
            this.currentReconnectDelay = this.reconnectDelay;
            this.notifyListeners('connected', null);
        };

        // Handle errors
        this.eventSource.onerror = (error) => {
            console.error('SSE connection error:', error);
            this.isConnected = false;
            this.eventSource.close();
            this.notifyListeners('disconnected', null);

            // Attempt to reconnect with exponential backoff
            setTimeout(() => {
                this.connect();
            }, this.currentReconnectDelay);

            this.currentReconnectDelay = Math.min(
                this.currentReconnectDelay * 2,
                this.maxReconnectDelay
            );
        };
    }

    /**
     * Disconnect from the SSE stream
     */
    disconnect() {
        if (this.eventSource) {
            console.log('Disconnecting from operation stream');
            this.eventSource.close();
            this.eventSource = null;
            this.isConnected = false;
        }
    }

    /**
     * Register a listener for operation events
     * @param {Function} callback - Callback function (event, operation)
     */
    addListener(callback) {
        this.listeners.push(callback);
    }

    /**
     * Remove a listener
     * @param {Function} callback - Callback function to remove
     */
    removeListener(callback) {
        this.listeners = this.listeners.filter(l => l !== callback);
    }

    /**
     * Notify all listeners of an event
     */
    notifyListeners(event, operation) {
        this.listeners.forEach(callback => {
            try {
                callback(event, operation, this);
            } catch (err) {
                console.error('Error in operation manager listener:', err);
            }
        });
    }

    /**
     * Get all operations
     */
    getAllOperations() {
        return Array.from(this.operations.values());
    }

    /**
     * Get operation by ID
     */
    getOperation(id) {
        return this.operations.get(id);
    }

    /**
     * Clear a completed or failed operation
     */
    async clearOperation(operationId) {
        try {
            const response = await fetch(`/api/operations/${operationId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.operations.delete(operationId);
                this.notifyListeners('cleared', { id: operationId });
                return true;
            }
            return false;
        } catch (err) {
            console.error('Error clearing operation:', err);
            return false;
        }
    }

    /**
     * Get current status
     */
    getStatus() {
        const operations = this.getAllOperations();
        return {
            totalOperations: operations.length,
            queued: operations.filter(op => op.status === 'queued').length,
            inProgress: operations.filter(op => op.status === 'in-progress').length,
            completed: operations.filter(op => op.status === 'completed').length,
            failed: operations.filter(op => op.status === 'failed').length,
            isConnected: this.isConnected
        };
    }
}

// Create global instance
window.operationManager = new SSEOperationManager();


/**
 * Operation Queue UI Component
 * Displays operations at the bottom of the screen
 */
class OperationQueueUI {
    constructor(manager) {
        this.manager = manager;
        this.panel = null;
        this.isExpanded = false;
        this.autoScroll = true;
        this.init();
    }

    init() {
        // Create the UI panel
        this.createPanel();

        // Listen to operation events
        this.manager.addListener((event, operation, manager) => {
            this.handleOperationEvent(event, operation, manager);
        });

        // Auto-collapse after 10 seconds of inactivity
        this.setupAutoCollapse();

        // Update elapsed time for in-progress operations every second
        this.startElapsedTimeUpdater();

        // Connect to SSE stream
        this.manager.connect();
    }

    startElapsedTimeUpdater() {
        // Update every second to show elapsed time
        setInterval(() => {
            const operations = this.manager.getAllOperations();
            const hasInProgress = operations.some(op => op.status === 'in-progress');

            if (hasInProgress && this.isExpanded) {
                this.renderOperations();
            }
        }, 1000);
    }

    formatElapsedTime(startTime) {
        const start = new Date(startTime);
        const now = new Date();
        const elapsed = Math.floor((now - start) / 1000); // seconds

        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;

        if (minutes > 0) {
            return `${minutes}m ${seconds}s`;
        }
        return `${seconds}s`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'operationQueuePanel';
        panel.className = 'operation-queue-panel collapsed';
        panel.innerHTML = `
            <div class="operation-queue-header" onclick="operationQueueUI.toggle()">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="bi bi-list-task"></i>
                        <span class="ms-2">Operations</span>
                        <span class="badge bg-warning ms-2" id="opQueueCount">0</span>
                        <span class="badge bg-success ms-1" id="opCompletedCount">0</span>
                        <span class="badge bg-danger ms-1" id="opFailedCount">0</span>
                        <span class="connection-status ms-2" id="connectionStatus">
                            <i class="bi bi-circle-fill text-secondary"></i>
                        </span>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-link text-white" onclick="event.stopPropagation(); operationQueueUI.clearCompleted()">
                            <i class="bi bi-trash"></i> Clear
                        </button>
                        <i class="bi bi-chevron-up" id="opQueueChevron"></i>
                    </div>
                </div>
            </div>
            <div class="operation-queue-body" id="operationQueueBody">
                <div class="operation-list" id="operationList">
                    <div class="text-muted text-center py-3">No operations yet</div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);
        this.panel = panel;

        // Add CSS styles
        this.addStyles();
    }

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .operation-queue-panel {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100%;
                max-width: 100vw;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
                z-index: 1000;
                transition: transform 0.3s ease;
                overflow-x: hidden;
                overflow-y: hidden;
            }

            .operation-queue-panel.collapsed {
                transform: translateY(calc(100% - 50px));
            }

            .operation-queue-header {
                padding: 12px 20px;
                cursor: pointer;
                user-select: none;
                border-bottom: 1px solid rgba(255,255,255,0.2);
            }

            .operation-queue-header:hover {
                background: rgba(255,255,255,0.1);
            }

            .operation-queue-body {
                max-height: 400px;
                overflow-y: auto;
                overflow-x: hidden;
                padding: 10px 20px;
            }

            .operation-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .operation-item {
                background: rgba(255,255,255,0.1);
                border-radius: 6px;
                padding: 12px;
                border-left: 4px solid;
                word-wrap: break-word;
                overflow-wrap: break-word;
                max-width: 100%;
                width: 100%;
                box-sizing: border-box;
                overflow: hidden;
                contain: layout style paint;
                min-width: 0;
            }

            .operation-item.queued {
                border-left-color: #ffc107;
            }

            .operation-item.in-progress {
                border-left-color: #17a2b8;
            }

            .operation-item.completed {
                border-left-color: #28a745;
            }

            .operation-item.failed {
                border-left-color: #dc3545;
            }

            .operation-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
                width: 100%;
                max-width: 100%;
                overflow: hidden;
                min-width: 0;
            }

            .operation-name {
                font-weight: 500;
                font-size: 14px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: 70%;
                min-width: 0;
                flex-shrink: 1;
            }

            .operation-actions {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
            }

            .operation-status {
                font-size: 11px;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 0.5px;
                white-space: nowrap;
                flex-shrink: 0;
                padding: 3px 8px;
                border-radius: 4px;
                margin-right: 10px;
            }

            .operation-status.status-queued {
                background: rgba(255, 193, 7, 0.3);
                color: #fff;
                background-color: #ffc107;
                border: 1px solid #ffc107;
            }

            .operation-status.status-in-progress {
                background: rgba(13, 110, 253, 0.3);
                color: #fff;
                background-color: #0d6efd;
                border: 1px solid #0d6efd;
            }

            .operation-status.status-completed {
                background: rgba(25, 135, 84, 0.3);
                color: #fff;
                background-color: #28a745;
                border: 1px solid #28a745;
            }

            .operation-status.status-failed {
                background: rgba(220, 53, 69, 0.3);
                color: #fff;
                background-color: #dc3545;
                border: 1px solid #dc3545;
            }

            .operation-clear-btn {
                background: transparent;
                border: none;
                color: rgba(255,255,255,0.6);
                cursor: pointer;
                padding: 2px 6px;
                font-size: 16px;
                line-height: 1;
                border-radius: 3px;
                transition: all 0.2s ease;
            }

            .operation-clear-btn:hover {
                background: rgba(255,255,255,0.1);
                color: rgba(255,255,255,0.9);
            }

            .operation-clear-btn:active {
                transform: scale(0.95);
            }

            .operation-progress {
                font-size: 12px;
                opacity: 0.9;
                margin-top: 4px;
                word-wrap: break-word;
                overflow-wrap: break-word;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                max-width: 100%;
                min-width: 0;
            }

            .operation-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
                white-space: nowrap;
            }

            .operation-error {
                background: rgba(220,53,69,0.2);
                padding: 8px;
                border-radius: 4px;
                margin-top: 8px;
                font-size: 12px;
                word-wrap: break-word;
                overflow-wrap: break-word;
                overflow: hidden;
            }

            .connection-status {
                display: inline-block;
                font-size: 8px;
            }

            .connection-status .bi-circle-fill.text-success {
                /* Connection indicator - no animation for stability */
            }

            .progress-bar-container {
                width: 100%;
                max-width: 100%;
                height: 4px;
                background: rgba(255,255,255,0.2);
                border-radius: 2px;
                margin-top: 6px;
                overflow: hidden;
                position: relative;
                contain: layout style paint;
            }

            .progress-bar {
                height: 100%;
                background: rgba(255,255,255,0.5);
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
            }

            .progress-bar.indeterminate {
                width: 100%;
            }
        `;
        document.head.appendChild(style);
    }

    handleOperationEvent(event, operation, manager) {
        const status = manager.getStatus();
        this.updateCounts(status);
        this.updateConnectionStatus(status.isConnected);

        if (event === 'init' || event === 'queued' || event === 'started' || event === 'progress' || event === 'completed' || event === 'failed') {
            this.renderOperations();

            // Auto-expand on new operation or status change
            if (event === 'queued' || event === 'started') {
                this.expand();
                this.resetAutoCollapse();
            }

            // Refresh cluster list when cluster operations start (to show CREATING status) or complete/fail
            // Note: We don't refresh on 'progress' to avoid constant reloading
            if ((event === 'started' || event === 'completed' || event === 'failed') && operation) {
                const clusterOperationTypes = ['create_cluster', 'delete_cluster', 'create_flex_cluster', 'delete_flex_cluster'];
                const deleteOperationTypes = ['delete_cluster', 'delete_flex_cluster'];

                if (clusterOperationTypes.includes(operation.type)) {
                    // Track delete operations to manually show DELETING status
                    if (deleteOperationTypes.includes(operation.type)) {
                        if (event === 'started') {
                            // Mark cluster as being deleted
                            const projectId = operation.metadata?.project_id;
                            const clusterName = operation.metadata?.cluster_name;
                            if (projectId && clusterName && typeof window.markClusterDeleting === 'function') {
                                window.markClusterDeleting(projectId, clusterName);
                            }
                        } else if (event === 'completed' || event === 'failed') {
                            // Unmark cluster as being deleted
                            const projectId = operation.metadata?.project_id;
                            const clusterName = operation.metadata?.cluster_name;
                            if (projectId && clusterName && typeof window.unmarkClusterDeleting === 'function') {
                                window.unmarkClusterDeleting(projectId, clusterName);
                            }
                        }
                    }

                    // Call loadClusters() if it exists (we're on the clusters page)
                    if (typeof window.loadClusters === 'function') {
                        console.log(`Cluster operation ${operation.type} ${event}, refreshing cluster list...`);

                        // For completed operations and started delete operations, add a small delay and refresh twice
                        // to ensure Atlas API has fully propagated the status change
                        if (event === 'completed' || (event === 'started' && deleteOperationTypes.includes(operation.type))) {
                            // Immediate refresh
                            window.loadClusters();
                            // Second refresh after 2 seconds to catch any delayed status updates
                            setTimeout(() => {
                                console.log(`Second refresh for ${operation.type} to ensure status is updated...`);
                                window.loadClusters();
                            }, 2000);
                        } else {
                            window.loadClusters();
                        }
                    }
                }
            }
        }

        if (event === 'cleared') {
            this.renderOperations();
            this.updateCounts(manager.getStatus());
        }

        if (event === 'connected') {
            this.updateConnectionStatus(true);
        }

        if (event === 'disconnected') {
            this.updateConnectionStatus(false);
        }
    }

    updateCounts(status) {
        document.getElementById('opQueueCount').textContent = status.queued + status.inProgress;
        document.getElementById('opCompletedCount').textContent = status.completed;
        document.getElementById('opFailedCount').textContent = status.failed;
    }

    updateConnectionStatus(isConnected) {
        const statusEl = document.getElementById('connectionStatus');
        if (isConnected) {
            statusEl.innerHTML = '<i class="bi bi-circle-fill text-success"></i>';
            statusEl.title = 'Connected to operation stream';
        } else {
            statusEl.innerHTML = '<i class="bi bi-circle-fill text-warning"></i>';
            statusEl.title = 'Reconnecting to operation stream...';
        }
    }

    renderOperations() {
        const list = document.getElementById('operationList');
        const operations = this.manager.getAllOperations()
            .sort((a, b) => b.id - a.id) // Sort by ID descending (newest first)
            .slice(0, 10); // Show last 10

        if (operations.length === 0) {
            list.innerHTML = '<div class="text-muted text-center py-3">No operations yet</div>';
            return;
        }

        list.innerHTML = operations.map(op => this.renderOperation(op)).join('');

        if (this.autoScroll && this.isExpanded) {
            const body = document.getElementById('operationQueueBody');
            body.scrollTop = 0; // Scroll to top to see newest
        }
    }

    renderOperation(op) {
        const startedAt = op.startedAt ? new Date(op.startedAt) : null;
        const completedAt = op.completedAt ? new Date(op.completedAt) : null;

        const duration = completedAt && startedAt ?
            ((completedAt - startedAt) / 1000).toFixed(1) + 's' : '';

        const progress = op.progress ?
            `<div class="operation-progress">${this.escapeHtml(op.progress)}</div>` : '';

        const error = op.error ?
            `<div class="operation-error"><i class="bi bi-exclamation-triangle"></i> ${this.escapeHtml(op.error)}</div>` : '';

        const progressBar = op.status === 'in-progress' ?
            `<div class="progress-bar-container"><div class="progress-bar indeterminate"></div></div>` : '';

        // Show elapsed time for in-progress operations
        const elapsedTime = (op.status === 'in-progress' && op.startedAt) ?
            `<div class="operation-time">Elapsed: ${this.formatElapsedTime(op.startedAt)}</div>` : '';

        const statusIcon = {
            'queued': '<i class="bi bi-clock-history"></i>',
            'in-progress': '<i class="bi bi-arrow-repeat"></i>',
            'completed': '<i class="bi bi-check-circle"></i>',
            'failed': '<i class="bi bi-x-circle"></i>'
        }[op.status] || '';

        // Show clear button for completed or failed operations
        const clearButton = (op.status === 'completed' || op.status === 'failed') ?
            `<button class="operation-clear-btn" onclick="window.operationQueueUI.clearOperation(${op.id})" title="Clear this operation">
                <i class="bi bi-x"></i>
            </button>` : '';

        // Update operation name text based on status (e.g., "Creating cluster" -> "Cluster created")
        let displayName = op.name;
        if (op.status === 'completed') {
            displayName = displayName
                .replace(/^Creating cluster:/i, 'Cluster created:')
                .replace(/^Creating Flex cluster:/i, 'Flex cluster created:')
                .replace(/^Deleting cluster:/i, 'Cluster deleted:')
                .replace(/^Deleting Flex cluster:/i, 'Flex cluster deleted:')
                .replace(/^Deleting project:/i, 'Project deleted:')
                .replace(/^Creating project:/i, 'Project created:');
        }

        return `
            <div class="operation-item ${op.status}">
                <div class="operation-header">
                    <div class="operation-status status-${op.status}">${statusIcon} ${op.status}</div>
                    <div class="operation-name">${this.escapeHtml(displayName)}</div>
                    <div class="operation-actions">
                        ${clearButton}
                    </div>
                </div>
                ${progress}
                ${progressBar}
                ${error}
                ${elapsedTime}
                ${duration ? `<div class="operation-time">Completed in ${duration}</div>` : ''}
            </div>
        `;
    }

    toggle() {
        if (this.isExpanded) {
            this.collapse();
        } else {
            this.expand();
        }
    }

    expand() {
        this.isExpanded = true;
        this.panel.classList.remove('collapsed');
        document.getElementById('opQueueChevron').className = 'bi bi-chevron-down';
    }

    collapse() {
        this.isExpanded = false;
        this.panel.classList.add('collapsed');
        document.getElementById('opQueueChevron').className = 'bi bi-chevron-up';
    }

    async clearCompleted() {
        const operations = this.manager.getAllOperations();
        const completedOrFailed = operations.filter(
            op => op.status === 'completed' || op.status === 'failed'
        );

        for (const op of completedOrFailed) {
            await this.manager.clearOperation(op.id);
        }

        this.renderOperations();
        this.updateCounts(this.manager.getStatus());
    }

    setupAutoCollapse() {
        this.autoCollapseTimer = null;
    }

    resetAutoCollapse() {
        if (this.autoCollapseTimer) {
            clearTimeout(this.autoCollapseTimer);
        }

        this.autoCollapseTimer = setTimeout(() => {
            const status = this.manager.getStatus();
            if (status.queued === 0 && status.inProgress === 0) {
                this.collapse();
            }
        }, 10000); // Collapse after 10 seconds of inactivity
    }

    async clearOperation(operationId) {
        const success = await this.manager.clearOperation(operationId);
        if (success) {
            console.log(`Operation ${operationId} cleared`);
        } else {
            console.error(`Failed to clear operation ${operationId}`);
        }
    }
}

// Initialize UI when DOM is ready
console.log('[OperationQueue] Script loaded, adding DOMContentLoaded listener');
document.addEventListener('DOMContentLoaded', () => {
    console.log('[OperationQueue] DOMContentLoaded fired');
    console.log('[OperationQueue] window.operationManager:', window.operationManager);

    try {
        window.operationQueueUI = new OperationQueueUI(window.operationManager);
        console.log('[OperationQueue] operationQueueUI initialized successfully');
    } catch (error) {
        console.error('[OperationQueue] Failed to initialize operationQueueUI:', error);
    }
});
