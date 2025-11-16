#!/bin/bash

# Quick Start Script for Local Development
# This script helps you set up and run the bot locally

set -e

echo "🤖 Torrent to Google Drive Bot - Quick Start"
echo "============================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check for rclone
echo ""
echo "🔍 Checking for rclone..."
if ! command -v rclone &> /dev/null; then
    echo "   ⚠️  Rclone not found. Installing..."
    curl https://rclone.org/install.sh | sudo bash
else
    echo "   ✅ Rclone found: $(rclone version | head -n 1)"
fi

# Check for .env file
echo ""
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "   ⚠️  Please edit .env file with your configuration"
    echo "   Required:"
    echo "   - BOT_TOKEN (from @BotFather)"
    echo "   - RCLONE_REMOTE_NAME (from rclone config)"
    echo ""
    read -p "   Press Enter to open .env in editor..." -r
    ${EDITOR:-nano} .env
else
    echo "✅ .env file exists"
fi

# Source .env file
echo ""
echo "⚙️  Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

# Check for rclone config
echo ""
if [ ! -f "$RCLONE_CONFIG_PATH" ]; then
    echo "📁 Rclone config not found at: $RCLONE_CONFIG_PATH"

    # Check default location
    if [ -f "$HOME/.config/rclone/rclone.conf" ]; then
        echo "   Found rclone config at default location"
        read -p "   Copy to $RCLONE_CONFIG_PATH? (y/n) " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mkdir -p $(dirname "$RCLONE_CONFIG_PATH")
            cp "$HOME/.config/rclone/rclone.conf" "$RCLONE_CONFIG_PATH"
            echo "   ✅ Config copied"
        fi
    else
        echo "   ⚠️  Run 'rclone config' first to set up Google Drive"
        exit 1
    fi
else
    echo "✅ Rclone config found"
fi

# Test rclone
echo ""
echo "🧪 Testing rclone connection..."
if rclone lsd "$RCLONE_REMOTE_NAME:" --config "$RCLONE_CONFIG_PATH" > /dev/null 2>&1; then
    echo "   ✅ Rclone connected successfully"
else
    echo "   ❌ Rclone connection failed"
    echo "   Please check your rclone configuration"
    exit 1
fi

# Create download directory
echo ""
echo "📂 Creating download directory..."
mkdir -p "$DOWNLOAD_DIR"
echo "   ✅ Directory created: $DOWNLOAD_DIR"

# Validate bot token
echo ""
echo "🔑 Validating bot token..."
if [ -z "$BOT_TOKEN" ]; then
    echo "   ❌ BOT_TOKEN not set in .env"
    exit 1
else
    echo "   ✅ Bot token found"
fi

# Summary
echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Configuration Summary:"
echo "   Bot Token: ${BOT_TOKEN:0:10}..."
echo "   Rclone Remote: $RCLONE_REMOTE_NAME"
echo "   Base Directory: $RCLONE_BASE_DIR"
echo "   Download Directory: $DOWNLOAD_DIR"
echo "   Max Download Size: $(($MAX_DOWNLOAD_SIZE / 1024 / 1024)) MB"
echo "   Concurrent Downloads: $CONCURRENT_DOWNLOADS"
echo "   Index URL: ${INDEX_BASE_URL:-Not set}"
echo ""

# Ask to start bot
read -p "🚀 Start the bot now? (y/n) " -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🤖 Starting bot..."
    echo "   Press Ctrl+C to stop"
    echo ""
    python3 main.py
else
    echo "To start the bot later, run:"
    echo "   source venv/bin/activate"
    echo "   python3 main.py"
fi
