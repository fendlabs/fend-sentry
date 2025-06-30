#!/bin/bash
# Fend Sentry Installation Test Script
# Run this on your Django server

echo "🚀 Installing Fend Sentry dependencies..."
pip install click rich paramiko google-generativeai python-dotenv pyyaml

echo "📦 Downloading Fend Sentry..."
cd /tmp
wget -O fend_sentry.tar.gz "https://github.com/fendlabs/fend-sentry/archive/refs/heads/main.tar.gz"
tar -xzf fend_sentry.tar.gz
cd fend-sentry-main

echo "✅ Ready to test!"
echo "Now run:"
echo "  export GEMINI_API_KEY='your_api_key_here'"
echo "  python cli.py init"
echo "  python cli.py check"