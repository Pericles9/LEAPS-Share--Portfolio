# Configuration settings for the portfolio system

# API Settings
ALPHA_VANTAGE_API_KEY = "your_api_key_here"
QUANDL_API_KEY = "your_api_key_here"

# Default Parameters
DEFAULT_RISK_FREE_RATE = 0.02
DEFAULT_CONFIDENCE_LEVEL = 0.05
DEFAULT_TRADING_DAYS_PER_YEAR = 252

# Portfolio Optimization Settings
DEFAULT_MIN_WEIGHT = 0.0
DEFAULT_MAX_WEIGHT = 1.0
DEFAULT_REBALANCE_THRESHOLD = 0.05

# Black-Scholes Model Settings
DEFAULT_OPTION_TYPE = "call"
MAX_ITERATIONS_IV = 100
TOLERANCE_IV = 1e-6

# Data Fetching Settings
DEFAULT_PERIOD = "1y"
DEFAULT_INTERVAL = "1d"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Monte Carlo Simulation Settings
DEFAULT_NUM_SIMULATIONS = 1000
DEFAULT_TIME_HORIZON = 252