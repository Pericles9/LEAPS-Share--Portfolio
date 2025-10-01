#!/usr/bin/env python3
"""
Polygon.io Options Data Source for Portfolio System
Premium real-time and historical options data integration
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
import requests
import time
import os
from polygon import RESTClient
import warnings
warnings.filterwarnings('ignore')

class PolygonOptionsDataSource:
    """
    Premium options data source using Polygon.io API
    Provides real-time options chains, historical data, and Greeks
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polygon.io client
        
        Args:
            api_key: Polygon.io API key. If None, will try to get from environment
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("Polygon.io API key required. Set POLYGON_API_KEY environment variable or pass api_key parameter")
        
        self.client = RESTClient(self.api_key)
        self.name = "Polygon.io"
        print(f"   Polygon.io client initialized with API key: {self.api_key[:8]}...")
        
    def get_options_data(self, symbol: str, option_type: str = 'both') -> Dict:
        """
        Get comprehensive options data from Polygon.io
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            option_type: 'calls', 'puts', or 'both'
            
        Returns:
            Dictionary with calls and puts DataFrames
        """
        print(f"Fetching options data for {symbol} from Polygon.io...")
        
        try:
            # Get current stock price
            stock_price = self._get_stock_price(symbol)
            if not stock_price:
                return self._empty_result()
            
            # Get options contracts
            contracts = self._get_options_contracts(symbol)
            if not contracts:
                return self._empty_result()
            
            # Get current options quotes
            calls_df = pd.DataFrame()
            puts_df = pd.DataFrame()
            
            if option_type in ['calls', 'both']:
                calls_df = self._get_options_quotes(contracts, 'call', stock_price)
                
            if option_type in ['puts', 'both']:
                puts_df = self._get_options_quotes(contracts, 'put', stock_price)
            
            # Get expiration dates
            exp_dates = self._extract_expiration_dates(contracts)
            
            return {
                'calls': calls_df,
                'puts': puts_df,
                'stock_price': stock_price,
                'expiration_dates': exp_dates,
                'source': 'polygon.io'
            }
            
        except Exception as e:
            print(f"Error fetching data from Polygon.io: {e}")
            return self._empty_result()
    
    def _get_stock_price(self, symbol: str) -> Optional[float]:
        """Get current stock price from Polygon.io"""
        try:
            # Get the most recent daily bar
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_=datetime.now().date() - timedelta(days=5),
                to=datetime.now().date()
            )
            
            if aggs and len(aggs) > 0:
                # Use the close price from the most recent bar
                return float(aggs[-1].close)
            
            return None
            
        except Exception as e:
            print(f"Error getting stock price for {symbol}: {e}")
            return None
    
    def _get_options_contracts(self, symbol: str, limit: int = 1000) -> List:
        """Get available options contracts for a symbol"""
        try:
            # Get options contracts
            contracts = self.client.list_options_contracts(
                underlying_ticker=symbol,
                limit=limit,
                expired=False  # Only active contracts
            )
            
            if contracts:
                return list(contracts)
            
            return []
            
        except Exception as e:
            print(f"Error getting options contracts for {symbol}: {e}")
            return []
    
    def _get_options_quotes(self, contracts: List, option_type: str, stock_price: float) -> pd.DataFrame:
        """Get current quotes for options contracts"""
        try:
            data = []
            
            # Filter contracts by type and get relevant strikes
            relevant_contracts = []
            for contract in contracts:
                if not hasattr(contract, 'contract_type') or not hasattr(contract, 'strike_price'):
                    continue
                    
                if contract.contract_type.lower() != option_type.lower():
                    continue
                
                # Focus on strikes near the money (±20%)
                strike = float(contract.strike_price)
                if strike < stock_price * 0.8 or strike > stock_price * 1.2:
                    continue
                
                relevant_contracts.append(contract)
            
            # Limit to avoid rate limits
            relevant_contracts = relevant_contracts[:50]
            
            print(f"   Getting quotes for {len(relevant_contracts)} {option_type} contracts...")
            
            for i, contract in enumerate(relevant_contracts):
                try:
                    # Add small delay to respect rate limits
                    if i > 0 and i % 10 == 0:
                        time.sleep(0.5)
                    
                    # Get the latest quote
                    ticker = contract.ticker
                    quote = self.client.get_last_quote(ticker=ticker)
                    
                    if quote:
                        data.append({
                            'strike': float(contract.strike_price),
                            'expiration': contract.expiration_date,
                            'lastPrice': (quote.bid + quote.ask) / 2 if quote.bid and quote.ask else 0,
                            'bid': quote.bid or 0,
                            'ask': quote.ask or 0,
                            'volume': getattr(quote, 'volume', 0),
                            'openInterest': getattr(contract, 'open_interest', 0),
                            'ticker': ticker
                        })
                    
                except Exception as e:
                    print(f"   Error getting quote for contract {getattr(contract, 'ticker', 'unknown')}: {e}")
                    continue
            
            if data:
                df = pd.DataFrame(data)
                # Sort by strike price
                df = df.sort_values('strike').reset_index(drop=True)
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error getting options quotes: {e}")
            return pd.DataFrame()
    
    def _extract_expiration_dates(self, contracts: List) -> List[str]:
        """Extract unique expiration dates from contracts"""
        try:
            dates = set()
            for contract in contracts:
                if hasattr(contract, 'expiration_date'):
                    dates.add(str(contract.expiration_date))
            
            return sorted(list(dates))
            
        except Exception as e:
            print(f"Error extracting expiration dates: {e}")
            return []
    
    def get_options_chain_by_expiration(self, symbol: str, expiration_date: str) -> Dict:
        """Get options chain for specific expiration date"""
        try:
            stock_price = self._get_stock_price(symbol)
            if not stock_price:
                return self._empty_result()
            
            # Get contracts for specific expiration
            contracts = self.client.list_options_contracts(
                underlying_ticker=symbol,
                expiration_date=expiration_date,
                limit=1000,
                expired=False
            )
            
            if not contracts:
                return self._empty_result()
            
            contracts_list = list(contracts)
            calls_df = self._get_options_quotes(contracts_list, 'call', stock_price)
            puts_df = self._get_options_quotes(contracts_list, 'put', stock_price)
            
            return {
                'calls': calls_df,
                'puts': puts_df,
                'stock_price': stock_price,
                'expiration_date': expiration_date,
                'source': 'polygon.io'
            }
            
        except Exception as e:
            print(f"Error getting options chain for {expiration_date}: {e}")
            return self._empty_result()
    
    def get_historical_options_data(self, option_ticker: str, days: int = 30) -> pd.DataFrame:
        """Get historical options data for a specific option"""
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get historical aggregates for the option
            aggs = self.client.get_aggs(
                ticker=option_ticker,
                multiplier=1,
                timespan="day",
                from_=start_date,
                to=end_date
            )
            
            if aggs:
                data = []
                for agg in aggs:
                    data.append({
                        'date': datetime.fromtimestamp(agg.timestamp / 1000).date(),
                        'open': agg.open,
                        'high': agg.high,
                        'low': agg.low,
                        'close': agg.close,
                        'volume': agg.volume
                    })
                
                return pd.DataFrame(data)
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error getting historical data for {option_ticker}: {e}")
            return pd.DataFrame()
    
    def get_options_analytics(self, symbol: str) -> Dict:
        """Get advanced options analytics from Polygon.io"""
        try:
            # This would use Polygon.io's advanced analytics endpoints
            # For now, we'll return basic analytics based on the options data
            
            options_data = self.get_options_data(symbol, 'both')
            if not options_data or options_data['source'] == 'error':
                return {}
            
            calls = options_data['calls']
            puts = options_data['puts']
            
            if calls.empty or puts.empty:
                return {}
            
            # Calculate analytics
            total_call_volume = calls['volume'].sum()
            total_put_volume = puts['volume'].sum()
            total_call_oi = calls['openInterest'].sum()
            total_put_oi = puts['openInterest'].sum()
            
            analytics = {
                'put_call_volume_ratio': total_put_volume / max(total_call_volume, 1),
                'put_call_oi_ratio': total_put_oi / max(total_call_oi, 1),
                'total_volume': total_call_volume + total_put_volume,
                'total_open_interest': total_call_oi + total_put_oi,
                'max_pain': self._calculate_max_pain(calls, puts, options_data['stock_price']),
                'gamma_exposure': self._calculate_gamma_exposure(calls, puts, options_data['stock_price'])
            }
            
            return analytics
            
        except Exception as e:
            print(f"Error getting options analytics: {e}")
            return {}
    
    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame, stock_price: float) -> float:
        """Calculate max pain point"""
        try:
            if calls.empty or puts.empty:
                return stock_price
            
            # Get all unique strikes
            all_strikes = pd.concat([calls['strike'], puts['strike']]).unique()
            
            max_pain_strike = stock_price
            min_pain = float('inf')
            
            for strike in all_strikes:
                # Calculate total pain at this strike
                call_pain = calls[calls['strike'] < strike]['openInterest'].sum() * (strike - calls[calls['strike'] < strike]['strike']).sum()
                put_pain = puts[puts['strike'] > strike]['openInterest'].sum() * (puts[puts['strike'] > strike]['strike'] - strike).sum()
                
                total_pain = call_pain + put_pain
                
                if total_pain < min_pain:
                    min_pain = total_pain
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            print(f"Error calculating max pain: {e}")
            return stock_price
    
    def _calculate_gamma_exposure(self, calls: pd.DataFrame, puts: pd.DataFrame, stock_price: float) -> float:
        """Calculate gamma exposure (simplified)"""
        try:
            # Simplified gamma exposure calculation
            # In a real implementation, you'd use actual Greeks from Polygon.io
            
            total_gamma = 0
            
            # Estimate gamma for calls (higher for ATM options)
            for _, call in calls.iterrows():
                strike = call['strike']
                oi = call['openInterest']
                
                # Simple gamma approximation (peaks at ATM)
                moneyness = abs(stock_price - strike) / stock_price
                gamma_estimate = max(0, 0.1 * (1 - moneyness * 2)) if moneyness < 0.5 else 0
                total_gamma += gamma_estimate * oi
            
            # Estimate gamma for puts (negative contribution)
            for _, put in puts.iterrows():
                strike = put['strike']
                oi = put['openInterest']
                
                moneyness = abs(stock_price - strike) / stock_price
                gamma_estimate = max(0, 0.1 * (1 - moneyness * 2)) if moneyness < 0.5 else 0
                total_gamma -= gamma_estimate * oi
            
            return total_gamma
            
        except Exception as e:
            print(f"Error calculating gamma exposure: {e}")
            return 0.0
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'calls': pd.DataFrame(),
            'puts': pd.DataFrame(),
            'stock_price': 0.0,
            'expiration_dates': [],
            'source': 'polygon_error'
        }

