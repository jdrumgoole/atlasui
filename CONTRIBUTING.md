# Contributing to AtlasUI

Thank you for your interest in contributing to AtlasUI! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- uv (recommended) or pip
- MongoDB Atlas account with API keys for testing

### Setting Up Your Environment

1. Clone the repository:
```bash
git clone <repository-url>
cd atlasui
```

2. Set up the development environment:
```bash
# Quick setup (recommended)
inv setup

# Or install dependencies manually
uv pip install -e ".[dev,docs]"
```

3. The setup task will create a `.env` file from `.env.example`:
```bash
# Edit .env with your credentials
nano .env
```

## Development Workflow

### Running Tests

```bash
# Run all tests
inv test

# Run tests without coverage
inv test --no-coverage

# Run specific test file
pytest tests/test_client.py

# Run with custom pytest options
pytest --cov=atlasui --cov-report=html
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
inv format

# Check formatting without changes
inv format --check

# Run linting
inv lint

# Run all checks (format, lint, test)
inv check
```

### Running the Application

```bash
# Start web server
inv run

# Run with auto-reload
inv run --reload

# Run with custom port
inv run --port=8080

# Run CLI
inv cli

# Test Atlas connection
inv info
```

### Building Documentation

```bash
# Build Sphinx docs
inv docs

# Build and open in browser
inv docs --open-browser
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings in Google style
- Keep lines under 100 characters
- Use meaningful variable and function names

## Testing Guidelines

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Mock external API calls
- Test both success and error cases

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Update documentation as needed
5. Run tests and linting locally
6. Submit a pull request with a clear description

## Project Structure

```
atlasui/
├── atlasui/           # Main package
│   ├── api/          # FastAPI routes
│   ├── cli/          # CLI commands
│   ├── client/       # Atlas API client
│   ├── models/       # Pydantic models
│   ├── services/     # Business logic
│   ├── static/       # Static files
│   ├── templates/    # HTML templates
│   └── config.py     # Configuration
├── tests/            # Test suite
├── docs/             # Sphinx documentation
├── openapi/          # MongoDB OpenAPI specs
└── tasks.py          # Invoke task definitions
```

## Adding New Features

### Adding a New API Endpoint

1. Add the endpoint method to `atlasui/client/base.py`
2. Create a route in the appropriate file in `atlasui/api/`
3. Add CLI command in the appropriate file in `atlasui/cli/`
4. Write tests in `tests/`
5. Update documentation

### Adding a New CLI Command

1. Add command to appropriate file in `atlasui/cli/`
2. Update CLI tests
3. Update documentation

## Questions?

If you have questions or need help, please:
- Open an issue on GitHub
- Check existing documentation
- Review closed issues for similar questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
