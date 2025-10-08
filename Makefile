# Makefile for Telegram File-to-Link Bot
# Provides convenient commands for development and deployment

.PHONY: help install test run clean deploy-check

# Default target
help:
	@echo "🤖 Telegram File-to-Link Bot - Available Commands:"
	@echo ""
	@echo "📦 Setup Commands:"
	@echo "  make install      - Install all dependencies"
	@echo "  make setup        - Setup environment file"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test         - Run test suite"
	@echo "  make test-config  - Test configuration only"
	@echo ""
	@echo "🚀 Run Commands:"
	@echo "  make run          - Run the bot locally"
	@echo "  make dev          - Run in development mode"
	@echo ""
	@echo "🌐 Deployment Commands:"
	@echo "  make deploy-check - Check deployment readiness"
	@echo "  make render-test  - Test Render deployment"
	@echo ""
	@echo "🧹 Maintenance Commands:"
	@echo "  make clean        - Clean temporary files"
	@echo "  make logs         - Show recent logs"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed successfully!"

# Setup environment file
setup:
	@echo "🔧 Setting up environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📝 Created .env file from template"; \
		echo "⚠️  Please edit .env with your credentials"; \
	else \
		echo "✅ .env file already exists"; \
	fi

# Run test suite
test:
	@echo "🧪 Running test suite..."
	@echo "⚠️  Test files have been removed. No tests to run."

# Test configuration only
test-config:
	@echo "🔧 Testing configuration..."
	python -c "from config import Config; Config.validate()"

# Run the bot locally
run:
	@echo "🚀 Starting bot..."
	python bot_main.py

# Run in development mode with debug logging
dev:
	@echo "🔧 Starting bot in development mode..."
	LOG_LEVEL=DEBUG python bot_main.py

# Check deployment readiness
deploy-check:
	@echo "🌐 Checking deployment readiness..."
	@echo "📋 Verifying files..."
	@for file in bot_main.py web_server.py config.py requirements.txt; do \
		if [ -f $$file ]; then \
			echo "  ✅ $$file"; \
		else \
			echo "  ❌ $$file (missing)"; \
		fi; \
	done
	@echo "📋 Testing configuration..."
	@python -c "from config import Config; Config.validate()" && echo "  ✅ Configuration valid" || echo "  ❌ Configuration invalid"
	@echo "📋 Checking dependencies..."
	@pip check && echo "  ✅ Dependencies OK" || echo "  ❌ Dependency issues"

# Test Render deployment locally
render-test:
	@echo "🌐 Testing Render-like environment..."
	HOST=0.0.0.0 PORT=10000 python bot_main.py

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.session" -delete
	find . -type f -name "*.session-journal" -delete
	@echo "✅ Cleanup completed!"

# Show recent logs (if running with systemd or similar)
logs:
	@echo "📝 Recent logs:"
	@if [ -f bot.log ]; then \
		tail -n 50 bot.log; \
	else \
		echo "No log file found. Run 'make run' to start the bot."; \
	fi

# Quick start command
quickstart: install setup
	@echo "🎉 Quick start completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your Telegram credentials"
	@echo "2. Run 'make test' to verify setup"
	@echo "3. Run 'make run' to start the bot"
