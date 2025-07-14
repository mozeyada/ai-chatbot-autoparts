#!/bin/bash
# Auto Parts Chatbot Startup Script

echo "Starting Auto Parts Chatbot..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and add your Groq API key"
    echo "Run: cp .env.example .env"
    echo "Get your free API key at: https://console.groq.com/keys"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    venv/bin/pip install -r requirements.txt
fi

# Start the chatbot
echo "Starting chatbot..."
echo "Access at: http://localhost:7860"
venv/bin/python chatbot.py