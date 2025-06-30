#!/usr/bin/env python3
"""
Fend Sentry - AI-Powered Django Monitoring CLI

A beautiful CLI tool that gives instant AI-powered insights into Django application health.
Uses SSH to securely access remote logs without downloading them.
"""

import click
import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from config import Config, ConfigError
from remote import RemoteConnection, ConnectionError
from parser import LogParser
from analyzer import AIAnalyzer
from reporter import HealthReporter

console = Console()

@click.group(invoke_without_command=True)
@click.pass_context  
@click.version_option(version="0.1.0", prog_name="fend-sentry")
def main(ctx):
    """
    🚀 Fend Sentry - AI-Powered Django Monitoring
    
    Get instant health insights for your Django applications.
    Uses AI to understand errors and suggest fixes.
    """
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit("""
[bold blue]🚀 Fend Sentry[/bold blue] - AI-Powered Django Monitoring

[dim]Get instant health insights for your Django applications.[/dim]

[yellow]Quick Start:[/yellow]
  fend-sentry init     Setup configuration
  fend-sentry check    Check application health

[yellow]Commands:[/yellow]
  init      Interactive configuration setup
  check     Instant health check with AI insights  
  monitor   Continuous monitoring (coming soon)
  config    Show current configuration
        """, title="Welcome", border_style="blue"))

@main.command()
@click.option('--skip-prompts', is_flag=True, help='Use environment variables and defaults')
def init(skip_prompts):
    """🔧 Interactive setup wizard"""
    try:
        config = Config()
        
        console.print(Panel.fit("""
[bold blue]🔧 Fend Sentry Setup[/bold blue]

Let's configure your Django monitoring setup.
[dim]Environment variables will be used as defaults when available.[/dim]
        """, border_style="blue"))
        
        # Get environment defaults
        env_defaults = config.get_env_defaults()
        
        if skip_prompts:
            console.print("📋 [cyan]Using environment variables and defaults...[/cyan]")
            config_data = env_defaults
        else:
            # Server configuration
            console.print("\n[bold cyan]📡 Server Configuration[/bold cyan]")
            server_host = click.prompt(
                "🌐 Server hostname or IP", 
                default=env_defaults['server']['host']
            )
            server_port = click.prompt(
                "🔌 SSH port", 
                default=env_defaults['server']['port'], 
                type=int
            )
            username = click.prompt(
                "👤 SSH username", 
                default=env_defaults['server']['username']
            )
            
            # SSH authentication
            auth_method = click.prompt(
                "🔐 Authentication method", 
                type=click.Choice(['key', 'password']), 
                default='key' if not env_defaults['server']['password'] else 'password'
            )
            
            if auth_method == 'key':
                private_key_path = click.prompt(
                    "🔑 SSH private key path", 
                    default=env_defaults['server']['private_key_path']
                )
                password = None
            else:
                private_key_path = None
                password = click.prompt("🔒 SSH password", hide_input=True)
            
            # Application configuration
            console.print("\n[bold cyan]🏗️  Application Configuration[/bold cyan]")
            app_name = click.prompt(
                "🏷️  Application name", 
                default=env_defaults['app']['name']
            )
            log_path = click.prompt(
                "📁 Django log file path on server", 
                default=env_defaults['app']['log_path']
            )
            app_env = click.prompt(
                "🌍 Environment (prod/staging/dev)", 
                default=env_defaults['app']['environment']
            )
            
            # AI configuration
            console.print("\n[bold cyan]🤖 AI Configuration[/bold cyan]")
            gemini_key = env_defaults['ai']['gemini_api_key']
            if not gemini_key:
                gemini_key = click.prompt("🔑 Gemini API key", hide_input=True)
            else:
                console.print(f"✅ Using Gemini API key from environment")
            
            # Monitoring configuration
            console.print("\n[bold cyan]📊 Monitoring Configuration[/bold cyan]")
            check_interval = click.prompt(
                "⏱️  Check interval (seconds)", 
                default=env_defaults['monitoring']['check_interval'],
                type=int
            )
            max_log_lines = click.prompt(
                "📄 Max log lines to analyze", 
                default=env_defaults['monitoring']['max_log_lines'],
                type=int
            )
            
            # Alert configuration (optional)
            console.print("\n[bold cyan]🚨 Alert Configuration (Optional)[/bold cyan]")
            alert_email = click.prompt(
                "📧 Alert email", 
                default=env_defaults['alerts']['email'],
                show_default=False
            ) or ""
            
            webhook_url = click.prompt(
                "🪝 Webhook URL (Slack/Discord)", 
                default=env_defaults['alerts']['webhook_url'],
                show_default=False
            ) or ""
            
            # Build configuration
            config_data = {
                'server': {
                    'host': server_host,
                    'port': server_port,
                    'username': username,
                    'private_key_path': private_key_path,
                    'password': password
                },
                'app': {
                    'name': app_name,
                    'log_path': log_path,
                    'environment': app_env
                },
                'ai': {
                    'gemini_api_key': gemini_key
                },
                'monitoring': {
                    'check_interval': check_interval,
                    'max_log_lines': max_log_lines
                },
                'alerts': {
                    'email': alert_email,
                    'webhook_url': webhook_url,
                    'enabled': bool(alert_email or webhook_url)
                }
            }
        
        # Save configuration
        config.save(config_data)
        
        console.print("\n✅ [green]Configuration saved successfully![/green]")
        console.print("🚀 Run [cyan]fend-sentry check[/cyan] to test your setup")
        
        # Show summary
        console.print(f"\n📋 [dim]Monitoring: {config_data['app']['name']} ({config_data['app']['environment']})[/dim]")
        console.print(f"🔄 [dim]Check interval: {config_data['monitoring']['check_interval']} seconds[/dim]")
        
    except (KeyboardInterrupt, click.Abort):
        console.print("\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ [red]Setup failed: {e}[/red]")
        sys.exit(1)

