# AtlasUI Configuration Tool

## Summary

A new interactive configuration tool has been created to simplify Atlas API authentication setup for AtlasUI.

## What Changed

### New Files

**`atlasui/configure.py`** - Interactive configuration wizard
- Supports both API Key and Service Account authentication
- Provides clear comparison of authentication methods
- Explains service account limitations
- Guides users through credential entry
- Creates/updates `.env` file automatically
- Tests connection to verify setup
- Provides helpful next steps

### Removed Files

- **`atlasui/setup.py`** - Replaced by `configure.py`

### Modified Files

**`pyproject.toml`**
- Changed `atlasui-setup` to `atlasui-configure` in project.scripts
- New entry point: `atlasui.configure:main`

**`README.md`**
- Completely rewrote Configuration section
- Added Quick Setup instructions
- Explained authentication methods with clear recommendations
- Highlighted service account limitations
- Added "Built with Claude" attribution

## Features

### Interactive Wizard

The configuration tool provides a user-friendly wizard that:

1. **Presents Authentication Options**
   - Displays comparison table of API Keys vs Service Accounts
   - Shows scope, compatibility, and use cases
   - Recommends API Keys for full functionality

2. **Explains Service Account Limitations**
   - Clear warning that service accounts are project-scoped
   - Explains AtlasUI needs organization-level access
   - Confirms user understanding before proceeding

3. **API Key Configuration**
   - Step-by-step instructions to get API keys from Atlas
   - Secure credential entry (hidden input for private key)
   - Confirmation prompt for private key
   - Automatic `.env` file creation/update
   - Secure file permissions (600)
   - Connection testing with visual feedback

4. **Service Account Configuration**
   - Additional warnings about limitations
   - Option to switch to API Keys
   - Redirects to API Key setup if user changes mind

5. **Connection Testing**
   - Tests Atlas API connectivity
   - Fetches and displays organizations/projects
   - Provides troubleshooting tips if connection fails

6. **Next Steps**
   - Clear instructions for starting the server
   - CLI command examples
   - Security reminders

### Visual Design

Uses Rich library for beautiful terminal UI:
- Color-coded messages (green for success, yellow for warnings, red for errors)
- Formatted panels and tables
- Progress spinners for API calls
- Clear visual hierarchy

## Usage

### For End Users

After installing AtlasUI:

```bash
# Run the configuration wizard
atlasui-configure
```

The wizard will guide you through:
1. Choosing authentication method
2. Entering credentials
3. Testing the connection
4. Starting to use AtlasUI

### Comparison Table

The wizard displays:

| Feature | API Keys | Service Accounts |
|---------|----------|------------------|
| **Scope** | Organization-level | Project-level only |
| **AtlasUI Compatibility** | Full (Recommended) | Limited |
| **Setup Complexity** | Simple | Moderate |
| **Security** | Moderate (with rotation) | High (JWT-based) |
| **Use Case** | Managing all org resources | Single project operations |

### Service Account Warnings

The tool provides multiple warnings:

1. **Initial Comparison**
   - Shows service accounts are project-scoped
   - Highlights incompatibility with AtlasUI's needs

2. **Confirmation Dialog**
   - Asks user to confirm they understand limitations
   - Offers option to switch to API Keys

3. **Setup Screen**
   - Displays prominent warning panel
   - Final chance to cancel and use API Keys instead

## API Key Setup Flow

1. **Welcome & Instructions**
   - Shows where to get API keys in Atlas
   - Step-by-step guide

2. **Credential Entry**
   - Public Key (visible input)
   - Private Key (hidden input)
   - Private Key confirmation (hidden input)

3. **File Configuration**
   - Creates/updates `.env` with:
     ```
     ATLAS_AUTH_METHOD=api_key
     ATLAS_PUBLIC_KEY=<public_key>
     ATLAS_PRIVATE_KEY=<private_key>
     ATLAS_BASE_URL=https://cloud.mongodb.com
     ATLAS_API_VERSION=v2
     ```
   - Sets secure permissions (chmod 600)

4. **Connection Test**
   - Connects to Atlas API
   - Lists organizations
   - Displays in formatted table

5. **Success Screen**
   - Green success panel
   - Next steps for using AtlasUI
   - Security reminders

## Security Features

1. **Hidden Input**
   - Private keys/secrets never displayed on screen
   - Uses `getpass` for secure entry

2. **Confirmation**
   - Requires re-entry of sensitive credentials
   - Prevents typos

3. **File Permissions**
   - Automatically sets `.env` to 600 (owner read/write only)
   - Warns if unable to set permissions

4. **No Storage**
   - Credentials only written to `.env`
   - Never logged or cached

5. **Security Reminders**
   - Warns about credential rotation
   - Reminds not to commit to Git
   - Suggests secrets managers for production

## Error Handling

The tool handles:
- Keyboard interrupt (Ctrl+C) - graceful exit
- Invalid credentials - validation with clear messages
- File permission errors - helpful warnings
- API connection failures - troubleshooting tips
- Existing .env files - prompts before overwriting

## Benefits

### For New Users
- Simple, guided setup process
- Clear explanations of options
- Immediate feedback on configuration
- Reduces setup errors

### For Experienced Users
- Quick configuration
- Can skip connection testing
- Manual configuration still available

### For All Users
- Clear service account limitations explained upfront
- Reduces confusion about authentication methods
- Automatic `.env` file management
- Connection verification

## Documentation Updates

### README.md

**Before:**
- Manual configuration instructions
- Service account mentioned but limitations unclear
- No guided setup process

**After:**
- Prominent "Quick Setup" section
- Clear authentication method comparison
- Service account limitations highlighted
- Interactive wizard recommended
- Manual configuration still available

### Added Attribution

- "Built with Claude" section at bottom of README

## Installation

The configuration tool is automatically installed with AtlasUI:

```bash
pip install atlasui
```

Then available as:

```bash
atlasui-configure
```

## Future Enhancements

Potential improvements:
- Full service account setup implementation
- Multiple authentication profile support
- Credential rotation wizard
- Migration tool (service account → API keys)
- Configuration validation
- Export/import configuration

## Testing

The tool has been tested for:
- ✅ Module imports successfully
- ✅ Entry point registered in pyproject.toml
- ✅ Rich UI components display correctly
- ✅ Error handling works
- ✅ File operations succeed

## Migration from Old Setup

Users upgrading from previous versions:

**Old way:**
```bash
atlasui-setup  # Service account only
```

**New way:**
```bash
atlasui-configure  # Both API Keys and Service Accounts
```

The old `atlasui-setup` command no longer exists. Run `atlasui-configure` instead.

## Conclusion

The new configuration tool significantly improves the user experience by:
- Providing clear guidance on authentication methods
- Explaining service account limitations upfront
- Automating `.env` file creation
- Testing connections before use
- Giving immediate feedback

This reduces setup time and prevents common configuration mistakes.
