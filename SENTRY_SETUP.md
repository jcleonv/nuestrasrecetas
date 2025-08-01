# Sentry Error Monitoring Setup

This guide will help you set up Sentry for error monitoring and alerting on your NuestrasRecetas.club platform.

## 1. Create Sentry Account

1. Go to [sentry.io](https://sentry.io) and create a free account
2. Create a new project and select "Flask" as the platform
3. Copy the DSN (Data Source Name) provided

## 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Monitoring and Error Tracking
SENTRY_DSN=https://your-dsn-key@o123456.ingest.sentry.io/123456
ENVIRONMENT=production
```

## 3. Features Included

### Error Tracking
- Automatic error capture and reporting
- Stack traces with local variables
- Performance monitoring (10% sampling)
- Release tracking

### Custom Endpoints
- `/health` - Shows Sentry status
- `/sentry-test` - Test endpoint to trigger an error (for testing)

### Configuration Options
- **traces_sample_rate**: 0.1 (10% of transactions monitored for performance)
- **profiles_sample_rate**: 0.1 (10% profiling for performance insights)
- **environment**: Set from ENVIRONMENT env var (defaults to "production")
- **release**: Set from SENTRY_RELEASE env var (auto-populated from GitHub SHA in deployment)

## 4. Testing Sentry

After deployment with Sentry configured:

1. Visit `https://nuestrasrecetas.club/health` to verify Sentry is enabled
2. Visit `https://nuestrasrecetas.club/sentry-test` to trigger a test error
3. Check your Sentry dashboard for the error report

## 5. Sentry Dashboard Features

Once configured, you'll get:

- **Real-time error alerts** via email/Slack/webhooks
- **Performance monitoring** for slow endpoints
- **Release tracking** for deployment correlation
- **User context** for errors (when authenticated)
- **Environment separation** (production, staging, etc.)

## 6. Alert Configuration

In your Sentry project settings, configure:

- **Email alerts** for new issues
- **Slack integration** for team notifications
- **Issue assignment** rules
- **Alert frequency** settings

## 7. Production Recommendations

- Set up **issue assignment rules** based on error types
- Configure **release deployment notifications**
- Set up **performance alerts** for slow endpoints
- Enable **suspect commits** to identify problematic deployments
- Use **custom tags** for better error categorization

## 8. Privacy & Security

- Sentry automatically filters sensitive data (passwords, tokens)
- Personal data is scrubbed by default
- Configure additional data scrubbing in project settings
- Review Sentry's privacy policy for data handling

Your Flask app is now configured to automatically send errors and performance data to Sentry!