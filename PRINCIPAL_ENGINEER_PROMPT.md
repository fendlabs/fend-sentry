# Principal Engineer Implementation Prompt

Use this prompt with Claude to implement Fend Sentry:

---

I need you to implement Fend Sentry, a beautiful CLI tool that gives instant AI-powered insights into Django application health. You are a principal engineer focused on simplicity, user experience, and clean code.

## Project Context
- This is Fend Labs Project #001 - our first innovation showcase
- CLI tool: `fend-sentry check` should give instant health insights
- Uses SSH to securely access remote logs (no downloading)
- Beautiful terminal UI with colors and status indicators
- Must feel like `git status` - fast, informative, actionable

## What We're Building

A CLI tool that developers love to use:

```bash
# Setup once
fend-sentry init

# Check app health anytime
fend-sentry check

# Output:
🟢 Fend Marketplace - HEALTHY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Last 24 Hours
   • 12 total requests
   • 2 minor errors (down 67% from yesterday)
   • 0 critical issues

🔍 Recent Issues
   • Payment webhook timeout (payments/views.py:45)
     → Suggested fix: Add retry logic with exponential backoff

✅ System Health
   • Database: Connected
   • Memory: 45% (normal)
   • Response time: 120ms avg

💡 Run `fend-sentry report` for detailed analysis
```

## Technical Requirements

1. **cli.py**: Main command-line interface using Click
   - `fend-sentry init` - Interactive setup wizard
   - `fend-sentry check` - Instant health check
   - `fend-sentry monitor` - Continuous monitoring
   - Beautiful help text and error messages

2. **remote.py**: SSH connection to servers
   - Use paramiko for secure SSH connections
   - Read log files without downloading
   - Support SSH keys and password auth
   - Handle connection errors gracefully

3. **parser.py**: Intelligent log parsing
   - Parse Django error logs remotely
   - Extract: timestamp, level, module, message, traceback
   - Group similar errors (same root cause)
   - Calculate error rates and trends

4. **analyzer.py**: AI-powered analysis
   - Use Gemini 1.5 Flash (free tier: 60 requests/minute)
   - Analyze patterns: "Why are these errors happening?"
   - Suggest specific fixes: "Add retry logic to line 45"
   - Determine severity and urgency

5. **reporter.py**: Beautiful terminal output
   - Use Rich library for colors and formatting
   - Status indicators: 🟢🟡🔴 for health levels
   - Progress bars for analysis
   - Tables for error summaries

## Design Principles
- Fail gracefully - monitoring should never crash
- Clear logging - easy to debug issues
- Testable - each module works independently
- Efficient - minimal resource usage
- Secure - no sensitive data in logs

## Example Error Analysis

Input: ConnectionRefusedError in Django logs

Expected AI output:
```
Severity: CRITICAL
Summary: Database unreachable - 23 failed connections
Root Cause: PostgreSQL container appears offline
Fix: 
1. Check container: docker ps | grep postgres
2. Restart: docker-compose restart db
3. Check logs: docker logs <container-id>
```

## User Experience Goals
- `fend-sentry check` completes in < 5 seconds
- Beautiful, informative output that developers love
- Zero configuration after `init` - just works
- Error messages that help, don't frustrate

## Performance Goals
- < 30MB memory usage (it's a CLI tool)
- SSH connection established in < 2 seconds
- AI analysis completes in < 3 seconds
- Can handle 1000+ log lines efficiently

## Implementation Order
1. **cli.py** - Get the command structure working
2. **remote.py** - SSH connection and log reading
3. **parser.py** - Parse Django logs into structured data
4. **analyzer.py** - AI analysis with Gemini
5. **reporter.py** - Beautiful terminal output

## Expected Output Style

Think `git status` meets `docker ps` - concise, colorful, actionable.

Focus on developer experience - this tool should be a joy to use, not a chore. The goal is developers running `fend-sentry check` before every deployment because it's that useful and fast.

Please implement this as a professional CLI tool that showcases the quality of Fend Labs innovations.