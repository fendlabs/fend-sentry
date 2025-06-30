# Fend Sentry

AI-powered monitoring that actually understands your Django app. Get intelligent error analysis without the enterprise price tag.

## What It Is

A simple command-line tool that gives you instant insights into your Django application's health:

```bash
# Get instant analysis
fend-sentry check

# Output:
🟢 Application Health: GOOD
- 3 minor errors in last hour (down from 12 yesterday)
- No critical issues detected
- Suggested fix: Add retry logic to payment webhook (line 45 in payments/views.py)
```

## Features

- 🚀 **One Command**: No log downloading, just run and get insights
- 🤖 **AI Powered**: Gemini understands Django patterns and suggests fixes
- 💰 **Free Forever**: Uses free-tier APIs, no monthly fees
- 📊 **Smart Reports**: Only see what matters, when it matters
- 🔍 **Root Cause Analysis**: Actual solutions, not just error dumps

## Installation

```bash
# Install
pip install fend-sentry

# Configure (one time)
fend-sentry init

# Check your app
fend-sentry check
```

## Deployment Options

### Local Development
```bash
fend-sentry check --app ~/projects/myapp
```

### Production Server
```bash
# SSH to your server and check
ssh myserver
cd /path/to/django/project
fend-sentry check
```

### Later: Docker Sidecar (Phase 2)
```yaml
# Future enhancement
services:
  django:
    image: myapp
  sentry:
    image: fendsentry/sentry:latest
```

## Current Status (MVP)

- ✅ Parse Django error logs
- ✅ AI analysis with Gemini
- ✅ Command-line interface
- ✅ Email alerts for critical issues

## Roadmap

### Phase 1: Enhanced CLI (Current)
- [ ] Beautiful terminal UI with Rich
- [ ] Historical comparisons ("errors down 50% this week")
- [ ] Export reports (PDF/HTML)

### Phase 2: Multi-App Support
- [ ] Monitor multiple Django apps from one place
- [ ] Central dashboard (simple web UI)
- [ ] Team notifications (Slack/Discord)

### Phase 3: Fend Platform Integration
- [ ] One-click deployment for Fend Marketplace clients
- [ ] Automatic monitoring for all pilots
- [ ] Success metrics tracking

### Phase 4: Enterprise Features
- [ ] Self-hosted dashboard
- [ ] Custom AI training on your codebase
- [ ] Compliance reporting (SOC2, HIPAA)
- [ ] SLA monitoring

## Why We Built This

Every Django developer needs monitoring, but existing solutions are:
- **Expensive**: $100-500/month for basic features
- **Complex**: Overwhelming dashboards with 1000s of metrics
- **Dumb**: They show errors but don't understand them

Fend Sentry is different. It's the monitoring tool we wanted - simple, smart, and free.

Built by [Fend Labs](https://fend.ai) - Innovation through collaboration.