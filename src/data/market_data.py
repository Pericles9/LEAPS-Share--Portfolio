"""
Market Data Fetcher

Module for fetching and processing financial market data.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass


@dataclass
class StockData:
    """Container for stock data."""
    symbol: str
    prices: pd.DataFrame
    info: Dict
    dividends: pd.Series
    splits: pd.Series


class MarketDataFetcher:
    """Fetch and process market data from various sources."""
    
    def __init__(self):
        """Initialize the market data fetcher."""
        self.session = None
    
    def fetch_stock_data(self, symbols: Union[str, List[str]], 
                        period: str = "1y",
                        interval: str = "1d") -> Dict[str, StockData]:
        """
        Fetch stock data for given symbols.
        
        Args:
            symbols: Stock symbol(s) to fetch
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            Dictionary mapping symbols to StockData objects
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        stock_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                
                # Fetch price data
                hist = ticker.history(period=period, interval=interval)
                
                # Fetch additional info
                try:
                    info = ticker.info
                except:
                    info = {}
                    
                try:
                    dividends = ticker.dividends
                except:
                    dividends = pd.Series(dtype=float)
                    
                try:
                    splits = ticker.splits  
                except:
                    splits = pd.Series(dtype=float)
                
                stock_data[symbol] = StockData(
                    symbol=symbol,
                    prices=hist,
                    info=info,
                    dividends=dividends,
                    splits=splits
                )
                
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                continue
        
        return stock_data
    
    def calculate_returns(self, prices: pd.DataFrame, 
                         method: str = "simple") -> pd.DataFrame:
        """
        Calculate returns from price data.
        
        Args:
            prices: Price data DataFrame
            method: 'simple' or 'log' returns
            
        Returns:
            Returns DataFrame
        """
        if method == "simple":
            returns = prices.pct_change().dropna()
        elif method == "log":
            returns = np.log(prices / prices.shift(1)).dropna()
        else:
            raise ValueError("method must be 'simple' or 'log'")
        
        return returns
    
    def get_risk_free_rate(self, duration: str = "3m") -> float:
        """
        Get risk-free rate from Treasury securities.
        
        Args:
            duration: Duration of Treasury security (3m, 6m, 1y, 2y, 5y, 10y, 30y)
            
        Returns:
            Risk-free rate as decimal
        """
        treasury_symbols = {
            "3m": "^IRX",
            "6m": "^IRX",  # Using 3-month as proxy
            "1y": "^TNX",
            "2y": "^TNX",  # Using 10-year as proxy
            "5y": "^TNX",  # Using 10-year as proxy
            "10y": "^TNX",
            "30y": "^TYX"
        }
        
        symbol = treasury_symbols.get(duration, "^TNX")
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            latest_rate = hist['Close'].iloc[-1] / 100  # Convert percentage to decimal
            return latest_rate
        except Exception:
            # Return default rate if fetch fails
            return 0.02
    
    def fetch_options_chain(self, symbol: str, expiration_date: Optional[str] = None) -> Dict:
        """
        Fetch complete options chain for a given symbol.
        
        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date (YYYY-MM-DD format), if None gets all available
            
        Returns:
            Dictionary containing options chain data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get expiration dates
            expiration_dates = ticker.options
            
            if not expiration_dates:
                return {'error': f'No options available for {symbol}'}
            
            options_data = {
                'symbol': symbol,
                'expiration_dates': list(expiration_dates),
                'chains': {}
            }
            
            # If specific expiration date requested
            if expiration_date:
                if expiration_date in expiration_dates:
                    expiration_dates = [expiration_date]
                else:
                    return {'error': f'Expiration date {expiration_date} not available for {symbol}'}
            
            # Fetch options for each expiration date
            for exp_date in expiration_dates:
                try:
                    chain = ticker.option_chain(exp_date)
                    
                    # Process calls
                    calls = chain.calls.copy()
                    calls['optionType'] = 'call'
                    calls['expirationDate'] = exp_date
                    
                    # Process puts
                    puts = chain.puts.copy()
                    puts['optionType'] = 'put'
                    puts['expirationDate'] = exp_date
                    
                    # Calculate additional metrics
                    current_price = self._get_current_price(symbol)
                    if current_price:
                        calls['moneyness'] = calls['strike'] / current_price
                        puts['moneyness'] = puts['strike'] / current_price
                        
                        # Calculate days to expiration
                        exp_datetime = pd.to_datetime(exp_date)
                        days_to_exp = (exp_datetime - pd.Timestamp.now()).days
                        calls['daysToExpiration'] = days_to_exp
                        puts['daysToExpiration'] = days_to_exp
                    
                    options_data['chains'][exp_date] = {
                        'calls': calls,
                        'puts': puts,
                        'current_price': current_price
                    }
                    
                except Exception as e:
                    print(f"Error fetching options for {symbol} exp {exp_date}: {e}")
                    continue
            
            return options_data
            
        except Exception as e:
            return {'error': f"Error fetching options chain for {symbol}: {e}"}
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current stock price."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return hist['Close'].iloc[-1]
        except:
            pass
        return None
    
    def get_implied_volatilities(self, symbol: str, expiration_date: Optional[str] = None) -> Dict:
        """
        Get implied volatilities from options chain.
        
        Args:
            symbol: Stock symbol
            expiration_date: Specific expiration date, if None uses nearest expiration
            
        Returns:
            Dictionary with implied volatility data
        """
        options_data = self.fetch_options_chain(symbol, expiration_date)
        
        if 'error' in options_data:
            return options_data
        
        iv_data = {
            'symbol': symbol,
            'iv_surface': {}
        }
        
        for exp_date, chain_data in options_data['chains'].items():
            calls = chain_data['calls']
            puts = chain_data['puts']
            current_price = chain_data['current_price']
            
            if current_price and len(calls) > 0:
                # Get ATM implied volatility
                atm_calls = calls[abs(calls['strike'] - current_price) == abs(calls['strike'] - current_price).min()]
                atm_puts = puts[abs(puts['strike'] - current_price) == abs(puts['strike'] - current_price).min()]
                
                iv_data['iv_surface'][exp_date] = {
                    'atm_call_iv': atm_calls['impliedVolatility'].iloc[0] if len(atm_calls) > 0 else None,
                    'atm_put_iv': atm_puts['impliedVolatility'].iloc[0] if len(atm_puts) > 0 else None,
                    'call_iv_range': [calls['impliedVolatility'].min(), calls['impliedVolatility'].max()],
                    'put_iv_range': [puts['impliedVolatility'].min(), puts['impliedVolatility'].max()],
                    'current_price': current_price,
                    'days_to_expiration': calls['daysToExpiration'].iloc[0] if len(calls) > 0 else None
                }
        
        return iv_data
    
    def calculate_volatility(self, returns: pd.Series, 
                           window: Optional[int] = None,
                           annualize: bool = True) -> Union[float, pd.Series]:
        """
        Calculate historical volatility.
        
        Args:
            returns: Return series
            window: Rolling window size (None for single value)
            annualize: Whether to annualize the volatility
            
        Returns:
            Volatility (float if window is None, Series if window is specified)
        """
        if window is None:
            volatility = returns.std()
        else:
            volatility = returns.rolling(window=window).std()
        
        if annualize:
            volatility *= np.sqrt(252)  # Assume 252 trading days per year
        
        return volatility