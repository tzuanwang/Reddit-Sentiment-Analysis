#!/usr/bin/env bash
set -euo pipefail

# Setup script for enhanced Reddit sentiment analysis system
# This script will:
# 1. Install dependencies with the optimized approach
# 2. Setup the database
# 3. Build containers
# 4. Initialize sentiment analysis

echo "🚀 Setting up Enhanced Reddit Sentiment Analysis System"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create a python virtual environment for local development
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Use the specialized installation script
    echo "📦 Installing dependencies with the optimized approach..."
    chmod +x scripts/install_dependencies.sh
    PYTHON_EXE="$(pwd)/venv/bin/python" ./scripts/install_dependencies.sh
    
    # Install additional local development requirements
    pip install tqdm
else
    echo "✅ Python virtual environment already exists."
    source venv/bin/activate
fi

# Create directories if they don't exist
mkdir -p data/postgres

# Start PostgreSQL container separately for initialization
echo "🐘 Starting PostgreSQL..."
docker run --name postgres-init \
    -e POSTGRES_USER=reddit_user \
    -e POSTGRES_PASSWORD=reddit_pass \
    -e POSTGRES_DB=reddit_db \
    -v "$(pwd)/data/postgres:/var/lib/postgresql/data" \
    -p 5432:5432 \
    --rm -d postgres:14

# Wait for PostgreSQL to start
echo "⏳ Waiting for PostgreSQL to start..."
sleep 10

# Initialize the database
echo "🔧 Creating database tables..."
export DATABASE_URL="postgresql+psycopg2://reddit_user:reddit_pass@localhost:5432/reddit_db"
python scripts/init_db.py

# Stop the PostgreSQL container
echo "🛑 Stopping PostgreSQL initialization container..."
docker stop postgres-init

# Build Docker images with --no-cache to ensure fresh builds
echo "🏗️ Building Docker images..."
docker-compose build --no-cache

# Start the Docker Compose environment
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 15

# Harvest some initial data
echo "🔍 Harvesting initial Reddit data..."
curl -X POST "http://localhost:5001/harvest/CryptoCurrency?limit=20"

# Run sentiment analysis initialization
echo "🧠 Running initial sentiment analysis..."
export DATABASE_URL="postgresql+psycopg2://reddit_user:reddit_pass@localhost:5432/reddit_db"
python scripts/init_sentiment.py

echo "✅ Setup complete! Services are running:"
echo "  - Airflow: http://localhost:8080 (user: admin, pass: admin)"
echo "  - Backend API: http://localhost:5001"
echo "  - Frontend Dashboard: http://localhost:8501"
echo ""
echo "You can now use the system to analyze Reddit sentiment."