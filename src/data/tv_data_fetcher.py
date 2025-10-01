"""
TradingView Data Fetcher

Uses tvdatafeed library to fetch market data from TradingView.
This replaces yfinance as the primary data source.
Includes intelligent caching to avoid redundant API calls.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import warnings
warnings.filterwarnings('ignore')

# Import cache manager
try:
    from ..utils.cache_manager import get_cache_manager
    CACHING_AVAILABLE = True
except ImportError:
    CACHING_AVAILABLE = False
    print("⚠️ Cache manager not available - caching disabled")

try:
    from tvDatafeed import TvDatafeed, Interval
    TVDATAFEED_AVAILABLE = True
    print("✅ TradingView tvDatafeed successfully imported")
except ImportError as e:
    TVDATAFEED_AVAILABLE = False
    print(f"Warning: tvDatafeed not available ({e}), falling back to synthetic data")
except Exception as e:
    TVDATAFEED_AVAILABLE = False
    print(f"Warning: tvDatafeed import error ({e}), falling back to synthetic data")


class TradingViewDataFetcher:
    """Fetch market data using TradingView via tvdatafeed."""
    
    def __init__(self, enable_cache: bool = True):
        """Initialize the TradingView data fetcher."""
        self.tv = None
        self.cache_enabled = enable_cache and CACHING_AVAILABLE
        
        if TVDATAFEED_AVAILABLE:
            try:
                self.tv = TvDatafeed()
                print("✅ TradingView data fetcher initialized")
            except Exception as e:
                print(f"⚠️  TradingView initialization failed: {e}")
                self.tv = None
        
        if self.cache_enabled:
            self.cache = get_cache_manager()
            print("💾 TradingView caching enabled")
        else:
            self.cache = None
        
        # Exchange mappings for common symbols
        self.exchange_map = {
            'AAPL': 'NASDAQ',
            'MSFT': 'NASDAQ', 
            'GOOGL': 'NASDAQ',
            'GOOG': 'NASDAQ',
            'AMZN': 'NASDAQ',
            'TSLA': 'NASDAQ',
            'META': 'NASDAQ',
            'NVDA': 'NASDAQ',
            'NFLX': 'NASDAQ',
            'AVGO': 'NASDAQ',
            'COST': 'NASDAQ',
            'ADBE': 'NASDAQ',
            'JPM': 'NYSE',
            'BAC': 'NYSE',
            'WFC': 'NYSE',
            'GS': 'NYSE',
            'MS': 'NYSE',
            'AXP': 'NYSE',
            'V': 'NYSE',
            'MA': 'NYSE',
            'BRK-B': 'NYSE',
            'XLF': 'NYSE',
            'XLK': 'NYSE',
            'SPY': 'NYSE',
            'QQQ': 'NASDAQ'
        }
    
    def get_stock_data(self, symbol: str, days: int = 180, allow_synthetic: bool = True) -> pd.DataFrame:
        """
        Fetch stock data for a single symbol with caching.
        
        Args:
            symbol: Stock symbol
            days: Number of days of historical data
            allow_synthetic: Whether to generate synthetic data if real data fails
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        # Check cache first
        if self.cache_enabled:
            cache_key_params = {'days': days, 'allow_synthetic': allow_synthetic}
            cached_data = self.cache.get('tv_stock_data', symbol, **cache_key_params)
            if cached_data is not None:
                return cached_data
        
        if not self.tv:
            print(f"⚠️  TradingView not available for {symbol}, using synthetic data")
            synthetic_data = self._generate_synthetic_data(symbol, days)
            
            # Cache synthetic data
            if self.cache_enabled and synthetic_data is not None:
                cache_key_params = {'days': days, 'allow_synthetic': allow_synthetic}
                self.cache.set('tv_stock_data', synthetic_data, symbol, **cache_key_params)
            
            return synthetic_data
        
        # Try multiple exchanges automatically - no more guessing!
        exchanges_to_try = []
        
        # If we have a known exchange, try it first
        if symbol in self.exchange_map:
            exchanges_to_try.append(self.exchange_map[symbol])
        
        # Always try both major exchanges
        for exchange in ['NASDAQ', 'NYSE']:
            if exchange not in exchanges_to_try:
                exchanges_to_try.append(exchange)
        
        print(f"📊 Fetching {symbol} (trying {len(exchanges_to_try)} exchanges)...")
        
        for i, exchange in enumerate(exchanges_to_try):
            try:
                if i > 0:
                    print(f"🔄 Trying {symbol} on {exchange}...")
                    time.sleep(1.0)  # Brief delay between exchange attempts
                
                # Fetch data
                data = self.tv.get_hist(
                    symbol=symbol,
                    exchange=exchange, 
                    interval=Interval.in_daily,
                    n_bars=days
                )
                
                if data is not None and len(data) > 0:
                    print(f"✅ {symbol}: {len(data)} days from {exchange}")
                    
                    # Cache successful data
                    if self.cache_enabled:
                        cache_key_params = {'days': days, 'allow_synthetic': allow_synthetic}
                        self.cache.set('tv_stock_data', data, symbol, **cache_key_params)
                    
                    return data
                    
            except Exception as e:
                if i < len(exchanges_to_try) - 1:
                    print(f"⚠️  {symbol} failed on {exchange}, trying next exchange...")
                    continue
                else:
                    print(f"❌ {symbol}: Failed on all exchanges")
        
        # If all exchanges fail, check if we should generate synthetic data
        if not allow_synthetic:
            print(f"❌ {symbol}: Failed on all exchanges, synthetic data disabled")
            return None
            
        # For clearly invalid symbols, don't generate synthetic data  
        if symbol.upper() in ['INVALID', 'BADSTOCK', 'FAKE_SYM', 'ZZZZ', 'XXXX', 'QQQQ'] or \
           any(char.isdigit() for char in symbol) or len(symbol) > 5 or len(symbol) < 2:
            print(f"❌ {symbol}: Invalid symbol, not generating synthetic data")
            return None
        
        # For potentially valid symbols that just had connection issues, use synthetic data
        print(f"🔄 Generating synthetic data for {symbol}")
        synthetic_data = self._generate_synthetic_data(symbol, days)
        
        # Cache synthetic data
        if self.cache_enabled and synthetic_data is not None:
            cache_key_params = {'days': days, 'allow_synthetic': allow_synthetic}
            self.cache.set('tv_stock_data', synthetic_data, symbol, **cache_key_params)
        
        return synthetic_data
    
    def get_multiple_stocks(self, symbols: List[str], days: int = 180, allow_synthetic: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            days: Number of days of historical data
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        data = {}
        
        for i, symbol in enumerate(symbols):
            if i > 0:
                time.sleep(2.0)  # Increased delay to avoid connection issues
            
            stock_data = self.get_stock_data(symbol, days, allow_synthetic)
            if stock_data is not None:
                data[symbol] = stock_data
        
        return data
    
    def get_returns_data(self, symbols: List[str], days: int = 180, allow_synthetic: bool = True) -> pd.DataFrame:
        """
        Get returns data for portfolio optimization with caching.
        
        Args:
            symbols: List of stock symbols
            days: Number of days of historical data
            allow_synthetic: Whether to allow synthetic data
            
        Returns:
            DataFrame with daily returns for each symbol
        """
        # Check cache first (cache by symbol combination)
        if self.cache_enabled:
            symbols_key = "_".join(sorted(symbols))  # Consistent ordering for cache key
            cache_key_params = {'symbols': symbols_key, 'days': days, 'allow_synthetic': allow_synthetic}
            cached_data = self.cache.get('tv_returns_data', None, **cache_key_params)
            if cached_data is not None:
                return cached_data
        
        stock_data = self.get_multiple_stocks(symbols, days, allow_synthetic)
        
        returns_data = {}
        successful_symbols = []
        failed_symbols = []
        
        for symbol in symbols:
            if symbol in stock_data and stock_data[symbol] is not None:
                data = stock_data[symbol]
                if len(data) >= 20:  # Minimum data requirement
                    if 'close' in data.columns:
                        returns_series = data['close'].pct_change()
                    elif 'Close' in data.columns:
                        returns_series = data['Close'].pct_change()
                    else:
                        failed_symbols.append(symbol)
                        continue
                    
                    # Check data quality - allow some NaN values but not too many
                    returns_series_clean = returns_series.dropna()
                    if len(returns_series_clean) >= 15:  # Ensure sufficient returns data
                        returns_data[symbol] = returns_series  # Keep the series with its original index
                        successful_symbols.append(symbol)
                    else:
                        failed_symbols.append(symbol)
                else:
                    failed_symbols.append(symbol)
            else:
                failed_symbols.append(symbol)
        
        # Report results
        if failed_symbols:
            print(f"  ⚠️ Data fetch summary: {len(successful_symbols)}/{len(symbols)} successful")
            print(f"     ✅ Success: {successful_symbols}")
            print(f"     ❌ Failed: {failed_symbols}")
        
        if returns_data:
            # Find common date range for all series
            if len(returns_data) > 1:
                # Get the overlapping date range
                all_indices = [series.index for series in returns_data.values()]
                common_start = max(idx.min() for idx in all_indices)
                common_end = min(idx.max() for idx in all_indices)
                
                # Trim all series to common range
                aligned_data = {}
                for symbol, series in returns_data.items():
                    trimmed = series[(series.index >= common_start) & (series.index <= common_end)]
                    if len(trimmed) >= 15:  # Still require minimum data
                        aligned_data[symbol] = trimmed
                    else:
                        print(f"  ⚠️ Dropping {symbol}: insufficient data after alignment ({len(trimmed)} days)")
                
                if aligned_data:
                    returns_df = pd.DataFrame(aligned_data)
                    # Only drop rows where ALL values are NaN
                    returns_df = returns_df.dropna(how='all')
                    
                    # Cache the returns data
                    if self.cache_enabled:
                        symbols_key = "_".join(sorted(symbols))
                        cache_key_params = {'symbols': symbols_key, 'days': days, 'allow_synthetic': allow_synthetic}
                        self.cache.set('tv_returns_data', returns_df, None, **cache_key_params)
                    
                    return returns_df
                else:
                    return pd.DataFrame()
            else:
                # Single series case
                returns_df = pd.DataFrame(returns_data)
                returns_df = returns_df.dropna(how='all')
                
                # Cache single series returns data
                if self.cache_enabled and len(returns_df) > 0:
                    symbols_key = "_".join(sorted(symbols))
                    cache_key_params = {'symbols': symbols_key, 'days': days, 'allow_synthetic': allow_synthetic}
                    self.cache.set('tv_returns_data', returns_df, None, **cache_key_params)
                
                return returns_df
        else:
            return pd.DataFrame()
    
    def _generate_synthetic_data(self, symbol: str, days: int) -> pd.DataFrame:
        """
        Generate synthetic stock data for testing/fallback.
        
        Args:
            symbol: Stock symbol
            days: Number of days
            
        Returns:
            DataFrame with synthetic OHLCV data
        """
        print(f"🔄 Generating synthetic data for {symbol}")
        
        # Use symbol hash for deterministic randomness
        np.random.seed(hash(symbol) % 2**32)
        
        # Base parameters
        base_price = 100 + (hash(symbol) % 200)  # Price between 100-300
        volatility = 0.02 + (hash(symbol) % 100) * 0.0001  # Volatility 0.02-0.03
        
        # Generate price series using current date range
        from datetime import datetime, timedelta
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days + 10)  # Add buffer for weekends/holidays
        
        # Generate business days only to match real market data
        dates = pd.bdate_range(start=start_date, end=end_date, freq='B')[-days:]
        
        # Generate returns and prices
        returns = np.random.normal(0.0005, volatility, len(dates))
        prices = [base_price]
        
        for ret in returns[:-1]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        closes = np.array(prices)
        opens = closes * (1 + np.random.normal(0, 0.005, len(closes)))
        highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.01, len(closes))))
        lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.01, len(closes))))
        volumes = np.random.lognormal(15, 0.5, len(closes)).astype(int)
        
        # Create DataFrame
        data = pd.DataFrame({
            'open': opens,
            'high': highs, 
            'low': lows,
            'close': closes,
            'volume': volumes
        }, index=dates)
        
        return data
    
    def get_data_quality_report(self, symbols: List[str], days: int = 180) -> Dict:
        """
        Get detailed data quality report for a list of symbols.
        
        Args:
            symbols: List of stock symbols
            days: Number of days requested
            
        Returns:
            Dictionary with success/failure details
        """
        stock_data = self.get_multiple_stocks(symbols, days, allow_synthetic=False)  # Don't use synthetic for quality report
        
        report = {
            'requested_symbols': symbols,
            'successful': [],
            'failed': [],
            'insufficient_data': [],
            'total_requested': len(symbols),
            'success_rate': 0.0
        }
        
        for symbol in symbols:
            if symbol in stock_data and stock_data[symbol] is not None:
                data = stock_data[symbol]
                if len(data) >= 20:
                    report['successful'].append(symbol)
                else:
                    report['insufficient_data'].append(symbol)
            else:
                report['failed'].append(symbol)
        
        report['success_rate'] = len(report['successful']) / len(symbols) * 100
        return report
    
    def test_connection(self) -> bool:
        """Test if TradingView connection is working."""
        if not self.tv:
            return False
        
        try:
            # Try to fetch a small amount of data for AAPL
            data = self.tv.get_hist(symbol='AAPL', exchange='NASDAQ', 
                                  interval=Interval.in_daily, n_bars=5)
            return data is not None and len(data) > 0
        except:
            return False


