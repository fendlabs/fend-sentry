"""
AI Analysis module using Gemini for Fend Sentry

Provides intelligent analysis of Django application logs using Google's Gemini AI,
offering insights, root cause analysis, and actionable fix suggestions.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

@dataclass
class AnalysisResult:
    """AI analysis result"""
    health_status: str  # HEALTHY, WARNING, CRITICAL
    summary: str
    error_count: int
    warning_count: int
    recent_issues: List[Dict[str, Any]]
    suggestions: List[str]
    system_health: Dict[str, Any]
    trends: Dict[str, Any]
    analysis_timestamp: datetime

class AIAnalyzer:
    """AI-powered log analyzer using Gemini"""
    
    def __init__(self, api_key: str):
        """Initialize AI analyzer
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Use Gemini 1.5 Flash for fast, efficient analysis
        self.model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
    
    def analyze_logs(self, parsed_logs: Dict[str, Any], app_name: str) -> AnalysisResult:
        """Analyze parsed logs and generate insights
        
        Args:
            parsed_logs: Dictionary from LogParser.parse_logs()
            app_name: Name of the Django application
            
        Returns:
            AnalysisResult with AI-generated insights
        """
        try:
            # Prepare log summary for AI
            log_summary = self._create_log_summary(parsed_logs)
            
            # Generate AI analysis
            ai_response = self._query_gemini(log_summary, app_name)
            
            # Process AI response
            analysis = self._process_ai_response(ai_response, parsed_logs)
            
            return analysis
            
        except Exception as e:
            # Fallback analysis if AI fails
            return self._create_fallback_analysis(parsed_logs, f"AI analysis failed: {e}")
    
    def _create_log_summary(self, parsed_logs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a concise summary for AI analysis"""
        error_groups = parsed_logs.get('error_groups', [])
        recent_errors = parsed_logs.get('recent_errors', [])
        level_counts = parsed_logs.get('level_counts', {})
        
        # Summarize error groups
        error_summaries = []
        for group in error_groups[:5]:  # Top 5 error groups
            if group.example_entry:
                error_summaries.append({
                    'count': group.count,
                    'message': group.example_entry.message[:200],  # Truncate long messages
                    'logger': group.example_entry.logger,
                    'traceback': group.example_entry.traceback[:3] if group.example_entry.traceback else []
                })
        
        # Recent error samples  
        recent_error_samples = []
        for error in recent_errors[-3:]:  # Last 3 errors
            recent_error_samples.append({
                'timestamp': error.timestamp.isoformat() if error.timestamp else 'unknown',
                'message': error.message[:150],
                'logger': error.logger,
                'url_path': error.url_path,
                'ip_address': error.ip_address
            })
        
        return {
            'total_entries': parsed_logs.get('total_entries', 0),
            'level_counts': level_counts,
            'error_groups': error_summaries,
            'recent_errors': recent_error_samples,
            'analysis_period': '1 hour'
        }
    
    def _query_gemini(self, log_summary: Dict[str, Any], app_name: str) -> str:
        """Query Gemini AI for log analysis"""
        prompt = self._build_analysis_prompt(log_summary, app_name)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    def _build_analysis_prompt(self, log_summary: Dict[str, Any], app_name: str) -> str:
        """Build the AI analysis prompt"""
        return f"""You are an expert Django application monitoring system. Analyze the following log data from "{app_name}" and provide a JSON response with insights.

LOG SUMMARY:
{json.dumps(log_summary, indent=2)}

Please analyze this Django application's health and provide a JSON response with the following structure:

{{
  "health_status": "HEALTHY|WARNING|CRITICAL",
  "summary": "Brief 1-2 sentence summary of application health",
  "key_issues": [
    {{
      "type": "error|warning|performance",
      "description": "Clear description of the issue",
      "severity": "low|medium|high|critical",
      "affected_component": "specific Django component/view/model",
      "suggested_fix": "Specific actionable fix recommendation"
    }}
  ],
  "system_insights": {{
    "error_trends": "Are errors increasing/decreasing/stable?",
    "common_patterns": "What patterns do you see in the errors?",
    "risk_assessment": "What are the biggest risks right now?"
  }},
  "immediate_actions": [
    "Prioritized list of immediate actions to take"
  ],
  "monitoring_suggestions": [
    "What should be monitored more closely?"
  ]
}}

ANALYSIS GUIDELINES:
- Focus on actionable insights, not just descriptions
- Identify root causes when possible
- Consider Django-specific patterns (database connections, middleware, views, etc.)
- Suggest specific fixes with line numbers or code examples when applicable
- Prioritize critical issues that could cause downtime
- If errors are database-related, suggest connection pool, query optimization, or infrastructure checks
- If HTTP errors, suggest rate limiting, load balancing, or code fixes
- Be concise but specific

Respond ONLY with valid JSON, no additional text."""
    
    def _process_ai_response(self, ai_response: str, parsed_logs: Dict[str, Any]) -> AnalysisResult:
        """Process AI response into AnalysisResult"""
        try:
            # Parse JSON response
            ai_data = json.loads(ai_response)
            
            # Extract data with fallbacks
            health_status = ai_data.get('health_status', 'WARNING')
            summary = ai_data.get('summary', 'Application analysis completed')
            key_issues = ai_data.get('key_issues', [])
            system_insights = ai_data.get('system_insights', {})
            immediate_actions = ai_data.get('immediate_actions', [])
            monitoring_suggestions = ai_data.get('monitoring_suggestions', [])
            
            # Count errors and warnings
            level_counts = parsed_logs.get('level_counts', {})
            error_count = level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0)
            warning_count = level_counts.get('WARNING', 0)
            
            # Format recent issues
            recent_issues = []
            for issue in key_issues:
                recent_issues.append({
                    'type': issue.get('type', 'unknown'),
                    'description': issue.get('description', ''),
                    'severity': issue.get('severity', 'medium'),
                    'component': issue.get('affected_component', 'unknown'),
                    'fix': issue.get('suggested_fix', '')
                })
            
            # Combine suggestions
            suggestions = immediate_actions + monitoring_suggestions
            
            # System health assessment
            system_health = {
                'status': health_status,
                'error_rate': self._calculate_error_rate(parsed_logs),
                'trends': system_insights.get('error_trends', 'Unknown'),
                'patterns': system_insights.get('common_patterns', 'None identified'),
                'risks': system_insights.get('risk_assessment', 'Assessment pending')
            }
            
            return AnalysisResult(
                health_status=health_status,
                summary=summary,
                error_count=error_count,
                warning_count=warning_count,
                recent_issues=recent_issues,
                suggestions=suggestions,
                system_health=system_health,
                trends=self._calculate_trends(parsed_logs),
                analysis_timestamp=datetime.now()
            )
            
        except json.JSONDecodeError:
            # If JSON parsing fails, create a basic analysis
            return self._create_fallback_analysis(parsed_logs, "AI response parsing failed")
    
    def _create_fallback_analysis(self, parsed_logs: Dict[str, Any], error_msg: str) -> AnalysisResult:
        """Create basic analysis when AI fails"""
        level_counts = parsed_logs.get('level_counts', {})
        error_count = level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0)
        warning_count = level_counts.get('WARNING', 0)
        
        # Determine health status based on error counts
        if error_count > 10:
            health_status = 'CRITICAL'
            summary = f"High error rate detected: {error_count} errors found"
        elif error_count > 0 or warning_count > 5:
            health_status = 'WARNING'
            summary = f"Some issues detected: {error_count} errors, {warning_count} warnings"
        else:
            health_status = 'HEALTHY'
            summary = "No significant issues detected"
        
        # Basic issue analysis
        recent_issues = []
        error_groups = parsed_logs.get('error_groups', [])
        for group in error_groups[:3]:
            if group.example_entry:
                recent_issues.append({
                    'type': 'error',
                    'description': group.example_entry.message[:100],
                    'severity': 'high' if group.count > 5 else 'medium',
                    'component': group.example_entry.logger,
                    'fix': 'Manual investigation required'
                })
        
        suggestions = [
            "Review application logs for detailed error information",
            "Check database connectivity and performance",
            "Monitor system resources (CPU, memory, disk)",
            f"Note: {error_msg}"
        ]
        
        return AnalysisResult(
            health_status=health_status,
            summary=summary,
            error_count=error_count,
            warning_count=warning_count,
            recent_issues=recent_issues,
            suggestions=suggestions,
            system_health={
                'status': health_status,
                'error_rate': self._calculate_error_rate(parsed_logs),
                'trends': 'Unknown (AI analysis failed)',
                'patterns': 'Manual analysis required',
                'risks': 'Assessment unavailable'
            },
            trends=self._calculate_trends(parsed_logs),
            analysis_timestamp=datetime.now()
        )
    
    def _calculate_error_rate(self, parsed_logs: Dict[str, Any]) -> str:
        """Calculate error rate as a percentage"""
        total_entries = parsed_logs.get('total_entries', 0)
        level_counts = parsed_logs.get('level_counts', {})
        error_count = level_counts.get('ERROR', 0) + level_counts.get('CRITICAL', 0)
        
        if total_entries == 0:
            return "0%"
        
        error_rate = (error_count / total_entries) * 100
        return f"{error_rate:.1f}%"
    
    def _calculate_trends(self, parsed_logs: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate basic trends from log data"""
        # This is a simplified trend calculation
        # In a real implementation, you'd compare with historical data
        
        error_groups = parsed_logs.get('error_groups', [])
        level_counts = parsed_logs.get('level_counts', {})
        
        return {
            'total_unique_errors': len(error_groups),
            'most_common_error': error_groups[0].example_entry.message[:50] if error_groups else 'None',
            'error_distribution': dict(level_counts),
            'analysis_coverage': f"{parsed_logs.get('total_entries', 0)} log entries analyzed"
        }
    
    def test_connection(self) -> bool:
        """Test if Gemini API is accessible"""
        try:
            # Simple test query
            response = self.model.generate_content("Respond with just 'OK' if you can read this.")
            return 'OK' in response.text
        except Exception:
            return False