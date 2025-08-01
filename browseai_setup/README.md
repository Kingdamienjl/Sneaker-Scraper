# BrowseAI Robot Setup for Sneaker Scraping

This directory contains everything you need to set up BrowseAI robots for scraping sneaker data.

## Files Included

- `robot_setup_instructions.json` - Detailed setup instructions for each robot
- `robot_configurations.json` - Robot configuration templates
- `browseai_integration.py` - Python code for API integration
- `README.md` - This file

## Quick Start

1. **Create BrowseAI Account**
   - Go to https://browse.ai
   - Sign up for an account
   - Get your API key from the dashboard

2. **Set Up Robots**
   - Follow the instructions in `robot_setup_instructions.json`
   - Create robots for Nike, StockX, and GOAT
   - Test each robot with the provided example URLs

3. **API Integration**
   - Use the code in `browseai_integration.py`
   - Replace `your_browseai_api_key_here` with your actual API key
   - Replace robot IDs with your actual robot IDs

## Robot Types

### Nike Product Scraper
- Extracts product details from Nike.com
- Gets images, prices, descriptions, SKUs
- Best for official product data

### StockX Product Scraper  
- Extracts market data from StockX.com
- Gets current prices, last sales, market trends
- Best for resale market data

### GOAT Product Scraper
- Extracts marketplace data from GOAT.com
- Gets prices, conditions, authenticity info
- Best for authenticated sneaker data

## Cost Estimation

- BrowseAI: $49/month for 50 robots + API access
- Each robot can run multiple times per day
- Estimated cost per sneaker: $0.02-0.05

## Next Steps

1. Set up the robots following the instructions
2. Test with sample URLs
3. Integrate with your existing scraper
4. Schedule regular data collection
5. Monitor and optimize robot performance

## Support

- BrowseAI Documentation: https://docs.browse.ai
- BrowseAI Support: support@browse.ai
