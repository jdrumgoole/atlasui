# Service Account Authentication

AtlasUI supports MongoDB Atlas Service Accounts for secure, programmatic access to the Atlas API.
Service accounts use OAuth 2.0 Client Credentials flow and are the **recommended authentication method**
for production deployments.

## Why Use Service Accounts?

Service accounts provide several advantages over API keys:

* **OAuth 2.0 Standard**: Industry-standard authentication protocol
* **Short-lived Tokens**: Access tokens expire after 1 hour, limiting exposure
* **Better Audit Trail**: Service accounts are clearly identified in Atlas logs
* **Fine-grained Permissions**: Assign specific roles and permissions to service accounts
* **Credential Rotation**: Easier to rotate credentials without downtime
* **No User Account Required**: Service accounts are independent of user accounts

## How It Works

MongoDB Atlas service accounts use the **OAuth 2.0 Client Credentials flow**:

1. **Service Account Credentials**: You receive a `client_id` and `client_secret`
2. **Token Exchange**: AtlasUI exchanges these credentials for an access token
3. **API Authentication**: The access token is used to authenticate API requests
4. **Token Refresh**: Tokens expire after 1 hour and are automatically refreshed

```text
┌─────────────┐
│  AtlasUI    │
└──────┬──────┘
       │ 1. POST /api/oauth/token
       │    Authorization: Basic base64(client_id:client_secret)
       │    grant_type=client_credentials
       ▼
┌─────────────────────┐
│ Atlas OAuth Endpoint│
│ /api/oauth/token    │
└──────┬──────────────┘
       │ 2. Returns access_token (expires in 1 hour)
       ▼
┌─────────────┐
│  AtlasUI    │──────► 3. Use Bearer token for API calls
└─────────────┘
```

**Technical Details:**

* **Token Endpoint**: `https://cloud.mongodb.com/api/oauth/token`
* **Authentication Method**: HTTP Basic Authentication with `client_id:client_secret`
* **Grant Type**: `client_credentials`
* **Token Type**: Bearer token
* **Token Lifetime**: 1 hour (3600 seconds)
* **Token Format**: JWT (JSON Web Token)

## Prerequisites

Before using service account authentication, you need to:

1. Have access to a MongoDB Atlas organization
2. Have permissions to create service accounts (Organization Owner or Project Owner)
3. Create a service account in the Atlas UI or API

## Creating a Service Account

### Via Atlas UI

1. **Log in to MongoDB Atlas**

   Visit https://cloud.mongodb.com

2. **Navigate to Organization Settings**

   - Click on your organization name in the top-left
   - Select "Organization Settings" from the dropdown

3. **Go to Access Manager**

   - In the left sidebar, click "Access Manager"
   - Click on the "Service Accounts" tab

4. **Create New Service Account**

   - Click "Create Service Account"
   - **Name**: Give it a descriptive name (e.g., `atlasui-production`)
   - **Description**: Add details about its purpose
   - **Expiration**: Set an expiration date (optional, but recommended)

5. **Assign Roles**

   Choose roles based on what AtlasUI needs to do:

   **For full access (typical use case):**

   - ✅ `Organization Owner` - Full access to all organization resources

   **For project-specific access:**

   - ✅ `Project Owner` - Full access to specific projects
   - ✅ `Project Data Access Admin` - Database operations
   - ✅ `Project Cluster Manager` - Cluster management

   **For read-only monitoring:**

   - ✅ `Organization Read Only` - View organization resources
   - ✅ `Project Read Only` - View project resources

6. **Save and Download Credentials**

   - Click "Next" or "Create"
   - **⚠️ CRITICAL**: You'll see the **Client ID** and **Client Secret** - this is your only chance!
   - Copy both values immediately
   - The client secret is a regular string (not a PEM key)

```{warning}
The client secret is shown only once during creation. If you lose it, you'll need to
delete the service account and create a new one.
```

## Configuration

### Credentials File Format

Create a JSON file with your service account credentials:

```json
{
    "client_id": "your-client-id-here",
    "client_secret": "your-client-secret-here",
    "token_url": "https://cloud.mongodb.com/api/oauth/token"
}
```

The `token_url` field is optional and defaults to Atlas's OAuth endpoint.

### Option 1: Using a Credentials File (Recommended)

1. **Create the credentials file**:

   ```bash
   # Using Python helper
   uv run python << EOF
   from atlasui.client import ServiceAccountManager

   ServiceAccountManager.create_credentials_file(
       client_id="your-client-id",
       client_secret="your-client-secret",
       output_file="./service-account.json"
   )
   EOF
   ```

   Or create it manually using the JSON format shown above.

2. **Set secure permissions**:

   ```bash
   chmod 600 service-account.json
   ```

3. **Configure your .env file**:

   ```bash
   ATLAS_AUTH_METHOD=service_account
   ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE=/absolute/path/to/service-account.json
   ```

### Option 2: Using Environment Variables

Set the credentials directly in your `.env` file:

