/**
 * Operation Queue Manager
 * Handles queuing and sequential processing of API operations
 */

class OperationQueue {
    constructor() {
        this.queue = [];
        this.currentOperation = null;
        this.isProcessing = false;
        this.operationHistory = [];
        this.listeners = [];
        this.operationId = 0;
    }

    /**
     * Add an operation to the queue
     * @param {Object} operation - Operation details
     * @param {string} operation.type - Type of operation (e.g., 'delete_project', 'create_cluster')
     * @param {string} operation.name - Display name of the operation
     * @param {Function} operation.execute - Async function to execute the operation
     * @param {Object} operation.metadata - Additional metadata about the operation
     * @returns {number} Operation ID
     */
    enqueue(operation) {
        const op = {
            id: ++this.operationId,
            type: operation.type,
            name: operation.name,
            execute: operation.execute,
            metadata: operation.metadata || {},
            status: 'queued',
            progress: null,
            result: null,
            error: null,
            queuedAt: new Date(),
            startedAt: null,
            completedAt: null
        };

        this.queue.push(op);
        this.operationHistory.push(op);
        this.notifyListeners('queued', op);

        // Start processing if not already processing
        if (!this.isProcessing) {
            this.processQueue();
        }

        return op.id;
    }

    /**
     * Process the queue sequentially
     */
    async processQueue() {
        if (this.isProcessing || this.queue.length === 0) {
            return;
        }

        this.isProcessing = true;

        while (this.queue.length > 0) {
            const operation = this.queue[0];
            this.currentOperation = operation;

            try {
                // Update status to in-progress
                operation.status = 'in-progress';
                operation.startedAt = new Date();
                this.notifyListeners('started', operation);

                // Execute the operation
                const result = await operation.execute((progress) => {
                    // Progress callback
                    operation.progress = progress;
                    this.notifyListeners('progress', operation);
                });

                // Mark as completed
                operation.status = 'completed';
                operation.result = result;
                operation.completedAt = new Date();
                this.notifyListeners('completed', operation);

            } catch (error) {
                // Mark as failed
                operation.status = 'failed';
                operation.error = error.message || 'Unknown error';
                operation.completedAt = new Date();
                this.notifyListeners('failed', operation);
            }

            // Remove from queue
            this.queue.shift();
            this.currentOperation = null;
        }

        this.isProcessing = false;
        this.notifyListeners('queue_empty', null);
    }

    /**
     * Register a listener for queue events
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
                console.error('Error in operation queue listener:', err);
            }
        });
    }

    /**
     * Get all operations in history
     */
    getHistory() {
        return [...this.operationHistory];
    }

    /**
     * Get current queue status
     */
    getStatus() {
        return {
            queueLength: this.queue.length,
            isProcessing: this.isProcessing,
            currentOperation: this.currentOperation,
            historyLength: this.operationHistory.length
        };
    }

    /**
     * Clear completed operations from history
     */
    clearHistory() {
        this.operationHistory = this.operationHistory.filter(
            op => op.status === 'queued' || op.status === 'in-progress'
        );
        this.notifyListeners('history_cleared', null);
    }
}

// Create global instance
window.operationQueue = new OperationQueue();


/**
 * Operation Queue UI Component
 * Displays operations at the bottom of the screen
 */
class OperationQueueUI {
    constructor(queue) {
        this.queue = queue;
        this.panel = null;
        this.isExpanded = false;
        this.autoScroll = true;
        this.init();
    }

    init() {
        // Create the UI panel
        this.createPanel();

        // Listen to queue events
        this.queue.addListener((event, operation, queue) => {
            this.handleQueueEvent(event, operation, queue);
        });

        // Auto-collapse after 5 seconds of inactivity
        this.setupAutoCollapse();
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
                        <span class="badge bg-primary ms-2" id="opQueueCount">0</span>
                        <span class="badge bg-success ms-1" id="opCompletedCount">0</span>
                        <span class="badge bg-danger ms-1" id="opFailedCount">0</span>
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
                z-index: 1000;
                transition: transform 0.3s ease;
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
                transition: all 0.3s ease;
            }

            .operation-item.queued {
                border-left-color: #ffc107;
            }

            .operation-item.in-progress {
                border-left-color: #17a2b8;
                animation: pulse 1.5s ease-in-out infinite;
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
            }

