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
from dotenv import load_dotenv

from config import Config, ConfigError
from remote import RemoteConnection, ConnectionError
from parser import LogParser
from analyzer import AIAnalyzer
from reporter import HealthReporter

# Load environment variables
load_dotenv()

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
  chat      Interactive chat with AI about your logs  
  monitor   Continuous monitoring (coming soon)
  config    Show current configuration
        """, title="Welcome", border_style="blue"))

@main.command()
def init():
    """🔧 Quick setup - just 2 questions!"""
    try:
        console.print(Panel.fit("""
[bold blue]🚀 Fend Sentry Setup[/bold blue]

Let's get you monitoring in 30 seconds!
        """, border_style="blue"))
        
        # 1. Get API key
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if not gemini_key:
            console.print("\n[cyan]First, we need your Gemini API key for AI analysis.[/cyan]")
            console.print("[dim]Get one free at: https://makersuite.google.com/app/apikey[/dim]")
            gemini_key = click.prompt("🤖 Gemini API key", hide_input=True)
        else:
            console.print("\n✅ [green]Found Gemini API key in environment[/green]")
        
        # 2. Project name
        console.print("\n[cyan]What's your project name?[/cyan]")
        default_project = os.path.basename(os.getcwd())
        if default_project in ['root', 'home', '']:
            default_project = "My Django App"
        project_name = click.prompt("📱 Project name", default=default_project)
        
        # 3. Environment dropdown
        console.print("\n[cyan]What environment is this?[/cyan]")
        environments = ["production", "staging", "development"]
        for i, env in enumerate(environments, 1):
            console.print(f"  {i}. {env}")
        env_choice = click.prompt("🌍 Environment (1-3)", type=int, default=1) - 1
        environment = environments[env_choice]
        
        # 4. Log path with auto-detection and Docker detection
        console.print("\n[cyan]Where are your Django logs?[/cyan]")
        
        # Check if Docker is available and find containers
        docker_containers = []
        try:
            import subprocess
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                containers = [name.strip() for name in result.stdout.split('\n') if name.strip()]
                # Look for common Django container patterns
                django_containers = [c for c in containers if any(keyword in c.lower() 
                    for keyword in ['web', 'django', 'app', 'backend', 'api'])]
                docker_containers = [f"docker:{c}" for c in django_containers[:3]]  # Top 3
        except:
            pass
        
        possible_paths = docker_containers + [
            "/var/log/django/django.log",
            "/app/logs/django.log", 
            "/app/logs/error.log",
            "./logs/django.log"
        ]
        
        found_logs = []
        for path in possible_paths:
            if path.startswith('docker:') or os.path.exists(path):
                found_logs.append(path)
        
        if docker_containers:
            console.print("🐳 [blue]Docker containers detected![/blue] Recommended for containerized apps:")
            for container in docker_containers[:2]:
                console.print(f"   • {container}")
            console.print("")
        
        if found_logs:
            console.print("🎯 [green]Suggested log paths:[/green]")
            for i, path in enumerate(found_logs, 1):
                console.print(f"  {i}. {path}")
            console.print(f"  {len(found_logs) + 1}. Custom path")
            
            choice = click.prompt(f"📁 Log path (1-{len(found_logs) + 1})", type=int) - 1
            if choice < len(found_logs):
                log_path = found_logs[choice]
            else:
                log_path = click.prompt("📁 Enter custom log path")
        else:
            log_path = click.prompt("📁 Django log file path")
        
        # Build simplified config
        config_data = {
            'app': {
                'name': project_name,
                'log_path': log_path,
                'environment': environment
            },
            'ai': {
                'gemini_api_key': gemini_key
            },
            'monitoring': {
                'check_interval': 300,
                'max_log_lines': 1000
            }
        }
        
        # Save it
        config = Config()
        config.save(config_data)
        
        console.print("\n🎉 [bold green]Ready to go![/bold green]")
        console.print("✨ Run [cyan]fend-sentry check[/cyan] to see your app's health")
        
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
        parser = LogParser()
        analyzer = AIAnalyzer(config_data['ai']['gemini_api_key'])
        
        # Show startup with environment info
        app_display = f"{config_data['app']['name']} ({config_data['app']['environment']})"
        reporter.show_startup(app_display)
        
        # Check if we're in local mode (no server host specified)
        server_host = config_data.get('server', {}).get('host', '')
        log_path = config_data['app']['log_path']
        max_lines = config_data['monitoring']['max_log_lines']
        
        if not server_host or server_host == 'localhost':
            # LOCAL MODE - Read log file directly or Docker logs
            with reporter.status("Reading logs..."):
                try:
                    if log_path.startswith('docker:'):
                        # Docker logs
                        import subprocess
                        container_name = log_path.replace('docker:', '')
                        result = subprocess.run(
                            ['docker', 'logs', '--tail', str(max_lines), container_name],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode != 0:
                            raise ConnectionError(f"Docker logs failed: {result.stderr}")
                        
                        # Docker logs can go to either stdout or stderr, combine both
                        combined_output = result.stdout + result.stderr
                        log_data = [line.strip() for line in combined_output.split('\n') if line.strip()]
                        
                        if not log_data:
                            raise ConnectionError(f"No logs found for container: {container_name}")
                    else:
                        # Regular file
                        with open(log_path, 'r') as f:
                            lines = f.readlines()
                        # Get last N lines
                        log_data = [line.strip() for line in lines[-max_lines:] if line.strip()]
                except FileNotFoundError:
                    raise ConnectionError(f"Log file not found: {log_path}")
                except subprocess.TimeoutExpired:
                    raise ConnectionError("Docker logs command timed out")
                except Exception as e:
                    raise ConnectionError(f"Failed to read logs: {e}")
        else:
            # REMOTE MODE - Use SSH
            remote = RemoteConnection(config_data['server'])
            
            with reporter.status("Connecting to server..."):
                remote.connect()
            
            with reporter.status("Reading application logs..."):
                log_data = remote.read_log_file(log_path, lines=max_lines)
            
            # Cleanup connection
            remote.disconnect()
        
        # Parse logs
        with reporter.status("Parsing log entries..."):
            parsed_logs = parser.parse_logs(log_data)
        
        # AI Analysis
        with reporter.status("Running AI analysis..."):
            analysis = analyzer.analyze_logs(parsed_logs, config_data['app']['name'])
        
        # Generate report
        reporter.show_health_report(analysis, parsed_logs)
        
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
def chat():
    """💬 Interactive chat with AI about your logs"""
    try:
        # Load configuration
        config = Config()
        config_data = config.load_with_env_fallback()
        
        if not config_data['ai']['gemini_api_key']:
            console.print("❌ [red]Gemini API key not found![/red]")
            console.print("💡 Set [cyan]GEMINI_API_KEY[/cyan] environment variable or run [cyan]fend-sentry init[/cyan]")
            sys.exit(1)
        
        # Initialize components
        parser = LogParser()
        analyzer = AIAnalyzer(config_data['ai']['gemini_api_key'])
        
        console.print(Panel.fit(f"""
