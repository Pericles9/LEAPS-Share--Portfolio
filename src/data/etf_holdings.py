"""
ETF Holdings Manager

Automatically extract holdings from sector ETFs and add them to the portfolio universe.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time
import json
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ETFHolding:
    """Individual holding within an ETF."""
    symbol: str
    name: str
    weight: float
    sector: Optional[str] = None
    shares: Optional[int] = None


@dataclass
class ETFInfo:
    """Information about an ETF and its holdings."""
    symbol: str
    name: str
    holdings: List[ETFHolding]
    total_holdings: int
    expense_ratio: Optional[float] = None
    aum: Optional[float] = None


class ETFHoldingsManager:
    """Manage ETF holdings extraction and universe building."""
    
    def __init__(self):
        """Initialize the ETF holdings manager."""
        self.etf_cache = {}
        self.popular_sector_etfs = {
            # SPDR Sector ETFs
            'XLK': 'Technology Select Sector SPDR Fund',
            'XLF': 'Financial Select Sector SPDR Fund', 
            'XLV': 'Health Care Select Sector SPDR Fund',
            'XLE': 'Energy Select Sector SPDR Fund',
            'XLI': 'Industrial Select Sector SPDR Fund',
            'XLY': 'Consumer Discretionary Select Sector SPDR Fund',
            'XLP': 'Consumer Staples Select Sector SPDR Fund',
            'XLU': 'Utilities Select Sector SPDR Fund',
            'XLB': 'Materials Select Sector SPDR Fund',
            'XLRE': 'Real Estate Select Sector SPDR Fund',
            'XLC': 'Communication Services Select Sector SPDR Fund',
            
            # Vanguard Sector ETFs
            'VGT': 'Vanguard Information Technology ETF',
            'VFH': 'Vanguard Financials ETF',
            'VHT': 'Vanguard Health Care ETF',
            'VDE': 'Vanguard Energy ETF',
            'VIS': 'Vanguard Industrials ETF',
            'VCR': 'Vanguard Consumer Discretionary ETF',
            'VDC': 'Vanguard Consumer Staples ETF',
            'VPU': 'Vanguard Utilities ETF',
            'VAW': 'Vanguard Materials ETF',
            'VNQ': 'Vanguard Real Estate ETF',
            
            # iShares Sector ETFs
            'IYW': 'iShares U.S. Technology ETF',
            'IYF': 'iShares U.S. Financials ETF',
            'IYH': 'iShares U.S. Healthcare ETF',
            'IYE': 'iShares U.S. Energy ETF',
            'IYJ': 'iShares U.S. Industrials ETF',
            'IYC': 'iShares U.S. Consumer Discretionary ETF',
            'IYK': 'iShares U.S. Consumer Staples ETF',
            'IDU': 'iShares U.S. Utilities ETF',
            'IYM': 'iShares U.S. Basic Materials ETF',
            'IYZ': 'iShares U.S. Telecommunications ETF',
            
            # Popular broad market and thematic ETFs
            'SPY': 'SPDR S&P 500 ETF Trust',
            'QQQ': 'Invesco QQQ Trust',
            'IWM': 'iShares Russell 2000 ETF',
            'VTI': 'Vanguard Total Stock Market ETF',
            'ARKK': 'ARK Innovation ETF',
            'ARKG': 'ARK Genomics Revolution ETF',
            'ARKQ': 'ARK Autonomous & Robotics ETF',
            'ARKW': 'ARK Next Generation Internet ETF',
            'SOXX': 'iShares Semiconductor ETF',
            'JETS': 'U.S. Global Jets ETF',
            'ICLN': 'iShares Global Clean Energy ETF',
            'GDX': 'VanEck Gold Miners ETF'
        }
    
    def get_etf_holdings_yfinance(self, etf_symbol: str, top_n: Optional[int] = None) -> Optional[ETFInfo]:
        """
        Get ETF holdings using yfinance (limited data available).
        
        Args:
            etf_symbol: ETF symbol
            top_n: Number of top holdings to return (None for all available)
            
        Returns:
            ETFInfo object or None if failed
        """
        try:
            etf = yf.Ticker(etf_symbol)
            
            # Get basic info
            info = etf.info
            etf_name = info.get('longName', etf_symbol)
            
            # Try to get major holdings (limited in yfinance)
            holdings = []
            
            # yfinance sometimes has holdings data in the info
            if 'holdings' in info:
                holdings_data = info['holdings']
                for holding in holdings_data:
                    holdings.append(ETFHolding(
                        symbol=holding.get('symbol', ''),
                        name=holding.get('holdingName', ''),
                        weight=holding.get('holdingPercent', 0) * 100
                    ))
            
            # Try alternative approach - get major holdings from fund data
            try:
                major_holders = etf.major_holders
                if major_holders is not None and not major_holders.empty:
                    # This usually contains institutional holders, not individual stocks
                    pass
            except:
                pass
            
            # If we have holdings, create ETFInfo
            if holdings or info:
                return ETFInfo(
                    symbol=etf_symbol,
                    name=etf_name,
                    holdings=holdings[:top_n] if top_n else holdings,
                    total_holdings=len(holdings),
                    expense_ratio=info.get('annualReportExpenseRatio'),
                    aum=info.get('totalAssets')
                )
            
            return None
            
        except Exception as e:
            print(f"Error fetching holdings for {etf_symbol}: {e}")
            return None
    
    def get_etf_holdings_alternative(self, etf_symbol: str, top_n: Optional[int] = 50) -> Optional[ETFInfo]:
        """
        Alternative method to get ETF holdings using known compositions.
        This is a fallback when APIs don't provide holdings data.
        """
        # For demonstration, we'll use some known large holdings for popular ETFs
        known_holdings = {
            'SPY': [
                ('AAPL', 'Apple Inc', 7.1), ('MSFT', 'Microsoft Corp', 6.8),
                ('AMZN', 'Amazon.com Inc', 3.4), ('NVDA', 'NVIDIA Corp', 3.1),
                ('GOOGL', 'Alphabet Inc Class A', 2.1), ('TSLA', 'Tesla Inc', 2.0),
                ('GOOG', 'Alphabet Inc Class C', 2.0), ('META', 'Meta Platforms Inc', 1.9),
                ('BRK-B', 'Berkshire Hathaway Inc Class B', 1.7), ('UNH', 'UnitedHealth Group Inc', 1.3)
            ],
            'QQQ': [
                ('AAPL', 'Apple Inc', 8.7), ('MSFT', 'Microsoft Corp', 8.1),
                ('AMZN', 'Amazon.com Inc', 5.4), ('NVDA', 'NVIDIA Corp', 4.8),
                ('META', 'Meta Platforms Inc', 4.7), ('GOOGL', 'Alphabet Inc Class A', 4.5),
                ('GOOG', 'Alphabet Inc Class C', 4.3), ('TSLA', 'Tesla Inc', 3.8),
                ('AVGO', 'Broadcom Inc', 2.4), ('COST', 'Costco Wholesale Corp', 2.2)
            ],
            'XLK': [
                ('AAPL', 'Apple Inc', 22.1), ('MSFT', 'Microsoft Corp', 21.8),
                ('NVDA', 'NVIDIA Corp', 9.2), ('AVGO', 'Broadcom Inc', 4.1),
                ('CRM', 'Salesforce Inc', 2.6), ('ORCL', 'Oracle Corp', 2.5),
                ('ADBE', 'Adobe Inc', 2.4), ('ACN', 'Accenture PLC Class A', 2.1),
                ('NOW', 'ServiceNow Inc', 1.9), ('TXN', 'Texas Instruments Inc', 1.8)
            ],
            'XLF': [
                ('BRK-B', 'Berkshire Hathaway Inc Class B', 12.8), ('JPM', 'JPMorgan Chase & Co', 10.1),
                ('V', 'Visa Inc Class A', 7.2), ('MA', 'Mastercard Inc Class A', 6.1),
                ('BAC', 'Bank of America Corp', 4.9), ('WFC', 'Wells Fargo & Co', 3.6),
                ('GS', 'Goldman Sachs Group Inc', 2.8), ('SPGI', 'S&P Global Inc', 2.7),
                ('MS', 'Morgan Stanley', 2.6), ('AXP', 'American Express Co', 2.4)
            ],
            'XLV': [
                ('UNH', 'UnitedHealth Group Inc', 9.8), ('JNJ', 'Johnson & Johnson', 8.1),
                ('PFE', 'Pfizer Inc', 5.2), ('ABBV', 'AbbVie Inc', 4.9),
                ('TMO', 'Thermo Fisher Scientific Inc', 4.2), ('MRK', 'Merck & Co Inc', 4.1),
                ('ABT', 'Abbott Laboratories', 3.8), ('DHR', 'Danaher Corp', 3.2),
                ('BMY', 'Bristol-Myers Squibb Co', 2.8), ('AMGN', 'Amgen Inc', 2.6)
            ]
        }
        
        if etf_symbol.upper() in known_holdings:
            holdings_data = known_holdings[etf_symbol.upper()]
            if top_n:
                holdings_data = holdings_data[:top_n]
            
            holdings = [
                ETFHolding(symbol=symbol, name=name, weight=weight)
                for symbol, name, weight in holdings_data
            ]
            
            etf_name = self.popular_sector_etfs.get(etf_symbol.upper(), etf_symbol)
            
            return ETFInfo(
                symbol=etf_symbol.upper(),
                name=etf_name,
                holdings=holdings,
                total_holdings=len(holdings)
            )
        
        return None
    
    def get_etf_holdings(self, etf_symbol: str, top_n: Optional[int] = 50) -> Optional[ETFInfo]:
        """
        Get ETF holdings using multiple methods.
        
        Args:
            etf_symbol: ETF symbol
            top_n: Number of top holdings to return
            
        Returns:
            ETFInfo object or None if failed
        """
        etf_symbol = etf_symbol.upper()
        
        # Check cache first
        if etf_symbol in self.etf_cache:
            cached_info = self.etf_cache[etf_symbol]
            return ETFInfo(
                symbol=cached_info.symbol,
                name=cached_info.name,
                holdings=cached_info.holdings[:top_n] if top_n else cached_info.holdings,
                total_holdings=cached_info.total_holdings,
                expense_ratio=cached_info.expense_ratio,
                aum=cached_info.aum
            )
        
        print(f"Fetching holdings for {etf_symbol}...")
        
        # Try yfinance first
        etf_info = self.get_etf_holdings_yfinance(etf_symbol, top_n)
        
        # If yfinance fails or returns no holdings, try alternative method
        if not etf_info or not etf_info.holdings:
            etf_info = self.get_etf_holdings_alternative(etf_symbol, top_n)
        
        # Cache the result
        if etf_info:
            self.etf_cache[etf_symbol] = etf_info
            print(f"✓ Found {len(etf_info.holdings)} holdings for {etf_symbol}")
        else:
            print(f"✗ Could not fetch holdings for {etf_symbol}")
        
        return etf_info
    
    def extract_symbols_from_etfs(self, etf_symbols: List[str], 
                                 min_weight: float = 0.5,
                                 top_n_per_etf: Optional[int] = 20) -> Dict[str, List[str]]:
        """
        Extract stock symbols from multiple ETFs.
        
        Args:
            etf_symbols: List of ETF symbols
            min_weight: Minimum weight threshold for including stocks
            top_n_per_etf: Maximum number of holdings per ETF
            
        Returns:
            Dictionary mapping ETF symbols to list of stock symbols
        """
        etf_holdings = {}
        
        for etf_symbol in etf_symbols:
            etf_info = self.get_etf_holdings(etf_symbol, top_n_per_etf)
            
            if etf_info and etf_info.holdings:
                # Filter by minimum weight and valid symbols
                valid_symbols = []
                for holding in etf_info.holdings:
                    if (holding.weight >= min_weight and 
                        holding.symbol and 
                        len(holding.symbol) <= 5 and  # Filter out complex symbols
                        not any(char in holding.symbol for char in ['.', '=', '^'])):  # Filter out indices/bonds
                        valid_symbols.append(holding.symbol)
                
                etf_holdings[etf_symbol] = valid_symbols
                print(f"  {etf_symbol}: {len(valid_symbols)} stocks (min weight: {min_weight}%)")
            else:
                etf_holdings[etf_symbol] = []
                print(f"  {etf_symbol}: No holdings found")
        
        return etf_holdings
    
    def build_universe_from_etfs(self, etf_symbols: List[str],
                                min_weight: float = 0.5,
                                top_n_per_etf: Optional[int] = 20,
                                remove_duplicates: bool = True) -> List[str]:
        """
        Build a universe of stocks from multiple ETFs.
        
        Args:
            etf_symbols: List of ETF symbols
            min_weight: Minimum weight threshold
            top_n_per_etf: Maximum holdings per ETF
            remove_duplicates: Whether to remove duplicate symbols
            
        Returns:
            List of unique stock symbols
        """
        print(f"Building universe from {len(etf_symbols)} ETFs...")
        print(f"ETFs: {', '.join(etf_symbols)}")
        
        etf_holdings = self.extract_symbols_from_etfs(etf_symbols, min_weight, top_n_per_etf)
        
        # Combine all symbols
        all_symbols = []
        for etf, symbols in etf_holdings.items():
            all_symbols.extend(symbols)
        
        if remove_duplicates:
            unique_symbols = list(set(all_symbols))
            print(f"\nTotal unique stocks: {len(unique_symbols)} (from {len(all_symbols)} total holdings)")
        else:
            unique_symbols = all_symbols
            print(f"\nTotal stocks: {len(all_symbols)}")
        
        return sorted(unique_symbols)
    
    def get_popular_sector_etfs(self) -> Dict[str, str]:
        """Get dictionary of popular sector ETFs."""
        return self.popular_sector_etfs.copy()
    
    def print_etf_info(self, etf_symbol: str) -> None:
        """Print detailed information about an ETF."""
        etf_info = self.get_etf_holdings(etf_symbol)
        
        if not etf_info:
            print(f"No information found for {etf_symbol}")
            return
        
        print(f"\n{etf_info.symbol} - {etf_info.name}")
        print("-" * 60)
        print(f"Total Holdings: {etf_info.total_holdings}")
        if etf_info.expense_ratio:
            print(f"Expense Ratio: {etf_info.expense_ratio:.2%}")
        if etf_info.aum:
            print(f"AUM: ${etf_info.aum:,.0f}")
        
        print(f"\nTop Holdings:")
        for i, holding in enumerate(etf_info.holdings[:10], 1):
            print(f"  {i:2d}. {holding.symbol:<6} - {holding.name:<30} ({holding.weight:.1f}%)")
    
    def suggest_etfs_by_theme(self, theme: str) -> List[str]:
        """Suggest ETFs based on investment theme."""
        theme = theme.lower()
        suggestions = []
        
        theme_mapping = {
            'technology': ['XLK', 'VGT', 'IYW', 'QQQ', 'SOXX'],
            'tech': ['XLK', 'VGT', 'IYW', 'QQQ', 'SOXX'], 
            'financial': ['XLF', 'VFH', 'IYF'],
            'healthcare': ['XLV', 'VHT', 'IYH'],
            'energy': ['XLE', 'VDE', 'IYE'],
            'industrial': ['XLI', 'VIS', 'IYJ'],
            'consumer': ['XLY', 'XLP', 'VCR', 'VDC', 'IYC', 'IYK'],
            'utilities': ['XLU', 'VPU', 'IDU'],
            'materials': ['XLB', 'VAW', 'IYM'],
            'real estate': ['XLRE', 'VNQ'],
            'communication': ['XLC'],
            'broad market': ['SPY', 'VTI', 'QQQ'],
            'small cap': ['IWM'],
            'innovation': ['ARKK', 'ARKG', 'ARKQ', 'ARKW'],
            'semiconductor': ['SOXX'],
            'aviation': ['JETS'],
            'clean energy': ['ICLN'],
            'gold': ['GDX']
        }
        
        for key, etfs in theme_mapping.items():
            if theme in key or key in theme:
                suggestions.extend(etfs)
        
        return list(set(suggestions))  # Remove duplicates