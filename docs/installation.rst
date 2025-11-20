Installation
============

Requirements
------------

* Python 3.11 or higher
* MongoDB Atlas account with API keys

Installation Steps
------------------

Using uv (Recommended)
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    # Install AtlasUI
    uv pip install -e .

    # With development dependencies
    uv pip install -e ".[dev]"

    # With documentation dependencies
    uv pip install -e ".[docs]"

Using pip
^^^^^^^^^

.. code-block:: bash

    # Install AtlasUI
    pip install -e .

    # With development dependencies
    pip install -e ".[dev]"

Configuration
-------------

Create a ``.env`` file in your project root with your MongoDB Atlas credentials:

.. code-block:: bash

    ATLAS_PUBLIC_KEY=your_public_key
    ATLAS_PRIVATE_KEY=your_private_key
    ATLAS_BASE_URL=https://cloud.mongodb.com
    ATLAS_API_VERSION=v2

Getting Atlas API Keys
----------------------

1. Log in to `MongoDB Atlas <https://cloud.mongodb.com>`_
2. Navigate to your organization settings
3. Go to "Access Manager" > "API Keys"
4. Click "Create API Key"
5. Set appropriate permissions (e.g., Organization Owner, Project Owner)
6. Save the Public Key and Private Key

Verification
------------

Verify your installation:

.. code-block:: bash

    # Check CLI
    atlasui --help

    # Test connection
    atlasui info

    # Start web server
    atlasui-server
