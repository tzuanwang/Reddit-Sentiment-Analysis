# Reddit Sentiment Analysis

[![Python 3.9](https://img.shields.io/badge/Python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.2-009688.svg)](https://fastapi.tiangolo.com/)
[![Airflow](https://img.shields.io/badge/Airflow-2.5.1-017CEE.svg)](https://airflow.apache.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Latest-FF4B4B.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive system for harvesting and analyzing sentiment data from Reddit posts and comments, with a focus on cryptocurrency subreddits.

![Dashboard Preview](https://img.shields.io/badge/Dashboard-Preview-brightgreen.svg)

## 🚀 Features

- 📊 **Multi-dimensional Sentiment Analysis**: Analyze posts and comments for sentiment and emotion detection
- 🤖 **Advanced NLP Processing**: Utilizes RoBERTa, NLTK, spaCy and other NLP techniques
- 📈 **Interactive Dashboard**: Real-time visualization of sentiment trends and statistics
- ⏱️ **Automated Data Collection**: Scheduled harvesting of Reddit data with Apache Airflow
- 🐳 **Containerized Architecture**: Easy deployment with Docker Compose
- ☁️ **Kubernetes Ready**: Scalable deployment to Kubernetes clusters with included manifests

## 📋 System Architecture

The project consists of four main components:

1. **Backend API** (FastAPI): Handles data harvesting, analysis, and provides a REST API
2. **Frontend Dashboard** (Streamlit): User interface for visualizing and exploring sentiment data
3. **Database** (PostgreSQL): Stores posts, comments, and sentiment analysis results
4. **Airflow** (optional): Manages scheduled tasks for data collection and analysis

## 🛠️ Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- PostgreSQL (for local development)

### Quick Setup

```bash

# Run the setup script
./scripts/setup_enhanced_system.sh
```

This will:
- Install dependencies
- Set up the database
- Build and start Docker containers
- Harvest initial Reddit data
- Perform initial sentiment analysis

### Manual Setup

```bash
# Start the services
docker-compose up -d

# Harvest data from a subreddit
curl -X POST "http://localhost:5001/harvest/CryptoCurrency?limit=20"

# Initialize sentiment analysis
python scripts/init_sentiment.py
```

## 🖥️ Accessing the System

- **Frontend Dashboard**: http://localhost:8501
- **Backend API**: http://localhost:5001
- **API Documentation**: http://localhost:5001/docs
- **Airflow UI** (if enabled): http://localhost:8080 (user: admin, pass: admin)

## 📊 Data Analysis Features

- **Sentiment Analysis**: Classifies content as positive, negative, or neutral
- **Emotion Detection**: Identifies joy, sadness, anger, fear, surprise, and other emotions
- **Trend Analysis**: Track sentiment changes over time
- **Example Extraction**: Find representative posts for each sentiment category

## 🔧 API Endpoints

The REST API provides the following key endpoints:

- `POST /harvest/{subreddit}`: Collect new posts and comments
- `GET /posts`: List posts with optional filtering
- `GET /stats/sentiment`: Get sentiment statistics over time
- `GET /trends`: Get sentiment trends over a specified period
- `POST /analyze/text`: Analyze custom text input

## 🚀 Deployment Options

### Docker Compose

For development and small-scale deployments:

```bash
docker-compose up -d
```

To include Airflow (optional):

```bash
docker-compose --profile with-airflow up -d
```

### Kubernetes

For production deployments:

```bash
# Deploy to Kubernetes cluster
./scripts/deploy.sh <GCP_PROJECT_ID> <K8S_NAMESPACE>

# Forward ports for local access
./scripts/port-forward.sh <K8S_NAMESPACE>
```

## 🧪 Running Tests

```bash
# Run backend tests
cd backend
pytest

# Run frontend tests
cd frontend
pytest
```

## 📚 Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PRAW (Reddit API), Transformers, spaCy, NLTK
- **Frontend**: Streamlit, Pandas, Altair (visualization)
- **Database**: PostgreSQL
- **Orchestration**: Apache Airflow
- **Infrastructure**: Docker, Kubernetes

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
