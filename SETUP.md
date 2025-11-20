# AtlasUI Quick Setup Guide

## Interactive Service Account Setup

The easiest way to configure AtlasUI is using the interactive setup wizard:

```bash
inv configure-service-account
```

Or directly:

```bash
atlasui-setup
```

This will guide you through:

1. ✅ Entering your service account credentials (Client ID and Secret)
2. ✅ Creating a secure credentials file
3. ✅ Updating your `.env` configuration
4. ✅ Testing the Atlas API connection
5. ✅ Showing your projects to verify it works

## What You Need

Before running the setup:

1. **MongoDB Atlas Account**
   - Go to https://cloud.mongodb.com
   - Sign in or create an account

2. **Service Account Credentials**
   - Organization Settings → Access Manager → Service Accounts
   - Click "Create Service Account"
   - Assign roles (e.g., Organization Owner)
   - **Save the Client ID and Client Secret** (shown only once!)

## Setup Walkthrough

### Step 1: Run Setup Command

```bash
inv configure-service-account
```

You'll see:
```
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║              AtlasUI Service Account Setup            ║
    ║                                                       ║
    ║        MongoDB Atlas OAuth 2.0 Configuration          ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
```

### Step 2: Enter Credentials

When prompted, paste your credentials from Atlas:

```
Client ID: abc123def456-7890-abcd-ef12-34567890abcd
Enter Client Secret: ************************************
Confirm Client Secret: ************************************
```

### Step 3: Choose File Location

```
Credentials file path [./service-account.json]:
```

Press Enter for default, or specify a custom path.

### Step 4: Configuration

The wizard will:
- Create `service-account.json` with chmod 600 permissions
- Update `.env` with `ATLAS_AUTH_METHOD=service_account`
- Test your connection to Atlas

### Step 5: Verify

You'll see:
```
✓ Successfully connected to Atlas API!
✓ Found 5 projects

Your Projects
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name           ┃ ID                       ┃ Org ID                   ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Production     │ 5f8a1e2b3c4d5e6f7g8h9i0j │ 5f8a1e2b3c4d5e6f7g8h9i0k │
│ Staging        │ 6f9b2e3c4d5e6f7g8h9i0j1k │ 5f8a1e2b3c4d5e6f7g8h9i0k │
└────────────────┴──────────────────────────┴──────────────────────────┘
```

## What Gets Created

After setup, you'll have:

1. **service-account.json** (chmod 600)
   ```json
   {
     "client_id": "your-client-id",
     "client_secret": "your-client-secret",
     "token_url": "https://cloud.mongodb.com/api/oauth/token"
   }
   ```

2. **.env** (updated)
   ```bash
   ATLAS_AUTH_METHOD=service_account
   ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE=/absolute/path/to/service-account.json
   ```

## Next Steps

After successful setup:

### Start the Web Server

```bash
inv run
```

Visit http://localhost:8000

### Use the CLI

```bash
# List projects
atlasui projects list

# List clusters
atlasui clusters list <project-id>

# Get cluster details
atlasui clusters get <project-id> <cluster-name>

# See all commands
atlasui --help
```

### Run Tests

```bash
inv test
```

### View Documentation

```bash
inv docs --open-browser
```

## Troubleshooting

### "OAuth token request failed"

- Verify Client ID and Secret are correct
- Check service account exists in Atlas
- Ensure network connectivity to cloud.mongodb.com

### "Permission denied"

- Check service account has required roles
- Assign "Organization Owner" for full access
- Wait a few minutes for permissions to propagate

### "Credentials file not found"

- Use absolute path in .env
- Check file permissions: `ls -l service-account.json`
- Verify file exists: `cat service-account.json`

### Re-run Setup

You can run the setup again to:
- Update credentials
- Fix configuration issues
- Test connection

Just run:
```bash
inv configure-service-account
```

And choose to overwrite existing files.

## Security Reminders

✅ **DO:**
- Keep service-account.json in .gitignore
- Set file permissions to 600
- Rotate credentials every 90 days
- Use different accounts for dev/staging/prod

❌ **DON'T:**
- Commit credentials to Git
- Share credentials in chat/email
- Use production credentials in development
- Store credentials in plain text outside secure files

## Manual Setup Alternative

If you prefer manual setup, see:
- [Service Account Documentation](docs/service_accounts.rst)
- [Quick Start Guide](QUICKSTART.md)

## Getting Help

- View all tasks: `inv --list`
- CLI help: `atlasui --help`
- Test connection: `inv info`
- Documentation: `inv docs`
