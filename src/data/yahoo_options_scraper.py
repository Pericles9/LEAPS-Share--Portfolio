#!/usr/bin/env python3
"""
Yahoo Options Scraper - Python implementation
Based on MichaelKono/Yahoo-Scraper C# library
Scrapes Yahoo Finance API for options chain data with caching
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Option:
    """Individual option contract data."""
    contract_symbol: str
    strike: float
    bid: float
    ask: float
    last_price: float
    change: float
    percent_change: float
    last_trade_date: int
    volume: int
    open_interest: int
    implied_volatility: float
    contract_size: str
    expiration: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Option':
        """Create Option from Yahoo API response dictionary."""
        return cls(
            contract_symbol=data.get('contractSymbol', ''),
            strike=float(data.get('strike', 0)),
            bid=float(data.get('bid', 0)),
            ask=float(data.get('ask', 0)),
            last_price=float(data.get('lastPrice', 0)),
            change=float(data.get('change', 0)),
            percent_change=float(data.get('percentChange', 0)),
            last_trade_date=int(data.get('lastTradeDate', 0)),
            volume=int(data.get('volume', 0)),
            open_interest=int(data.get('openInterest', 0)),
            implied_volatility=float(data.get('impliedVolatility', 0)),
            contract_size=data.get('contractSize', 'REGULAR'),
            expiration=int(data.get('expiration', 0))
        )


@dataclass
class OptionChain:
    """Options chain for a specific expiration date."""
    expiration_date: int
    calls: List[Option]
    puts: List[Option]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptionChain':
        """Create OptionChain from Yahoo API response dictionary."""
        calls = [Option.from_dict(call) for call in data.get('calls', [])]
        puts = [Option.from_dict(put) for put in data.get('puts', [])]
        
        return cls(
            expiration_date=int(data.get('expirationDate', 0)),
            calls=calls,
            puts=puts
        )


@dataclass
class UnderlyingQuote:
    """Underlying stock quote data."""
    symbol: str
    currency: str
    regular_market_time: int
    regular_market_previous_close: float
    regular_market_price: float
    regular_market_day_high: float
    regular_market_day_low: float
    regular_market_change: float
    regular_market_change_percent: float
    regular_market_volume: int
    market_state: str
    dividend_date: int = 0
    earnings_timestamp: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnderlyingQuote':
        """Create UnderlyingQuote from Yahoo API response dictionary."""
        return cls(
            symbol=data.get('symbol', ''),
            currency=data.get('currency', 'USD'),
            regular_market_time=int(data.get('regularMarketTime', 0)),
            regular_market_previous_close=float(data.get('regularMarketPreviousClose', 0)),
            regular_market_price=float(data.get('regularMarketPrice', 0)),
            regular_market_day_high=float(data.get('regularMarketDayHigh', 0)),
            regular_market_day_low=float(data.get('regularMarketDayLow', 0)),
            regular_market_change=float(data.get('regularMarketChange', 0)),
            regular_market_change_percent=float(data.get('regularMarketChangePercent', 0)),
            regular_market_volume=int(data.get('regularMarketVolume', 0)),
            market_state=data.get('marketState', 'REGULAR'),
            dividend_date=int(data.get('dividendDate', 0)),
            earnings_timestamp=int(data.get('earningsTimestamp', 0))
        )


@dataclass
class OptionChainCollection:
    """Complete options chain collection for a symbol."""
    underlying_symbol: str
    quote: UnderlyingQuote
    expiration_dates: List[int]
    strikes: List[float]
    options: List[OptionChain]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptionChainCollection':
        """Create OptionChainCollection from Yahoo API response dictionary."""
        quote_data = data.get('quote', {})
        quote = UnderlyingQuote.from_dict(quote_data)
        
        expiration_dates = [int(date) for date in data.get('expirationDates', [])]
        strikes = [float(strike) for strike in data.get('strikes', [])]
        
        options = []
        for option_data in data.get('options', []):
            options.append(OptionChain.from_dict(option_data))
        
        return cls(
            underlying_symbol=data.get('underlyingSymbol', ''),
            quote=quote,
            expiration_dates=expiration_dates,
            strikes=strikes,
            options=options
        )


class YahooOptionsScraper:
    """Yahoo Finance options scraper with caching functionality."""
    
    # Yahoo Finance API endpoint
    YAHOO_API_BASE = "https://query2.finance.yahoo.com/v7/finance/options/"
    
    def __init__(self, cache_location: str = "cache", cache_expiration_minutes: int = 60):
        """
        Initialize the Yahoo Options Scraper.
        
        Args:
            cache_location: Directory to store cached responses
            cache_expiration_minutes: How long cached data is valid
        """
        self.cache_location = Path(cache_location)
        self.cache_expiration = timedelta(minutes=cache_expiration_minutes)
        
        # Create cache directory if it doesn't exist
        self.cache_location.mkdir(exist_ok=True)
        
        # Initialize session first
        self._init_session()
        
    def _init_session(self):
        """Initialize session with proper headers and get any required tokens."""
        # Set up session with headers to mimic browser
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Referer': 'https://finance.yahoo.com/',
            'Origin': 'https://finance.yahoo.com'
        })
        
        # Try to get a session cookie by visiting Yahoo Finance first
        try:
            response = self.session.get('https://finance.yahoo.com/', timeout=10)
            print("   Initialized session with Yahoo Finance")
        except Exception as e:
            print(f"   Warning: Could not initialize session: {e}")
    
    def _try_get_from_cache(self, filename: str) -> Optional[str]:
        """
        Try to get data from cache if it's still valid.
        
        Args:
            filename: Cache file name
            
        Returns:
            Cached data string if valid, None otherwise
        """
        cache_path = self.cache_location / filename
        
        if not cache_path.exists():
            return None
        
        # Check if cache is still valid
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_time < self.cache_expiration:
            try:
                return cache_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Warning: Failed to read cache file {filename}: {e}")
                return None
        
        return None
    
    def _save_to_cache(self, filename: str, data: str) -> None:
        """
        Save data to cache file.
        
        Args:
            filename: Cache file name
            data: Data to save
        """
        cache_path = self.cache_location / filename
        
        # Create subdirectory if needed
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            cache_path.write_text(data, encoding='utf-8')
        except Exception as e:
            print(f"Warning: Failed to save cache file {filename}: {e}")
    
    def _http_get(self, symbol: str, expiration_date: int = 0) -> Optional[str]:
        """
        Make HTTP request to Yahoo Finance API.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            expiration_date: Optional expiration date timestamp
            
        Returns:
            JSON response string or None if failed
        """
        # Build URL
        url = f"{self.YAHOO_API_BASE}{symbol}"
        
        # Build cache filename
        if expiration_date > 0:
            url += f"?date={expiration_date}"
            filename = f"{symbol}/{symbol}-{expiration_date}.json"
        else:
            filename = f"{symbol}/{symbol}.json"
        
        # Try to get from cache first
        cached_data = self._try_get_from_cache(filename)
        if cached_data:
            print(f"   Using cached data for {symbol}" + (f" exp {expiration_date}" if expiration_date else ""))
            return cached_data
        
        # Make HTTP request
        try:
            print(f"   Fetching from Yahoo API: {symbol}" + (f" exp {expiration_date}" if expiration_date else ""))
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.text
            
            # Save to cache
            self._save_to_cache(filename, data)
            
            return data
            
        except requests.RequestException as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching data for {symbol}: {e}")
            return None
    
    def get_option_chain_collection(self, symbol: str) -> Optional[OptionChainCollection]:
        """
        Get complete options chain collection for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            OptionChainCollection or None if failed
        """
        try:
            print(f"Fetching options chain for {symbol}...")
            
            # First, get the basic options info to get expiration dates
            json_string = self._http_get(symbol)
            if not json_string:
                return None
            
            # Parse initial response
            try:
                response_data = json.loads(json_string)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response for {symbol}: {e}")
                return None
            
            # Extract the option chain result
            option_chain = response_data.get('optionChain', {})
            results = option_chain.get('result', [])
            
            if not results:
                print(f"No options data found for {symbol}")
                return None
            
            result = results[0]
            
            # Create the collection with basic data
            collection = OptionChainCollection.from_dict(result)
            
            # Clear the options array - we'll populate it with detailed data
            collection.options = []
            
            # Now fetch detailed data for each expiration date
            print(f"   Found {len(collection.expiration_dates)} expiration dates for {symbol}")
            
            for expiration_date in collection.expiration_dates:
                # Get options for this expiration
                exp_json_string = self._http_get(symbol, expiration_date)
                if exp_json_string:
                    try:
                        exp_response_data = json.loads(exp_json_string)
                        exp_option_chain = exp_response_data.get('optionChain', {})
                        exp_results = exp_option_chain.get('result', [])
                        
                        if exp_results and exp_results[0].get('options'):
                            for option_data in exp_results[0]['options']:
                                collection.options.append(OptionChain.from_dict(option_data))
                        
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON for {symbol} expiration {expiration_date}: {e}")
                        continue
                else:
                    print(f"Failed to get data for {symbol} expiration {expiration_date}")
            
            print(f"SUCCESS: Retrieved {len(collection.options)} option chains for {symbol}")
            return collection
            
        except Exception as e:
            print(f"Error getting option chain collection for {symbol}: {e}")
            return None
    
    def get_filtered_options(self, symbol: str, min_volume: int = 0, min_open_interest: int = 0, 
                           option_type: str = 'both') -> List[Option]:
        """
        Get filtered options based on criteria.
        
        Args:
            symbol: Stock symbol
            min_volume: Minimum volume filter
            min_open_interest: Minimum open interest filter  
            option_type: 'calls', 'puts', or 'both'
            
        Returns:
            List of filtered Option objects
        """
        collection = self.get_option_chain_collection(symbol)
        if not collection:
            return []
        
        results = []
        
        for option_chain in collection.options:
            # Process calls
            if option_type in ['calls', 'both']:
                for call in option_chain.calls:
                    if (call.volume >= min_volume and 
                        call.open_interest >= min_open_interest):
                        results.append(call)
            
            # Process puts  
            if option_type in ['puts', 'both']:
                for put in option_chain.puts:
                    if (put.volume >= min_volume and 
                        put.open_interest >= min_open_interest):
                        results.append(put)
        
        return results


# Test the scraper
if __name__ == "__main__":
    # Initialize scraper with 60-minute cache
    scraper = YahooOptionsScraper(cache_location="yahoo_cache", cache_expiration_minutes=60)
    
    # Test with AAPL
    test_symbol = "AAPL"
    print(f"Testing Yahoo Options Scraper with {test_symbol}")
    print("=" * 60)
    
    # Get complete options chain
    collection = scraper.get_option_chain_collection(test_symbol)
    
    if collection:
        print(f"\nOptions Chain Summary for {collection.underlying_symbol}:")
        print(f"  Current Price: ${collection.quote.regular_market_price:.2f}")
        print(f"  Market State: {collection.quote.market_state}")
        print(f"  Volume: {collection.quote.regular_market_volume:,}")
        print(f"  Change: {collection.quote.regular_market_change:.2f} ({collection.quote.regular_market_change_percent:.2f}%)")
        print(f"  Total Option Chains: {len(collection.options)}")
        print(f"  Expiration Dates: {len(collection.expiration_dates)}")
        
        # Show some sample options
        if collection.options:
            first_chain = collection.options[0]
            print(f"\nSample from first expiration (total calls: {len(first_chain.calls)}, puts: {len(first_chain.puts)}):")
            
            # Show first few calls
            for i, call in enumerate(first_chain.calls[:3]):
                print(f"  Call {call.strike}: bid={call.bid}, ask={call.ask}, vol={call.volume}, OI={call.open_interest}")
            
            # Show first few puts
            for i, put in enumerate(first_chain.puts[:3]):
                print(f"  Put {put.strike}: bid={put.bid}, ask={put.ask}, vol={put.volume}, OI={put.open_interest}")
        
        # Test filtering
        print(f"\nTesting filtering (min volume 1000)...")
        high_volume_options = scraper.get_filtered_options(test_symbol, min_volume=1000)
        print(f"Found {len(high_volume_options)} options with volume >= 1000")
        
    else:
        print(f"Failed to get options data for {test_symbol}")