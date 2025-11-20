# Installation

## Requirements

* Python 3.11 or higher
* MongoDB Atlas account with API keys

## Installation Steps

### From PyPI

```bash
# Install AtlasUI
pip install atlasui

# With development dependencies
pip install atlasui[dev]

# With documentation dependencies
pip install atlasui[docs]
```

### From Source

```bash
# Clone the repository
git clone https://github.com/jdrumgoole/atlasui.git
cd atlasui

# Install in development mode
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in your project root with your MongoDB Atlas credentials:

```bash
ATLAS_AUTH_METHOD=api_key
ATLAS_PUBLIC_KEY=your_public_key
ATLAS_PRIVATE_KEY=your_private_key
ATLAS_BASE_URL=https://cloud.mongodb.com
ATLAS_API_VERSION=v2
```

## Getting Atlas API Keys

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com)
2. Navigate to your organization settings
3. Go to "Access Manager" > "API Keys"
4. Click "Create API Key"
5. Set appropriate permissions (e.g., Organization Owner, Project Owner)
6. Save the Public Key and Private Key

## Verification

Verify your installation:

```bash
# Check CLI
atlasui --help

# Start web server
atlasui-server
```

The web interface will be available at http://localhost:8000
