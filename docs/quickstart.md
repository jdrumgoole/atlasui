# Quick Start

This guide will help you get started with AtlasUI quickly.

## Web Interface

### Starting the Server

```bash
# Start the web server
atlasui start

# Or with custom port
atlasui start --port 8080

# Or use the PORT environment variable
PORT=8080 atlasui start
```

Then open your browser to http://localhost:8000

### Using the Dashboard

The dashboard provides an overview of your Atlas resources:

* Organizations and projects
* Cluster status across projects
* Cluster details and management
* Database user management

## Command-Line Interface

### List Projects

```bash
# List all projects
atlasui projects list

# List with pagination
atlasui projects list --page 2 --limit 50
```

### Get Project Details

```bash
# Get specific project
atlasui projects get <project-id>
```

### Manage Clusters

```bash
# List clusters in a project
atlasui clusters list <project-id>

# Get cluster details
atlasui clusters get <project-id> <cluster-name>

# Get cluster details as JSON
atlasui clusters get <project-id> <cluster-name> --json
```

## API Usage

You can also use the Atlas client programmatically:

```python
from atlasui.client import AtlasClient

# Create client
with AtlasClient() as client:
    # List projects
    projects = client.list_projects()
    print(projects)

    # Get a project
    project = client.get_project('project-id')
    print(project)

    # List clusters
    clusters = client.list_clusters('project-id')
    print(clusters)

    # Get a cluster
    cluster = client.get_cluster('project-id', 'cluster-name')
    print(cluster)
```

## Next Steps

* Read the full API documentation
* Learn about available CLI commands
* Explore [service account authentication](service_accounts.md)
* Review [security guidelines](security.md)
