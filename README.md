# Sneaker Data Scraper

A comprehensive web scraper for collecting sneaker data including images, current values, purchase prices, and historical sold prices from various sneaker marketplaces.

## Features

- Multi-platform scraping (StockX, GOAT, eBay, etc.)
- Image collection and processing
- Price tracking and historical data
- Google Drive integration for data storage
- RESTful API for data access
- Automated data updates

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

3. Set up Google Drive API:
   - Create a Google Cloud project
   - Enable Google Drive API
   - Download credentials.json
   - Place in the project root

4. Run the scraper:
```bash
python main.py
```

## API Endpoints

- `GET /api/sneakers` - Get all sneakers
- `GET /api/sneakers/{id}` - Get specific sneaker
- `GET /api/search?q={query}` - Search sneakers
- `POST /api/scrape` - Trigger manual scrape

## Data Structure

Each sneaker entry contains:
- Name and model
- Brand
- Images (multiple angles)
- Current market value
- Retail price
- Historical sold prices
- Size availability
- Condition ratings