def test_polygon_integration():
    """Test the Polygon.io integration"""
    print("TESTING POLYGON.IO INTEGRATION")
    print("=" * 50)
    
    # Check if API key is available
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY environment variable not set")
        print("\n🔑 TO SET YOUR API KEY:")
        print("   Method 1 - Environment Variable (Recommended):")
        print("   SET POLYGON_API_KEY=your_api_key_here")
        print("   \n   Method 2 - Direct in code:")
        print("   polygon_source = PolygonOptionsDataSource(api_key='your_api_key_here')")
        return
    
    try:
        polygon_source = PolygonOptionsDataSource()
        
        # Test with AAPL
        symbol = 'AAPL'
        print(f"\n--- Testing {symbol} ---")
        
        result = polygon_source.get_options_data(symbol, 'both')
        
        print(f"Stock price: ${result['stock_price']}")
        print(f"Expiration dates: {len(result['expiration_dates'])}")
        print(f"Calls: {len(result['calls'])} options")
        print(f"Puts: {len(result['puts'])} options")
        print(f"Data source: {result['source']}")
        
        if not result['calls'].empty:
            print("\nSample call options:")
            print(result['calls'].head().to_string())
        
        # Test analytics
        print(f"\n--- Analytics for {symbol} ---")
        analytics = polygon_source.get_options_analytics(symbol)
        for key, value in analytics.items():
            print(f"{key}: {value}")
        
        print("\n✅ Polygon.io integration successful!")
        
    except Exception as e:
        print(f"❌ Error testing Polygon.io: {e}")
        print("\n🔑 Make sure your API key is valid and has options data access")

if __name__ == "__main__":
    test_polygon_integration()