[bold blue]💬 Fend Sentry Chat[/bold blue]

Chat with AI about your [cyan]{config_data['app']['name']}[/cyan] logs.
Type 'exit' or 'quit' to end the session.

[dim]Examples:[/dim]
• "What were the recent errors?"
• "Explain the database warnings"  
• "Are there any performance issues?"
        """, border_style="blue"))
        
        # Get recent logs once
        server_host = config_data.get('server', {}).get('host', '')
        log_path = config_data['app']['log_path']
        max_lines = min(config_data['monitoring']['max_log_lines'], 500)  # Limit for chat
        
        with console.status("Loading recent logs..."):
            if not server_host or server_host == 'localhost':
                # LOCAL MODE
                try:
                    if log_path.startswith('docker:'):
                        import subprocess
                        container_name = log_path.replace('docker:', '')
                        result = subprocess.run(
                            ['docker', 'logs', '--tail', str(max_lines), container_name],
                            capture_output=True, text=True, timeout=30
                        )
                        combined_output = result.stdout + result.stderr
                        log_data = [line.strip() for line in combined_output.split('\n') if line.strip()]
                    else:
                        with open(log_path, 'r') as f:
                            lines = f.readlines()
                        log_data = [line.strip() for line in lines[-max_lines:] if line.strip()]
                except Exception as e:
                    console.print(f"❌ [red]Failed to load logs: {e}[/red]")
                    sys.exit(1)
            else:
                # REMOTE MODE
                remote = RemoteConnection(config_data['server'])
                remote.connect()
                log_data = remote.read_log_file(log_path, lines=max_lines)
                remote.disconnect()
        
        parsed_logs = parser.parse_logs(log_data)
        console.print(f"✅ Loaded {len(log_data)} log entries")
        
        # Chat loop
        while True:
            try:
                question = click.prompt("\n[bold blue]>[/bold blue]", prompt_suffix=" ")
                
                if question.lower() in ['exit', 'quit', 'bye']:
                    console.print("👋 [green]Goodbye![/green]")
                    break
                
                with console.status("🤔 Analyzing..."):
                    # Create a chat-focused prompt with full log context
                    response = analyzer.chat_about_logs(parsed_logs, question, config_data['app']['name'], log_data)
                
                console.print(f"\n[dim]💬[/dim] {response}")
                
            except (KeyboardInterrupt, click.Abort):
                console.print("\n👋 [green]Goodbye![/green]")
                break
            except Exception as e:
                console.print(f"\n❌ [red]Error: {e}[/red]")
                
    except Exception as e:
        console.print(f"❌ [red]Chat failed: {e}[/red]")
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
        
        console.print(Panel.fit(f"""
[bold blue]⚙️ Current Configuration[/bold blue]

[yellow]Project:[/yellow]
  Name: {config_data['app']['name']}
  Environment: {config_data['app']['environment']}
  Log Path: {config_data['app']['log_path']}

[yellow]Monitoring:[/yellow]
  Check Interval: {config_data['monitoring']['check_interval']} seconds
  Max Log Lines: {config_data['monitoring']['max_log_lines']}

[yellow]AI:[/yellow]
  Gemini API: {'✅ ' + api_key if api_key else '❌ Missing'}

[dim]🔍 Use [cyan]--show-secrets[/cyan] to show masked values[/dim]
[dim]🔧 Run [cyan]fend-sentry init[/cyan] to reconfigure[/dim]
        """, border_style="blue"))
        
    except ConfigError as e:
        console.print(f"❌ [red]Configuration error: {e}[/red]")
        console.print("💡 Run [cyan]fend-sentry init[/cyan] to setup configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()