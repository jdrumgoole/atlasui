# AtlasUI Quick Start Guide

Get up and running with AtlasUI in 5 minutes!

## Prerequisites

- Python 3.11+
- MongoDB Atlas account
- Atlas API keys ([Get them here](https://cloud.mongodb.com/v2#/account/publicApi))

## Installation

```bash
# Quick setup (recommended)
inv setup

# Or install manually using uv
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Atlas API credentials:
```bash
ATLAS_PUBLIC_KEY=your_public_key_here
ATLAS_PRIVATE_KEY=your_private_key_here
```

## Test Your Setup

```bash
# Test CLI connection
inv info

# Or directly
uv run atlasui info

# List your projects
uv run atlasui projects list
```

## Start the Web UI

```bash
# Start the web server
inv run

# Or with auto-reload for development
inv run --reload

# Or directly
uv run python -m atlasui.server
```

Open your browser to: http://localhost:8000

## Common CLI Commands

```bash
# Projects
atlasui projects list
atlasui projects get <project-id>

# Clusters
atlasui clusters list <project-id>
atlasui clusters get <project-id> <cluster-name>
atlasui clusters delete <project-id> <cluster-name>

# Alerts
atlasui alerts list <project-id>

# Backups
atlasui backups list <project-id> <cluster-name>
atlasui backups schedule <project-id> <cluster-name>
```

## Development

```bash
# Run tests
inv test

# Format code
inv format

# Build docs
inv docs

# See all commands
inv --list
```

## API Access

The web server exposes RESTful APIs at:

- Projects: http://localhost:8000/api/projects/
- Clusters: http://localhost:8000/api/clusters/{project_id}
- Alerts: http://localhost:8000/api/alerts/{project_id}
- Backups: http://localhost:8000/api/backups/{project_id}/{cluster_name}/snapshots

View interactive API docs: http://localhost:8000/docs

## Need Help?

- Check the full documentation: `inv docs`
- View README: [README.md](README.md)
- See contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- List all commands: `inv --list`

## Troubleshooting

### Authentication Errors

Make sure your `.env` file has valid Atlas API keys:
```bash
inv info  # Test your connection
```

### Module Not Found

Make sure you installed the package:
```bash
uv pip install -e .
```

### Port Already in Use

Change the port in your `.env`:
```bash
PORT=8080
```

## What's Next?

- Explore the web dashboard
- Try different CLI commands
- Read the API documentation
- Check out the full docs for advanced features
