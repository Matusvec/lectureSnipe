#!/bin/bash
# Quick start script for LectureSnipe

echo "========================================"
echo "LectureSnipe - Quick Start"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo "✓ Dependencies installed"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created (please configure with your credentials)"
    echo ""
fi

# Display menu
echo "========================================"
echo "Choose an option:"
echo "========================================"
echo ""
echo "1. Start Web Interface"
echo "2. Run Demo (with sample data)"
echo "3. Run Tests"
echo "4. Process URL via CLI (requires URL argument)"
echo "5. Exit"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "Starting web interface..."
        echo "Open your browser to: http://localhost:5000"
        echo "Press Ctrl+C to stop the server"
        echo ""
        python app.py
        ;;
    2)
        echo ""
        echo "Running demo with sample data..."
        echo ""
        python demo.py
        ;;
    3)
        echo ""
        echo "Running tests..."
        echo ""
        python test_lecturesnipe.py
        ;;
    4)
        read -p "Enter Panopto URL: " url
        if [ -z "$url" ]; then
            echo "❌ No URL provided"
            exit 1
        fi
        echo ""
        python cli.py "$url"
        ;;
    5)
        echo ""
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