```bash
ATLAS_AUTH_METHOD=service_account
ATLAS_SERVICE_ACCOUNT_ID=your-client-id-here
ATLAS_SERVICE_ACCOUNT_SECRET=your-client-secret-here
```

## Usage

Once configured, AtlasUI will automatically use OAuth 2.0 service account authentication:

### Web Server

```bash
# Start server with service account auth
inv run
```

### CLI Tool

```bash
# List projects using service account
atlascli projects list

# Get cluster details
atlascli clusters get <project-id> <cluster-name>
```

### Python Client

```python
from atlasui.client import AtlasClient

# Using credentials file
with AtlasClient(
    auth_method="service_account",
    service_account_credentials_file="./service-account.json"
) as client:
    projects = client.list_projects()
    print(projects)

# Using direct credentials
with AtlasClient(
    auth_method="service_account",
    service_account_id="your-client-id",
    service_account_secret="your-client-secret"
) as client:
    clusters = client.list_clusters("project-id")
    print(clusters)
```

## Token Management

**Automatic Token Refresh**

AtlasUI automatically manages OAuth tokens:

- Tokens are cached after first request
- Tokens expire after 1 hour
- New tokens are requested 5 minutes before expiry
- No manual token management needed

**Token Storage**

- Tokens are stored in memory only
- Tokens are never written to disk
- Each AtlasClient instance manages its own tokens

## Security Best Practices

1. **Never Commit Credentials**

   Add to `.gitignore`:

   ```text
   service-account.json
   *-credentials.json
   .env
   ```

2. **Use File Permissions**

   Set restrictive permissions on credentials files:

   ```bash
   chmod 600 service-account.json
   chmod 600 .env
   ```

3. **Rotate Regularly**

   Rotate service account credentials periodically (e.g., every 90 days)

4. **Principle of Least Privilege**

   Assign minimum required permissions to service accounts

5. **Use Secrets Managers**

   Store credentials in AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, etc.

6. **Environment-Specific Accounts**

   Use different service accounts for dev, staging, and production

## Troubleshooting

### OAuth Token Request Failed

If you see "OAuth token request failed" errors:

* Verify the client ID and client secret are correct
* Ensure the service account hasn't been deleted or expired
* Check network connectivity to `cloud.mongodb.com`
* Review Atlas access logs for authentication failures

### Invalid Client

If you get "invalid_client" error:

* Double-check the client ID is correct
* Verify the client secret hasn't been rotated
* Ensure the service account exists and is active

### Permission Denied

If you get permission errors after authentication succeeds:

* Check the service account has the required roles
* Verify roles are assigned at the correct scope (organization vs. project)
* Review Atlas access logs to see what permissions are needed

### Connection Timeout

If token requests timeout:

* Check firewall rules allow HTTPS to `cloud.mongodb.com`
* Verify proxy settings if behind a corporate proxy
* Increase timeout in configuration if needed

## Migration from API Keys

To migrate from API key authentication to service accounts:

1. **Create Service Account**: Follow the creation steps above
2. **Update Configuration**: Change `ATLAS_AUTH_METHOD` to `service_account`
3. **Add Credentials**: Set either credentials file or environment variables
4. **Test**: Verify authentication works with `inv info`
5. **Remove API Keys**: Once verified, remove old API key credentials
6. **Update Documentation**: Update your deployment docs

Example migration `.env` changes:

```diff
- ATLAS_AUTH_METHOD=api_key
- ATLAS_PUBLIC_KEY=your_public_key
- ATLAS_PRIVATE_KEY=your_private_key
+ ATLAS_AUTH_METHOD=service_account
+ ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE=/etc/atlasui/service-account.json
```

## Differences from API Keys

| Feature                | API Keys (Digest Auth)          | Service Accounts (OAuth 2.0)   |
|------------------------|----------------------------------|--------------------------------|
| **Authentication**     | HTTP Digest                      | OAuth 2.0 Bearer Token         |
| **Credentials**        | Public Key + Private Key         | Client ID + Client Secret      |
| **Token Lifetime**     | No tokens (long-lived keys)      | 1 hour access tokens           |
| **Rotation**           | Manual, requires API update      | Easier, OAuth flow handles it  |
| **Audit Trail**        | User-based logging               | Service account-specific logs  |
| **Industry Standard**  | HTTP Digest (older)              | OAuth 2.0 (modern standard)    |
| **Recommended For**    | Development, legacy systems      | Production deployments         |

## API Reference

See the following classes for detailed API documentation:

* `atlasui.client.service_account.ServiceAccountAuth` - OAuth 2.0 authentication handler
* `atlasui.client.service_account.ServiceAccountManager` - Credential management

## Additional Resources

* [MongoDB Atlas Service Accounts Overview](https://www.mongodb.com/docs/atlas/api/service-accounts-overview/)
* [OAuth 2.0 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
* [Atlas Administration API Authentication](https://www.mongodb.com/docs/atlas/api/api-authentication/)
