# Security Policy

## Supported Authentication Methods

AtlasUI supports two authentication methods for MongoDB Atlas API access:

### API Keys (Legacy)
- Suitable for development and testing
- Uses HTTP Digest Authentication
- Configure with `ATLAS_PUBLIC_KEY` and `ATLAS_PRIVATE_KEY`

### Service Accounts (Recommended)
- **Recommended for production deployments**
- Uses JWT-based authentication
- Enhanced security with short-lived tokens
- Better audit trail and fine-grained permissions
- Configure with `ATLAS_SERVICE_ACCOUNT_CREDENTIALS_FILE`

See [Service Account Documentation](docs/service_accounts.rst) for setup instructions.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to the project maintainers. Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within 48 hours. If the issue is confirmed, we will:

1. Acknowledge receipt of the vulnerability
2. Work on a fix
3. Release a security update
4. Credit you for the discovery (unless you prefer to remain anonymous)

## Security Best Practices

1. **Never commit credentials** - Add `.env`, `service-account.json`, and credential files to `.gitignore`
2. **Use service accounts** - Prefer service account authentication over API keys for production
3. **Rotate credentials regularly** - Rotate service accounts and API keys periodically
4. **Set file permissions** - Use `chmod 600` on credential files
5. **Use secrets managers** - Store credentials in AWS Secrets Manager, Azure Key Vault, etc.
6. **Enable HTTPS** - Always use HTTPS for the web server
7. **Implement authentication** - Add user authentication to the web interface
8. **Monitor access** - Review Atlas access logs regularly
9. **Keep dependencies updated** - Run `inv dev-install` regularly to update dependencies
10. **Run security scans** - Use tools like `safety` and `bandit` to scan for vulnerabilities

## Security Features

- ✅ HTTPS-only API communication
- ✅ JWT-based service account authentication
- ✅ Support for credential rotation
- ✅ Secure credential file permissions
- ✅ No credentials in logs or error messages
- ✅ Input validation on all API endpoints
- ✅ Configurable request timeouts
- ✅ Environment-based configuration

## Compliance

AtlasUI is designed to help you comply with:

- **GDPR** - Data protection and privacy
- **HIPAA** - Healthcare data security (when properly configured)
- **SOC 2** - Service organization controls
- **PCI DSS** - Payment card industry standards

However, compliance ultimately depends on your deployment configuration and operational practices.

## Security Updates

Security updates are released as soon as possible after a vulnerability is confirmed. Update to the latest version using:

```bash
uv pip install -e ".[dev]" --upgrade
```

Subscribe to GitHub releases to be notified of security updates.

## Additional Resources

- [Security Guidelines](docs/security.rst) - Detailed security documentation
- [Service Accounts](docs/service_accounts.rst) - Service account setup
- [MongoDB Atlas Security](https://www.mongodb.com/docs/atlas/security/) - Atlas security features
