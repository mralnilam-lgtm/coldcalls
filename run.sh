#!/bin/bash
# Run script for Cold Calls Twilio

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found"
    echo "Please run: ./setup.sh"
    exit 1
fi

# Activate venv and run script
source venv/bin/activate
python cold_calls.py
