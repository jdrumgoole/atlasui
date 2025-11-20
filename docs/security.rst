Security Guidelines
===================

This document outlines security best practices for using AtlasUI.

Authentication Methods
----------------------

AtlasUI supports two authentication methods:

API Keys (Legacy)
^^^^^^^^^^^^^^^^^

* **Use Case**: Development and testing
* **Security Level**: Moderate
* **Pros**: Simple to set up
* **Cons**: Long-lived credentials, harder to audit

Service Accounts (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Use Case**: Production deployments
* **Security Level**: High
* **Pros**: JWT-based, better audit trail, fine-grained permissions
* **Cons**: Slightly more complex setup

See :doc:`service_accounts` for detailed information.

Credential Management
---------------------

Never Commit Credentials
^^^^^^^^^^^^^^^^^^^^^^^^^

Add these to your `.gitignore`:

.. code-block:: text

    .env
    .env.local
    .env.*.local
    service-account.json
    *-credentials.json

File Permissions
^^^^^^^^^^^^^^^^

Set restrictive permissions on credential files:

.. code-block:: bash

    chmod 600 .env
    chmod 600 service-account.json

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Use environment-specific `.env` files:

* `.env.development` - Development credentials
* `.env.staging` - Staging credentials
* `.env.production` - Production credentials (never commit!)

Secrets Management
^^^^^^^^^^^^^^^^^^

For production deployments, use a secrets manager:

* **AWS Secrets Manager**
* **Azure Key Vault**
* **HashiCorp Vault**
* **Google Cloud Secret Manager**

Example with AWS Secrets Manager:

.. code-block:: python

    import boto3
    import json
    from atlasui.client import AtlasClient

    # Retrieve credentials from AWS Secrets Manager
    client = boto3.client('secretsmanager')
    secret = client.get_secret_value(SecretId='atlasui/service-account')
    credentials = json.loads(secret['SecretString'])

    # Use credentials
    atlas_client = AtlasClient(
        auth_method="service_account",
        service_account_id=credentials['client_id'],
        service_account_secret=credentials['private_key']
    )

Network Security
----------------

HTTPS Only
^^^^^^^^^^

Always use HTTPS for Atlas API communications (default):

.. code-block:: bash

    ATLAS_BASE_URL=https://cloud.mongodb.com

IP Whitelisting
^^^^^^^^^^^^^^^

Configure IP access lists in Atlas to restrict access to your application servers.

Private Endpoints
^^^^^^^^^^^^^^^^^

For enhanced security, use AWS PrivateLink, Azure Private Link, or GCP Private Service Connect.

Application Security
--------------------

Web Server
^^^^^^^^^^

When deploying the web server:

1. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Apache) with TLS
2. **Authentication**: Implement user authentication (OAuth, SAML, etc.)
3. **Authorization**: Restrict access based on user roles
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **CORS**: Configure CORS appropriately for your frontend

Example nginx configuration:

.. code-block:: nginx

    server {
        listen 443 ssl http2;
        server_name atlasui.example.com;

        ssl_certificate /path/to/cert.pem;
        ssl_certificate_key /path/to/key.pem;

        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

API Security
^^^^^^^^^^^^

For the REST API:

1. **API Keys**: Require API keys for client applications
2. **JWT Tokens**: Use JWT tokens for user sessions
3. **Input Validation**: Validate all input parameters
4. **Output Sanitization**: Sanitize output to prevent XSS
5. **Audit Logging**: Log all API access for security auditing

Credential Rotation
-------------------

Service Account Rotation
^^^^^^^^^^^^^^^^^^^^^^^^

Rotate service account credentials regularly (e.g., every 90 days):

1. Create new service account
2. Update configuration with new credentials
3. Test new credentials
4. Deploy updated configuration
5. Delete old service account

API Key Rotation
^^^^^^^^^^^^^^^^

To rotate API keys:

1. Generate new API key in Atlas
2. Update `.env` with new credentials
3. Restart application
4. Delete old API key in Atlas

Zero-Downtime Rotation
^^^^^^^^^^^^^^^^^^^^^^^

For zero-downtime rotation:

1. Create new credentials
2. Update configuration to support both old and new
3. Deploy update
4. Switch to new credentials only
5. Remove old credentials

Monitoring & Auditing
---------------------

Access Logs
^^^^^^^^^^^

Monitor Atlas access logs for:

* Unusual access patterns
* Failed authentication attempts
* Unexpected API calls

Application Logs
^^^^^^^^^^^^^^^^

Log security-relevant events:

* Authentication successes/failures
* Authorization denials
* Credential rotations
* Configuration changes

Alerts
^^^^^^

Set up alerts for:

* Multiple failed authentication attempts
* Access from unexpected IPs
* High-privilege operations
* Unusual API usage patterns

Compliance
----------

Data Protection
^^^^^^^^^^^^^^^

* **GDPR**: Handle user data in compliance with GDPR
* **HIPAA**: For healthcare data, ensure HIPAA compliance
* **SOC 2**: Follow SOC 2 requirements for service providers

Encryption
^^^^^^^^^^

* **In Transit**: All API communications use TLS 1.2+
* **At Rest**: Atlas encrypts data at rest by default

Vulnerability Management
------------------------

Keep Dependencies Updated
^^^^^^^^^^^^^^^^^^^^^^^^^^

Regularly update dependencies to get security patches:

.. code-block:: bash

    inv dev-install
    pip list --outdated

Security Scanning
^^^^^^^^^^^^^^^^^

Use security scanning tools:

.. code-block:: bash

    # Scan for vulnerabilities
    pip install safety
    safety check

    # Scan code for security issues
    pip install bandit
    bandit -r atlasui/

Incident Response
-----------------

If you suspect a security breach:

1. **Rotate Credentials**: Immediately rotate all credentials
2. **Review Logs**: Check Atlas and application logs
3. **Notify Team**: Inform your security team
4. **Document**: Document the incident and response
5. **Update**: Update security measures to prevent recurrence

Reporting Security Issues
--------------------------

To report security vulnerabilities in AtlasUI:

* **Do not** open a public GitHub issue
* Email security concerns to the project maintainers
* Provide detailed information about the vulnerability
* Allow time for a fix before public disclosure
