# AtlasUI - MongoDB Atlas User Interface

[![Tests](https://github.com/jdrumgoole/atlasui/actions/workflows/tests.yml/badge.svg)](https://github.com/jdrumgoole/atlasui/actions/workflows/tests.yml)
[![PyPI version](https://badge.fury.io/py/atlasui.svg)](https://badge.fury.io/py/atlasui)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Documentation Status](https://readthedocs.org/projects/atlasui/badge/?version=latest)](https://atlasui.readthedocs.io/en/latest/?badge=latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive user interface for MongoDB Atlas, providing both a web-based UI and CLI tool for managing MongoDB Atlas resources.

**📚 [Full Documentation on Read the Docs](https://atlasui.readthedocs.io/)**

## Features

- **Web UI**: FastAPI-based web interface for MongoDB Atlas management
- **CLI Tool**: Command-line interface for Atlas operations
- **Complete API Coverage**: Built from official MongoDB Atlas OpenAPI specifications
- **Modern Stack**: FastAPI, Typer, Rich, and modern Python tooling
- **Secure Authentication**: Supports both API keys (recommended for full functionality) and service accounts (project-scoped only)

## Screenshots

### Dashboard
![Dashboard](https://raw.githubusercontent.com/jdrumgoole/atlasui/main/docs/images/dashboard.png)

### Organizations
![Organizations](https://raw.githubusercontent.com/jdrumgoole/atlasui/main/docs/images/organizations.png)

### All Clusters
![Clusters](https://raw.githubusercontent.com/jdrumgoole/atlasui/main/docs/images/clusters.png)

### All Projects
![Projects](https://raw.githubusercontent.com/jdrumgoole/atlasui/main/docs/images/projects.png)

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

AtlasUI supports two authentication methods. **Both provide the same capabilities** - full access to one organization including all projects and clusters. The key difference is the authentication approach:

#### API Keys (Traditional)

**Best for:** Simple setup, traditional workflows

API keys provide **organization-level** access using traditional digest authentication:
- Manage a single organization in your Atlas account
- Access all projects within that organization
- Control all clusters within those projects
- Simpler setup process
- HTTP Basic Auth (Digest)

**Quick start:**
```bash
atlasui-configure
# Choose option 1 (API Keys)
# Follow the wizard instructions
```

**How to get API keys:**
1. Go to your organization's API Keys page:
   - Direct link: `https://cloud.mongodb.com/v2#/org/<Organization ID>/access/apiKeys`
   - Or navigate: https://cloud.mongodb.com/v2#/preferences/organizations → Select organization → Access Manager → API Keys
2. Click **Create API Key**
3. Set permissions: **Organization Owner**
4. Copy the **Public Key** and **Private Key**
5. Add your IP address to the API Key whitelist

#### Service Accounts (Modern & More Secure)

**Best for:** Modern applications, higher security requirements

Service accounts provide **the same organization-level access as API Keys** using modern OAuth 2.0:
- Access all projects within the organization
- Control all clusters within those projects
- Modern OAuth 2.0 authentication with JWT tokens
- More secure token-based authentication
- Industry-standard authentication approach

**Setup:**
```bash
atlasui-configure
# Choose option 2 (Service Account)
# Follow the wizard instructions
```

**How to get service account credentials:**
1. Go to your organization's Service Accounts page:
   - Direct link: `https://cloud.mongodb.com/v2#/org/<Organization ID>/access/serviceAccounts`
   - Or navigate: https://cloud.mongodb.com/v2#/preferences/organizations → Select organization → Access Manager → Service Accounts
2. Click **Create Service Account**
3. Assign **organization-level roles** (e.g., Organization Owner) for full access
4. Copy the **Client ID** and **Client Secret**

**Note:** Both API Keys and Service Accounts are scoped to a single organization. To work with a different organization, you'll need to configure credentials for that organization.

See [Service Account Documentation](https://github.com/jdrumgoole/atlasui/blob/main/docs/service_accounts.md) for details.

### Web-Based Configuration

You can also configure AtlasUI through the web interface:

1. Start the server without configuration:
   ```bash
   atlasui start
   ```

2. Open http://localhost:8000 in your browser

3. The setup wizard will guide you through configuration

4. Enter your API keys and test the connection

5. Settings are automatically saved and reloaded

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
atlasui start
```

Then open your browser to http://localhost:8000

The server can also be started with custom options:

```bash
# Custom port
atlasui start --port 8080

# Or use environment variable
PORT=8080 atlasui start

# Stop the server
atlasui stop
```

### CLI Tool

```bash
# List all clusters
atlascli clusters list <project-id>

# Get cluster details
atlascli clusters get <project-id> <cluster-name>

# Create a new cluster
atlascli clusters create --name my-new-cluster --project-id <project-id>

# List projects
atlascli projects list

# View help and version
atlascli --help
atlascli --version
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
# Development: Fast iteration (excludes slow M10 tests, ~11 min)
inv test-dev                     # Runs in parallel by default
inv test-dev --no-parallel       # Sequential execution

# M10 tests: Pause/resume functionality (~20 min)
inv m10-test

# Release: Complete test suite (~20-25 min)
inv test-release                 # Runs in parallel by default
inv test-release --no-parallel   # Sequential execution

# Or use pytest directly
pytest                                    # All tests
pytest -m "browser and not m10"          # Skip M10 tests
pytest --cov=atlasui --cov-report=html   # With coverage
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

Contributions are welcome! Please see [CONTRIBUTING.md](https://github.com/jdrumgoole/atlasui/blob/main/CONTRIBUTING.md) for details.

## Quick Links

- [Full Documentation](https://atlasui.readthedocs.io/) - Complete documentation on Read the Docs
- [Quick Start Guide](https://github.com/jdrumgoole/atlasui/blob/main/QUICKSTART.md) - Get started in 5 minutes
- [Contributing Guide](https://github.com/jdrumgoole/atlasui/blob/main/CONTRIBUTING.md) - Development guidelines
- [MongoDB Atlas API Docs](https://www.mongodb.com/docs/atlas/reference/api-resources-spec/)
- [MongoDB Atlas OpenAPI Specs](https://github.com/mongodb/openapi)

---

## Built with Claude

This project was built with assistance from [Claude](https://claude.ai), Anthropic's AI assistant.
