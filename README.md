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
# Install from PyPI
pip install atlasui

# Or install from source
pip install -e .

# With development dependencies
pip install -e ".[dev]"

# With documentation dependencies
pip install -e ".[docs]"
```

## Configuration

AtlasUI provides an interactive configuration tool that guides you through the setup process.

### Quick Setup (Recommended)

Run the interactive configuration wizard:

```bash
atlasui-configure
```

This wizard will:
- Help you choose between API Keys (recommended) and Service Accounts
- Explain the limitations and benefits of each method
- Guide you through entering your credentials
- Create and configure your `.env` file automatically
- Test your connection to verify everything works

### Authentication Methods

#### API Keys (Recommended) ⭐

**Best for:** Full AtlasUI functionality

API keys provide **organization-level** access, allowing AtlasUI to:
- Manage all organizations in your Atlas account
- Access all projects across organizations
- Control all clusters across all projects

**Quick start:**
```bash
atlasui-configure
# Choose option 1 (API Keys)
# Follow the wizard instructions
```

**How to get API keys:**
1. Go to https://cloud.mongodb.com
2. Organization → Access Manager → API Keys
3. Create API Key with Organization Owner permissions
4. Copy Public Key and Private Key

#### Service Accounts (Limited) ⚠️

**Best for:** Single project operations only

**⚠️ Important Limitation**: Service accounts are **project-scoped** - each can only access ONE project.

Since AtlasUI needs organization-level access, service accounts have **limited utility**.

**Only use service accounts if:**
- You only need to manage a single specific project
- You prefer OAuth 2.0 authentication
- You understand you won't have full AtlasUI functionality

**Setup:**
```bash
atlasui-configure
# Choose option 2 (Service Account)
# Follow the wizard (will warn about limitations)
```

See [Service Account Documentation](docs/service_accounts.md) for details.

### Manual Configuration

If you prefer to configure manually:

**For API Keys:**
```bash
cp .env.example .env
# Edit .env and set:
ATLAS_AUTH_METHOD=api_key
ATLAS_PUBLIC_KEY=your_public_key
ATLAS_PRIVATE_KEY=your_private_key
```

**⚠ Important**: Never commit credentials to version control!

## Usage

### Web UI

Start the web server:

```bash
atlasui-server
```

Then open your browser to http://localhost:8000

The server can also be started with custom options:

```bash
# Custom host and port
uvicorn atlasui.server:app --host 0.0.0.0 --port 8080

# With auto-reload for development
uvicorn atlasui.server:app --reload
```

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

For developers working on AtlasUI, the project uses [Invoke](https://www.pyinvoke.org/) for task automation.

### Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Or use invoke
inv setup
```

### Running Tests

```bash
# Run all tests
inv test

# Run tests without coverage
inv test --no-coverage

# Or use pytest directly
pytest
pytest --cov=atlasui --cov-report=html
```

### Code Quality

```bash
# Format code
inv format

# Check formatting without changes
inv format --check

# Lint code
inv lint

# Run all checks (format, lint, test)
inv check

# Or use tools directly
black atlasui tests
ruff check atlasui tests
mypy atlasui
```

### Building Documentation

```bash
# Build docs with invoke
inv docs

# Build and open in browser
inv docs --open-browser

# Or build directly with Sphinx
cd docs
sphinx-build -b html . _build/html
```

### Other Development Tasks

```bash
# Run development server
inv run

# Run with custom host/port
inv run --host=0.0.0.0 --port=8080

# Clean build artifacts
inv clean

# Show version
inv version
```

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

---

## Built with Claude

This project was built with assistance from [Claude](https://claude.ai), Anthropic's AI assistant.