            .operation-name {
                font-weight: 500;
                font-size: 14px;
            }

            .operation-status {
                font-size: 11px;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 0.5px;
            }

            .operation-progress {
                font-size: 12px;
                opacity: 0.9;
                margin-top: 4px;
            }

            .operation-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
            }

            .operation-error {
                background: rgba(220,53,69,0.2);
                padding: 8px;
                border-radius: 4px;
                margin-top: 8px;
                font-size: 12px;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            .progress-bar-container {
                width: 100%;
                height: 4px;
                background: rgba(255,255,255,0.2);
                border-radius: 2px;
                margin-top: 6px;
                overflow: hidden;
            }

            .progress-bar {
                height: 100%;
                background: rgba(255,255,255,0.8);
                transition: width 0.3s ease;
            }

            .progress-bar.indeterminate {
                width: 30%;
                animation: indeterminate 1.5s ease-in-out infinite;
            }

            @keyframes indeterminate {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(400%); }
            }
        `;
        document.head.appendChild(style);
    }

    handleQueueEvent(event, operation, queue) {
        const status = queue.getStatus();
        this.updateCounts(status);

        if (event === 'queued' || event === 'started' || event === 'progress' || event === 'completed' || event === 'failed') {
            this.renderOperations();

            // Auto-expand on new operation or status change
            if (event === 'queued' || event === 'started') {
                this.expand();
                this.resetAutoCollapse();
            }
        }

        if (event === 'queue_empty') {
            // Auto-collapse after queue is empty
            this.resetAutoCollapse();
        }
    }

    updateCounts(status) {
        const history = this.queue.getHistory();
        const queued = history.filter(op => op.status === 'queued' || op.status === 'in-progress').length;
        const completed = history.filter(op => op.status === 'completed').length;
        const failed = history.filter(op => op.status === 'failed').length;

        document.getElementById('opQueueCount').textContent = queued;
        document.getElementById('opCompletedCount').textContent = completed;
        document.getElementById('opFailedCount').textContent = failed;
    }

    renderOperations() {
        const list = document.getElementById('operationList');
        const history = this.queue.getHistory().slice(-10).reverse(); // Show last 10, newest first

        if (history.length === 0) {
            list.innerHTML = '<div class="text-muted text-center py-3">No operations yet</div>';
            return;
        }

        list.innerHTML = history.map(op => this.renderOperation(op)).join('');

        if (this.autoScroll && this.isExpanded) {
            const body = document.getElementById('operationQueueBody');
            body.scrollTop = 0; // Scroll to top to see newest
        }
    }

    renderOperation(op) {
        const duration = op.completedAt && op.startedAt ?
            ((op.completedAt - op.startedAt) / 1000).toFixed(1) + 's' : '';

        const progress = op.progress ?
            `<div class="operation-progress">${op.progress}</div>` : '';

        const error = op.error ?
            `<div class="operation-error"><i class="bi bi-exclamation-triangle"></i> ${op.error}</div>` : '';

        const progressBar = op.status === 'in-progress' ?
            `<div class="progress-bar-container"><div class="progress-bar indeterminate"></div></div>` : '';

        const statusIcon = {
            'queued': '<i class="bi bi-clock-history"></i>',
            'in-progress': '<i class="bi bi-arrow-repeat"></i>',
            'completed': '<i class="bi bi-check-circle"></i>',
            'failed': '<i class="bi bi-x-circle"></i>'
        }[op.status] || '';

        return `
            <div class="operation-item ${op.status}">
                <div class="operation-header">
                    <div class="operation-name">${op.name}</div>
                    <div class="operation-status">${statusIcon} ${op.status}</div>
                </div>
                ${progress}
                ${progressBar}
                ${error}
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

    clearCompleted() {
        this.queue.clearHistory();
        this.renderOperations();
        this.updateCounts(this.queue.getStatus());
    }

    setupAutoCollapse() {
        this.autoCollapseTimer = null;
    }

    resetAutoCollapse() {
        if (this.autoCollapseTimer) {
            clearTimeout(this.autoCollapseTimer);
        }

        this.autoCollapseTimer = setTimeout(() => {
            if (this.queue.getStatus().queueLength === 0) {
                this.collapse();
            }
        }, 10000); // Collapse after 10 seconds of inactivity
    }
}

// Initialize UI when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.operationQueueUI = new OperationQueueUI(window.operationQueue);
});
