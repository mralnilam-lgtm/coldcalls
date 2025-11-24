#!/bin/bash
# Setup script for Cold Calls Twilio

echo "=================================="
echo "Cold Calls Setup"
echo "=================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Please run: sudo apt install python3-venv -y"
        exit 1
    fi
fi

# Activate venv and install dependencies
echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "To run the script:"
    echo "  source venv/bin/activate"
    echo "  python cold_calls.py"
    echo ""
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
