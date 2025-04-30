#!/bin/bash
set -e

# Setup script for Reddit Sentiment Analysis project
echo "🚀 Setting up Reddit Sentiment Analysis Project"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment with Python 3.9..."
    # Check if Python 3.9 is available
    if command -v python3.9 &> /dev/null; then
        python3.9 -m venv venv
    else
        echo "⚠️ Python 3.9 not found. Using default Python version."
        python3 -m venv venv
    fi
fi

# Activate virtual environment
source venv/bin/activate

# Install critical packages first
echo "📦 Installing critical packages..."
pip install --upgrade pip
pip install wheel setuptools
pip install sqlalchemy psycopg2-binary

# Run the database initialization script
echo "🔧 Initializing database tables..."
python scripts/init_db.py

# Start Docker services if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Starting Docker services..."
    docker-compose up -d postgres
    
    # Give PostgreSQL time to start
    echo "⏳ Waiting for PostgreSQL to start..."
    sleep 10
    
    echo "✅ PostgreSQL is now running on localhost:5432"
else
    echo "⚠️ Docker or docker-compose not found. Please start PostgreSQL manually."
fi

echo "✅ Setup complete!"
echo ""
echo "To start the complete application:"
echo "  docker-compose up -d"
echo ""
echo "To run the backend locally:"
echo "  cd backend"
echo "  export DATABASE_URL=\"postgresql+psycopg2://reddit_user:reddit_pass@localhost:5432/reddit_db\""
echo "  uvicorn app.main:app --reload"