@main.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed analysis')
def check(verbose):
    """⚡ Instant health check with AI insights"""
    try:
        # Load configuration with environment fallbacks
        config = Config()
        config_data = config.load_with_env_fallback()
        
        # Validate critical settings
        if not config_data['ai']['gemini_api_key']:
            console.print("❌ [red]Gemini API key not found![/red]")
            console.print("💡 Set [cyan]GEMINI_API_KEY[/cyan] environment variable or run [cyan]fend-sentry init[/cyan]")
            sys.exit(1)
        
        # Initialize components
        reporter = HealthReporter(console, verbose=verbose)
        remote = RemoteConnection(config_data['server'])
        parser = LogParser()
        analyzer = AIAnalyzer(config_data['ai']['gemini_api_key'])
        
        # Show startup with environment info
        app_display = f"{config_data['app']['name']} ({config_data['app']['environment']})"
        reporter.show_startup(app_display)
        
        # Connect to server
        with reporter.status("Connecting to server..."):
            remote.connect()
        
        # Read recent logs
        max_lines = config_data['monitoring']['max_log_lines']
        with reporter.status("Reading application logs..."):
            log_data = remote.read_log_file(
                config_data['app']['log_path'], 
                lines=max_lines
            )
        
        # Parse logs
        with reporter.status("Parsing log entries..."):
            parsed_logs = parser.parse_logs(log_data)
        
        # AI Analysis
        with reporter.status("Running AI analysis..."):
            analysis = analyzer.analyze_logs(parsed_logs, config_data['app']['name'])
        
        # Generate report
        reporter.show_health_report(analysis, parsed_logs)
        
        # Cleanup
        remote.disconnect()
        
    except ConfigError as e:
        console.print(f"❌ [red]Configuration error: {e}[/red]")
        console.print("💡 Run [cyan]fend-sentry init[/cyan] to setup configuration")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"❌ [red]Connection error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n❌ Check cancelled")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [red]Check failed: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)

@main.command()
def monitor():
    """🔄 Continuous monitoring (coming soon)"""
    console.print("🚧 [yellow]Continuous monitoring is coming in v0.2![/yellow]")
    console.print("For now, you can run [cyan]fend-sentry check[/cyan] periodically")

@main.command()
@click.option('--show-secrets', is_flag=True, help='Show API keys and passwords')
def config(show_secrets):
    """⚙️  Show current configuration"""
    try:
        config = Config()
        config_data = config.load_with_env_fallback()
        
        # Mask sensitive data unless requested
        api_key = config_data['ai']['gemini_api_key']
        if api_key and not show_secrets:
            api_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        
        webhook_url = config_data['alerts']['webhook_url']
        if webhook_url and not show_secrets:
            webhook_url = webhook_url[:20] + "..." if len(webhook_url) > 20 else "***"
        
        console.print(Panel.fit(f"""
[bold blue]⚙️ Current Configuration[/bold blue]

[yellow]Server:[/yellow]
  Host: {config_data['server']['host']}
  Port: {config_data['server']['port']}
  User: {config_data['server']['username']}
  Auth: {'SSH Key' if config_data['server'].get('private_key_path') else 'Password'}

[yellow]Application:[/yellow]
  Name: {config_data['app']['name']}
  Environment: {config_data['app']['environment']}
  Log Path: {config_data['app']['log_path']}

[yellow]Monitoring:[/yellow]
  Check Interval: {config_data['monitoring']['check_interval']} seconds
  Max Log Lines: {config_data['monitoring']['max_log_lines']}

[yellow]AI:[/yellow]
  Gemini API: {'✅ ' + api_key if api_key else '❌ Missing'}

[yellow]Alerts:[/yellow]
  Email: {config_data['alerts']['email'] or 'Not configured'}
  Webhook: {webhook_url or 'Not configured'}
  Enabled: {'✅ Yes' if config_data['alerts']['enabled'] else '❌ No'}

[dim]🔍 Use [cyan]--show-secrets[/cyan] to show masked values[/dim]
[dim]🔧 Run [cyan]fend-sentry init[/cyan] to reconfigure[/dim]
        """, border_style="blue"))
        
    except ConfigError as e:
        console.print(f"❌ [red]Configuration error: {e}[/red]")
        console.print("💡 Run [cyan]fend-sentry init[/cyan] to setup configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()