#!/usr/bin/env python3
"""
Test script to validate Fend Sentry components without requiring a real server
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from parser import LogParser
from analyzer import AIAnalyzer
from reporter import HealthReporter
from rich.console import Console

# Load environment variables
load_dotenv()

# Sample Django log data for testing
SAMPLE_DJANGO_LOGS = [
    "[2024-06-30 16:20:01,123] ERROR django.request: Internal Server Error: /api/payments/",
    "Traceback (most recent call last):",
    '  File "/app/payments/views.py", line 45, in process_payment',
    "    result = stripe.charge.create(amount=amount)",
    "ConnectionError: Could not connect to Stripe API",
    "",
    "[2024-06-30 16:21:15,456] WARNING django.security: Suspicious operation: Invalid session key",
    "[2024-06-30 16:21:20,789] INFO django.request: GET /health/ 200",
    "[2024-06-30 16:22:01,111] ERROR django.db: Database connection lost",
    "Traceback (most recent call last):",
    '  File "/app/models.py", line 123, in save',
    "    super().save(*args, **kwargs)",
    "OperationalError: (2006, 'MySQL server has gone away')",
    "",
    "[2024-06-30 16:23:10,333] INFO django.request: POST /api/users/ 201",
    "[2024-06-30 16:24:01,555] ERROR django.request: Internal Server Error: /api/payments/",
    "ConnectionError: Could not connect to Stripe API",
]

def test_log_parsing():
    """Test the log parser with sample data"""
    print("🔍 Testing Log Parser...")
    
    parser = LogParser()
    parsed_logs = parser.parse_logs(SAMPLE_DJANGO_LOGS)
    
    print(f"✅ Parsed {parsed_logs['total_entries']} log entries")
    print(f"✅ Found {len(parsed_logs['error_groups'])} error groups")
    print(f"✅ Error counts: {parsed_logs['level_counts']}")
    
    return parsed_logs

def test_ai_analysis(parsed_logs):
    """Test AI analysis (requires Gemini API key)"""
    print("🤖 Testing AI Analysis...")
    
    try:
        import os
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  No GEMINI_API_KEY found, skipping AI test")
            return None
        
        analyzer = AIAnalyzer(api_key)
        analysis = analyzer.analyze_logs(parsed_logs, "Test Django App")
        
        print(f"✅ AI Analysis completed: {analysis.health_status}")
        print(f"✅ Found {len(analysis.recent_issues)} issues")
        print(f"✅ Generated {len(analysis.suggestions)} suggestions")
        
        return analysis
        
    except Exception as e:
        print(f"⚠️  AI Analysis failed: {e}")
        return None

def test_reporter(analysis, parsed_logs):
    """Test the terminal reporter"""
    print("📊 Testing Reporter...")
    
    console = Console()
    reporter = HealthReporter(console, verbose=True)
    
    if analysis:
        reporter.show_health_report(analysis, parsed_logs)
    else:
        print("⚠️  Skipping reporter test (no analysis data)")

def main():
    print("🚀 Fend Sentry Component Test")
    print("=" * 50)
    
    # Test 1: Log Parsing
    parsed_logs = test_log_parsing()
    
    # Test 2: AI Analysis  
    analysis = test_ai_analysis(parsed_logs)
    
    # Test 3: Reporter
    test_reporter(analysis, parsed_logs)
    
    print("\n✅ Component testing complete!")
    print("💡 Run 'python cli.py check' to test with real server")

if __name__ == "__main__":
    main()