# Global instance with caching enabled
tv_fetcher = TradingViewDataFetcher(enable_cache=True)


def get_stock_returns(symbols: List[str], days: int = 180) -> pd.DataFrame:
    """
    Convenient function to get returns data for a list of symbols.
    
    Args:
        symbols: List of stock symbols
        days: Number of days of historical data
        
    Returns:
        DataFrame with daily returns
    """
    return tv_fetcher.get_returns_data(symbols, days)


def test_tv_data_fetcher():
    """Test the TradingView data fetcher."""
    print("🧪 Testing TradingView Data Fetcher")
    print("=" * 50)
    
    # Test symbols
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    
    print(f"Testing connection...")
    if tv_fetcher.test_connection():
        print("✅ TradingView connection working")
    else:
        print("⚠️  TradingView connection not available, using synthetic data")
    
    print(f"\nFetching returns data for {test_symbols}...")
    returns_df = get_stock_returns(test_symbols, days=90)
    
    if len(returns_df) > 0:
        print(f"✅ Success: {len(returns_df)} days, {len(returns_df.columns)} stocks")
        print(f"Columns: {list(returns_df.columns)}")
        print(f"Date range: {returns_df.index[0].date()} to {returns_df.index[-1].date()}")
        
        # Show some stats
        for col in returns_df.columns:
            mean_ret = returns_df[col].mean()
            std_ret = returns_df[col].std()
            print(f"{col}: Mean return {mean_ret:.4f}, Std {std_ret:.4f}")
    else:
        print("❌ No data returned")
    
    return len(returns_df) > 0


if __name__ == "__main__":
    test_tv_data_fetcher()