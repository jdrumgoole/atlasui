# AtlasUI - MongoDB Atlas User Interface

A comprehensive user interface for MongoDB Atlas, providing both a web-based UI and CLI tool for managing MongoDB Atlas resources.

## Features

- **Web UI**: FastAPI-based web interface for MongoDB Atlas management
- **CLI Tool**: Command-line interface for Atlas operations
- **Complete API Coverage**: Built from official MongoDB Atlas OpenAPI specifications
- **Modern Stack**: FastAPI, Typer, Rich, and modern Python tooling
- **Secure Authentication**: Supports both API keys (recommended for full functionality) and service accounts (project-scoped only)

## Atlas API Coverage

This UI provides access to all MongoDB Atlas administration APIs including:

- **Clusters**: Create, configure, and manage MongoDB clusters
- **Projects**: Manage Atlas projects and organizations
- **Backup & Restore**: Configure backups and restore operations
- **Alerts**: Set up and manage alert configurations
- **Access Control**: Manage users, roles, and API keys
- **Monitoring**: View metrics and performance data
- **Federation**: Configure identity providers and SSO
- **Network Access**: Manage IP access lists and private endpoints

## Installation

```bash
# Using uv (recommended)
uv pip install -e .

# With development dependencies
uv pip install -e ".[dev]"

# With documentation dependencies
uv pip install -e ".[docs]"

# Or use invoke for setup
inv setup
```

## Configuration

### Option 1: API Key Authentication (Recommended)

**For AtlasUI, API keys are the recommended authentication method** because they provide organization-level access, which is required for this application to work correctly across all organizations, projects, and clusters.

**Setup:**

```bash
cp .env.example .env
# Edit .env and set:
ATLAS_AUTH_METHOD=api_key
ATLAS_PUBLIC_KEY=your_public_key
ATLAS_PRIVATE_KEY=your_private_key
```

**⚠ Important**: Never commit credentials to version control!

### Option 2: Service Account Authentication (Limited Support)

**⚠️ Important Limitation**: Service accounts in MongoDB Atlas are scoped to individual projects, not organizations. Since AtlasUI is designed to manage **all organizations, projects, and clusters** in your Atlas account, service accounts have limited utility for this application.

**When to use service accounts:**
- You only need to manage resources within a single project
- You want OAuth 2.0 authentication for project-specific operations

**Setup (for project-scoped operations only):**

```bash
# Interactive setup wizard
inv configure-service-account

# Manual setup
cp .env.example .env
# Edit .env and set:
ATLAS_AUTH_METHOD=service_account
ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE=/path/to/service-account.json
```

See the [Service Account Documentation](docs/service_accounts.md) for detailed instructions.

**Recommendation**: For full AtlasUI functionality across all organizations and projects, use API key authentication (Option 1).

## Usage

### Web UI

Start the web server:

```bash
# Using invoke
inv run

# Or directly
atlasui-server

# Or with uv
uv run python -m atlasui.server
```

Then open your browser to http://localhost:8000

### CLI Tool

```bash
# List all clusters
atlasui clusters list <project-id>

# Get cluster details
atlasui clusters get <project-id> <cluster-name>

# Create a new cluster
atlasui clusters create --name my-new-cluster --project-id <project-id>

# List projects
atlasui projects list

# View help
atlasui --help
```

## Development

AtlasUI uses [Invoke](https://www.pyinvoke.org/) for task automation.

### Available Tasks

```bash
# See all available tasks
inv --list

# Setup development environment
inv setup

# Install with dev dependencies
inv dev-install

# Run tests
inv test

# Run tests without coverage
inv test --no-coverage

# Format code
inv format

# Check formatting without changes
inv format --check

# Lint code
inv lint

# Run all checks (format, lint, test)
inv check

# Build documentation
inv docs

# Build and open docs in browser
inv docs --open-browser

# Clean build artifacts
inv clean

# Run web server
inv run

# Run with custom host/port
inv run --host=127.0.0.1 --port=8080

# Run with auto-reload
inv run --reload

# Show CLI help
inv cli

# Show version
inv version

# Test Atlas connection
inv info
```

### Common Development Workflows

```bash
# Initial setup
inv setup

# Before committing
inv check

# Making a release
inv release
```

## Documentation

Build the documentation:

```bash
inv docs
```

View the documentation at `docs/_build/html/index.html`

## Project Structure

```
atlasui/
├── atlasui/           # Main package
│   ├── api/          # FastAPI routes and endpoints
│   ├── cli/          # CLI commands
│   ├── client/       # Atlas API client (generated from OpenAPI)
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   ├── static/       # Static files for web UI
│   ├── templates/    # HTML templates
│   └── config.py     # Configuration management
├── tests/            # Test suite
├── docs/             # Sphinx documentation
├── openapi/          # MongoDB Atlas OpenAPI specs
└── tasks.py          # Invoke task definitions
```

## Testing

```bash
# Run all tests
inv test

# Run specific test file
pytest tests/test_client.py

# Run with verbose output
inv test --verbose

# Generate coverage report
inv test --coverage
```

## API Access

The web server exposes RESTful APIs at:

- **Root**: http://localhost:8000/
- **Health**: http://localhost:8000/health
- **Projects**: http://localhost:8000/api/projects/
- **Clusters**: http://localhost:8000/api/clusters/{project_id}
- **Alerts**: http://localhost:8000/api/alerts/{project_id}
- **Backups**: http://localhost:8000/api/backups/{project_id}/{cluster_name}/snapshots
- **Interactive Docs**: http://localhost:8000/docs

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for details.

## Quick Links

- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [Contributing Guide](CONTRIBUTING.md) - Development guidelines
- [MongoDB Atlas API Docs](https://www.mongodb.com/docs/atlas/reference/api-resources-spec/)
- [MongoDB Atlas OpenAPI Specs](https://github.com/mongodb/openapi)
