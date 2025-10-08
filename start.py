#!/usr/bin/env python3
"""
Startup script for Telegram File-to-Link Bot
Handles environment loading and graceful startup
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env file loading")

from bot_main import main

if __name__ == "__main__":
    print("🚀 Starting Telegram File-to-Link Bot...")
    print("📁 Project directory:", Path(__file__).parent.absolute())
    print("🐍 Python version:", sys.version)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot shutdown completed gracefully")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
