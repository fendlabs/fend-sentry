"""
Beautiful terminal reporting with Rich for Fend Sentry

Creates stunning terminal output that developers love to see,
with colors, progress indicators, and clear health summaries.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.columns import Columns
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich import box

from analyzer import AnalysisResult

class HealthReporter:
    """Beautiful terminal health reporting"""
    
    # Health status colors and icons
    STATUS_STYLES = {
        'HEALTHY': ('🟢', 'green', 'HEALTHY'),
        'WARNING': ('🟡', 'yellow', 'WARNING'), 
        'CRITICAL': ('🔴', 'red', 'CRITICAL'),
        'UNKNOWN': ('⚪', 'white', 'UNKNOWN')
    }
    
    def __init__(self, console: Console, verbose: bool = False):
        """Initialize reporter
        
        Args:
            console: Rich console instance
            verbose: Show detailed output
        """
        self.console = console
        self.verbose = verbose
    
    @contextmanager
    def status(self, message: str):
        """Show a spinner with status message"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            progress.add_task(description=message, total=None)
            yield
    
    def show_startup(self, app_name: str):
        """Show startup banner"""
        startup_text = Text()
        startup_text.append("🚀 ", style="blue")
        startup_text.append("Fend Sentry", style="bold blue")
        startup_text.append(" - Checking ", style="dim")
        startup_text.append(app_name, style="bold cyan")
        
        self.console.print()
        self.console.print(Panel.fit(
            startup_text,
            border_style="blue",
            padding=(0, 1)
        ))
        self.console.print()
    
    def show_health_report(self, analysis: AnalysisResult, parsed_logs: Dict[str, Any]):
        """Show complete health analysis report"""
        # Header with app status
        self._show_health_header(analysis)
        
        # Main metrics
        self._show_metrics_section(analysis, parsed_logs)
        
        # Recent issues (if any)
        if analysis.recent_issues:
            self._show_issues_section(analysis)
        
        # System health
        self._show_system_health(analysis)
        
        # AI suggestions
        if analysis.suggestions:
            self._show_suggestions_section(analysis)
        
        # Verbose details
        if self.verbose:
            self._show_verbose_details(parsed_logs)
        
        # Footer
        self._show_footer()
    
    def _show_health_header(self, analysis: AnalysisResult):
        """Show main health status header"""
        status = analysis.health_status
        icon, color, label = self.STATUS_STYLES.get(status, self.STATUS_STYLES['UNKNOWN'])
        
        # Create header text
        header_text = Text()
        header_text.append(f"{icon} ", style=color)
        header_text.append("Application Status: ", style="bold")
        header_text.append(label, style=f"bold {color}")
        
        # Summary
        summary_text = Text(analysis.summary, style="dim")
        
        # Combine header and summary
        content = Text()
        content.append_text(header_text)
        content.append("\n")
        content.append_text(summary_text)
        
        self.console.print(Panel.fit(
            content,
            border_style=color,
            padding=(0, 1)
        ))
        self.console.print()
    
    def _show_metrics_section(self, analysis: AnalysisResult, parsed_logs: Dict[str, Any]):
        """Show key metrics"""
        # Create metrics table
        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="bold")
        table.add_column("Details", style="dim")
        
        # Add metrics
        total_entries = parsed_logs.get('total_entries', 0)
        table.add_row(
            "📊 Log Entries",
            str(total_entries),
            "analyzed in last check"
        )
        
        if analysis.error_count > 0:
            table.add_row(
                "❌ Errors",
                str(analysis.error_count),
                self._get_trend_indicator(analysis.error_count, "errors")
            )
        
        if analysis.warning_count > 0:
            table.add_row(
                "⚠️  Warnings", 
                str(analysis.warning_count),
                self._get_trend_indicator(analysis.warning_count, "warnings")
            )
        
        error_rate = analysis.system_health.get('error_rate', '0%')
        table.add_row(
            "📈 Error Rate",
            error_rate,
            "of total log entries"
        )
        
        self.console.print(Panel(
            table,
            title="📊 Last 24 Hours",
            border_style="blue",
            padding=(0, 1)
        ))
        self.console.print()
    
    def _show_issues_section(self, analysis: AnalysisResult):
        """Show recent issues with AI insights"""
        # Create issues table
        table = Table(show_header=True, box=box.ROUNDED, expand=True)
        table.add_column("Issue", style="red", width=40)
        table.add_column("Severity", justify="center", width=10)
        table.add_column("Component", style="cyan", width=15)
        table.add_column("Suggested Fix", style="green")
        
        for issue in analysis.recent_issues[:5]:  # Show top 5 issues
            severity_style = self._get_severity_style(issue.get('severity', 'medium'))
            
            table.add_row(
                issue.get('description', 'Unknown issue')[:60] + "...",
                Text(issue.get('severity', 'medium').upper(), style=severity_style),
                issue.get('component', 'unknown'),
                issue.get('fix', 'Manual investigation required')[:50] + "..."
            )
        
        self.console.print(Panel(
            table,
            title="🔍 Recent Issues",
            border_style="red",
            padding=(0, 1)
        ))
        self.console.print()
    
    def _show_system_health(self, analysis: AnalysisResult):
        """Show system health indicators"""
        system_health = analysis.system_health
        status = system_health.get('status', 'UNKNOWN')
        icon, color, _ = self.STATUS_STYLES.get(status, self.STATUS_STYLES['UNKNOWN'])
        
        # Create health indicators
        health_items = []
        
        # Connection status (assume healthy if we got this far)
        health_items.append(f"🔗 Connection: [green]✅ Connected[/green]")
        
        # Error rate
        error_rate = system_health.get('error_rate', '0%')
        rate_color = 'red' if float(error_rate.rstrip('%')) > 5 else 'green'
        health_items.append(f"📊 Error Rate: [{rate_color}]{error_rate}[/{rate_color}]")
        
        # Trends
        trends = system_health.get('trends', 'Unknown')
        health_items.append(f"📈 Trends: [yellow]{trends}[/yellow]")
        
        # Patterns
        patterns = system_health.get('patterns', 'None identified')
        health_items.append(f"🔍 Patterns: [blue]{patterns[:50]}[/blue]")
        
        # Create content
        content = "\n".join(health_items)
        
        self.console.print(Panel(
            content,
            title=f"{icon} System Health",
            border_style=color,
            padding=(0, 1)
        ))
        self.console.print()
    
    def _show_suggestions_section(self, analysis: AnalysisResult):
        """Show AI-generated suggestions"""
        # Create suggestions tree
        tree = Tree("💡 [bold cyan]AI Recommendations[/bold cyan]")
        
        for i, suggestion in enumerate(analysis.suggestions[:5], 1):
            suggestion_node = tree.add(f"[yellow]{i}.[/yellow] {suggestion}")
        
        self.console.print(Panel(
            tree,
            title="💡 Suggestions",
            border_style="cyan",
            padding=(0, 1)
        ))
        self.console.print()
    
    def _show_verbose_details(self, parsed_logs: Dict[str, Any]):
        """Show detailed verbose information"""
        if not self.verbose:
            return
        
        self.console.print(Rule("[dim]Verbose Details[/dim]"))
        
        # Error groups detail
        error_groups = parsed_logs.get('error_groups', [])
        if error_groups:
            table = Table(show_header=True, box=box.SIMPLE, expand=True)
            table.add_column("Count", justify="right", width=8)
            table.add_column("Error Type", width=20)
            table.add_column("Logger", width=15)
            table.add_column("Message", style="dim")
            
            for group in error_groups[:10]:
                if group.example_entry:
                    table.add_row(
                        str(group.count),
                        group.signature[:15] + "..." if len(group.signature) > 15 else group.signature,
                        group.example_entry.logger,
                        group.example_entry.message[:50] + "..."
                    )
            
            self.console.print(Panel(
                table,
                title="Error Groups Detail",
                border_style="dim",
                padding=(0, 1)
            ))
        
        # Trends detail
        trends = getattr(analysis, 'trends', {})
        if trends:
            trend_table = Table(show_header=False, box=box.SIMPLE)
            trend_table.add_column("Metric", style="cyan")
            trend_table.add_column("Value", style="bold")
            
            for key, value in trends.items():
                trend_table.add_row(key.replace('_', ' ').title(), str(value))
            
            self.console.print(Panel(
                trend_table,
                title="Analysis Trends",
                border_style="dim",
                padding=(0, 1)
            ))
        
        self.console.print()
    
    def _show_footer(self):
        """Show footer with next steps"""
        footer_text = Text()
        footer_text.append("💡 ", style="yellow")
        footer_text.append("Next: Run ", style="dim")
        footer_text.append("fend-sentry monitor", style="bold cyan")
        footer_text.append(" for continuous monitoring", style="dim")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        footer_text.append(f"\n🕒 Analysis completed at {timestamp}", style="dim")
        
        self.console.print(Panel.fit(
            footer_text,
            border_style="dim",
            padding=(0, 1)
        ))
    
    def _get_trend_indicator(self, value: int, item_type: str) -> str:
        """Get trend indicator for metrics"""
        # This would ideally compare with historical data
        # For now, provide general guidance
        if value == 0:
            return "🟢 None detected"
        elif value < 5:
            return "🟡 Low volume"  
        elif value < 20:
            return "🟠 Moderate"
        else:
            return "🔴 High volume"
    
    def _get_severity_style(self, severity: str) -> str:
        """Get color style for severity levels"""
        severity_map = {
            'low': 'green',
            'medium': 'yellow', 
            'high': 'red',
            'critical': 'bold red'
        }
        return severity_map.get(severity.lower(), 'white')
    
    def show_error(self, message: str, details: Optional[str] = None):
        """Show error message"""
        content = f"[red]❌ {message}[/red]"
        if details:
            content += f"\n[dim]{details}[/dim]"
        
        self.console.print(Panel(
            content,
            title="Error",
            border_style="red",
            padding=(0, 1)
        ))
    
    def show_warning(self, message: str):
        """Show warning message"""
        content = f"[yellow]⚠️  {message}[/yellow]"
        
        self.console.print(Panel(
            content,
            title="Warning", 
            border_style="yellow",
            padding=(0, 1)
        ))
    
    def show_success(self, message: str):
        """Show success message"""
        content = f"[green]✅ {message}[/green]"
        
        self.console.print(Panel(
            content,
            title="Success",
            border_style="green", 
            padding=(0, 1)
        ))