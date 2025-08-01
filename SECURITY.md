# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in NuestrasRecetas.club, please report it responsibly:

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Email security concerns to: [security@nuestrasrecetas.club]
3. Include detailed information about the vulnerability
4. Allow reasonable time for investigation and fix before public disclosure

## Security Best Practices

### For Developers

#### Authentication & Authorization
- All API endpoints requiring authentication use the `@require_auth` decorator
- User sessions are managed through Supabase Auth with JWT tokens
- Row Level Security (RLS) policies enforce data isolation at the database level
- Password requirements: minimum 8 characters with letters and numbers

#### Input Validation
- All user inputs are validated and sanitized using the `sanitize_input()` function
- Field length limits are enforced:
  - User names: 100 characters
  - Usernames: 50 characters (alphanumeric + underscore only)
  - Recipe titles: 200 characters
  - Recipe instructions: 5000 characters
  - Bio: 500 characters
  - Tags: 500 characters
- Email format validation using regex patterns
- Ingredient limits: maximum 50 ingredients per recipe

#### XSS Prevention
- HTML content is escaped using `html.escape()`
- Frontend uses safe DOM manipulation instead of `innerHTML`
- Content Security Policy (CSP) headers implemented

#### SQL Injection Prevention
- All database operations use Supabase's parameterized query builder
- No raw SQL queries or string concatenation
- Database-level Row Level Security (RLS) policies

### Security Headers

The application implements comprehensive security headers:

```nginx
# HSTS - HTTP Strict Transport Security
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Content Security Policy
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; img-src 'self' data: https: blob:; font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; connect-src 'self' https://*.supabase.co; frame-ancestors 'none';

# Additional Security Headers
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

### SSL/TLS Configuration

- TLS 1.2 and TLS 1.3 only
- Strong cipher suites (ECDHE-RSA-AES128-GCM-SHA256, ECDHE-RSA-AES256-GCM-SHA384)
- Session caching and security optimizations
- Cloudflare origin certificates for encryption

### CORS Policy

Production CORS is restricted to:
- `https://nuestrasrecetas.club`
- `https://www.nuestrasrecetas.club`

Development includes localhost origins for testing.

### Rate Limiting

Nginx implements rate limiting:
- API endpoints: 10 requests/second (burst of 5)
- Static files: 30 requests/second (burst of 20)

### Dependencies

All dependencies are regularly updated to patch security vulnerabilities:
- Flask 3.1.1+
- Gunicorn 23.0.0+
- Flask-CORS 6.0.1+
- Supabase 2.17.0+

## Security Checklist for Deployments

### Before Deployment
- [ ] Rotate all Supabase credentials
- [ ] Generate strong Flask SECRET_KEY
- [ ] Verify `.env` file is not committed to repository
- [ ] Remove any test/debug endpoints
- [ ] Update all dependencies to latest versions
- [ ] Run security linting tools

### Production Environment
- [ ] HTTPS-only traffic (HTTP redirects to HTTPS)
- [ ] Environment variables properly configured
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Log rotation configured
- [ ] Docker containers run as non-root user

### GitHub Repository Security
- [ ] Branch protection rules enabled
- [ ] Dependabot alerts enabled
- [ ] Secret scanning enabled
- [ ] Code scanning with CodeQL enabled
- [ ] SSH keys properly configured for deployment
- [ ] Workflow permissions restricted to minimum required

## Incident Response

In case of a security incident:

1. **Immediate Response**
   - Assess the scope and impact
   - Contain the breach (take systems offline if necessary)
   - Preserve logs and evidence

2. **Investigation**
   - Identify root cause
   - Document timeline and impact
   - Determine what data was affected

3. **Recovery**
   - Apply fixes and patches
   - Rotate compromised credentials
   - Restore systems from clean backups if needed

4. **Post-Incident**
   - Update security measures
   - Improve monitoring
   - Document lessons learned
   - Notify affected users if required

## Security Monitoring

### Log Monitoring
- Monitor authentication failures
- Track unusual access patterns
- Alert on error rate spikes
- Monitor resource usage anomalies

### Automated Security Checks
- Dependency vulnerability scans
- Container image scanning
- Infrastructure security scans
- Penetration testing (quarterly)

## Contact

For security-related questions or concerns:
- Security Email: [security@nuestrasrecetas.club]
- General Contact: [contact@nuestrasrecetas.club]

Last Updated: January 2025