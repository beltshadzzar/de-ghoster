#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease create a .env file or set these variables before running.")
        print("See .env.example for reference.")
        return False
    
    print("✅ Environment variables check passed")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import streamlit
        import langchain
        import openai
        import selenium
        import beautifulsoup4
        print("✅ Dependencies check passed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created")

def main():
    print("🎯 LinkedIn Job Analyzer")
    print("=" * 50)
    
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    print("🚀 Starting Streamlit application...")
    print("📱 The app will open in your browser automatically")
    print("🔗 URL: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the application")
    print("=" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "main.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()