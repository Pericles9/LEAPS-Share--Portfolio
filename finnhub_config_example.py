# Finnhub API Configuration Example
# 
# To use Finnhub ETF Holdings API, you need a premium API key
# Get your API key from: https://finnhub.io/dashboard

# Option 1: Environment Variable (Recommended)
# Set this in your system environment or in your shell profile:
# export FINNHUB_API_KEY="your_actual_api_key_here"

# Option 2: Direct initialization in code
# manager = ETFHoldingsManager(finnhub_api_key="your_actual_api_key_here")

# API Key Features:
# - Premium access required for ETF holdings endpoint
# - 30 API calls per second rate limit
# - Comprehensive global ETF coverage
# - Real-time holdings data with precise percentages
# - Security details (CUSIP, ISIN, asset types)

# Endpoint Documentation:
# https://finnhub.io/docs/api/etfs-holdings

# Example Response Format:
# {
#   "atDate": "2023-03-24",
#   "holdings": [
#     {
#       "assetType": "Equity",
#       "cusip": "88160R101",
#       "isin": "US88160R1014", 
#       "name": "TESLA INC",
#       "percent": 10.54,
#       "share": 3971395,
#       "symbol": "TSLA",
#       "value": 763381546.9
#     }
#   ],
#   "numberOfHoldings": 28,
#   "symbol": "ARKK"
# }