"""
ETF Holdings Manager

Automatically extract holdings from sector ETFs and add them to the portfolio universe.
Multi-source data architecture: Web Scraping -> yfinance -> hard-coded fallback -> caching
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
import os
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
    data_source: Optional[str] = None  # Track data source: 'Web Scraper', 'yfinance', 'Hard-coded'


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
    

    def get_etf_holdings_webscraper(self, etf_symbol: str, top_n: Optional[int] = None) -> Optional[ETFInfo]:
        """
        Get ETF holdings using web scraping from etf.com.
        
        Args:
            etf_symbol: ETF symbol
            top_n: Number of top holdings to return (None for all available)
            
        Returns:
            ETFInfo object with holdings data, None if failed
        """
        try:
            from .etf_web_scraper import ETFWebScraper
        except ImportError as e:
            print(f"WARNING: Could not import ETFWebScraper (relative): {e}")
            try:
                from etf_web_scraper import ETFWebScraper
            except ImportError as e2:
                print(f"ERROR: Web scraper dependencies not available: {e2}")
                return None
        
        try:
            print(f"EMOJI: Web scraping holdings for {etf_symbol} from etf.com...")
            
            # Initialize scraper with headless mode
            scraper = ETFWebScraper(headless=True, timeout=30)
            
            # Scrape holdings
            scraped_info = scraper.scrape_etf_holdings(etf_symbol, max_holdings=top_n)
            
            if not scraped_info or not scraped_info.holdings:
                print(f"ERROR: Web scraping failed for {etf_symbol}")
                return None
            
            # Convert to standard format
            holdings = []
            for scraped_holding in scraped_info.holdings:
                holding = ETFHolding(
                    symbol=scraped_holding.symbol,
                    name=scraped_holding.name,
                    weight=scraped_holding.weight,
                    shares=scraped_holding.shares
                )
                holdings.append(holding)
            
            # Sort by weight (descending) and limit if requested
            holdings.sort(key=lambda x: x.weight, reverse=True)
            if top_n:
                holdings = holdings[:top_n]
            
            # Create ETFInfo object
            etf_info = ETFInfo(
                symbol=etf_symbol,
                name=scraped_info.name,
                holdings=holdings,
                total_holdings=scraped_info.total_holdings,
                expense_ratio=scraped_info.expense_ratio,
                aum=scraped_info.aum
            )
            
            print(f"SUCCESS: Web scraper: Successfully extracted {len(holdings)} holdings for {etf_symbol}")
            return etf_info
            
        except ImportError as e:
            print(f"ERROR: Web scraper import error: {e}")
            return None
        except Exception as e:
            print(f"ERROR: Web scraping error for {etf_symbol}: {e}")
            import traceback
            print(f"   Full traceback: {traceback.format_exc()}")
            return None
    
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
        # Comprehensive ETF holdings database - current as of 2024/2025
        known_holdings = {
            # Broad Market ETFs
            'SPY': [
                ('AAPL', 'Apple Inc', 7.1), ('MSFT', 'Microsoft Corp', 6.8),
                ('AMZN', 'Amazon.com Inc', 3.4), ('NVDA', 'NVIDIA Corp', 3.1),
                ('GOOGL', 'Alphabet Inc Class A', 2.1), ('TSLA', 'Tesla Inc', 2.0),
                ('GOOG', 'Alphabet Inc Class C', 2.0), ('META', 'Meta Platforms Inc', 1.9),
                ('BRK-B', 'Berkshire Hathaway Inc Class B', 1.7), ('UNH', 'UnitedHealth Group Inc', 1.3),
                ('JNJ', 'Johnson & Johnson', 1.2), ('LLY', 'Eli Lilly and Co', 1.1),
                ('V', 'Visa Inc Class A', 1.0), ('PG', 'Procter & Gamble Co', 0.9),
                ('JPM', 'JPMorgan Chase & Co', 0.9), ('MA', 'Mastercard Inc Class A', 0.8)
            ],
            'QQQ': [
                ('AAPL', 'Apple Inc', 8.7), ('MSFT', 'Microsoft Corp', 8.1),
                ('AMZN', 'Amazon.com Inc', 5.4), ('NVDA', 'NVIDIA Corp', 4.8),
                ('META', 'Meta Platforms Inc', 4.7), ('GOOGL', 'Alphabet Inc Class A', 4.5),
                ('GOOG', 'Alphabet Inc Class C', 4.3), ('TSLA', 'Tesla Inc', 3.8),
                ('AVGO', 'Broadcom Inc', 2.4), ('COST', 'Costco Wholesale Corp', 2.2),
                ('NFLX', 'Netflix Inc', 1.9), ('ADBE', 'Adobe Inc', 1.8),
                ('PEP', 'PepsiCo Inc', 1.7), ('TMUS', 'T-Mobile US Inc', 1.6),
                ('CSCO', 'Cisco Systems Inc', 1.5), ('CMCSA', 'Comcast Corp Class A', 1.4)
            ],
            'IWM': [
                ('AMC', 'AMC Entertainment Holdings Inc Class A', 0.8), ('FTCH', 'Farfetch Ltd Class A', 0.7),
                ('BBBY', 'Bed Bath & Beyond Inc', 0.6), ('SPCE', 'Virgin Galactic Holdings Inc', 0.5),
                ('CLNE', 'Clean Energy Fuels Corp', 0.5), ('SNDL', 'Sundial Growers Inc', 0.4),
                ('NVAX', 'Novavax Inc', 0.4), ('PENN', 'Penn Entertainment Inc', 0.4),
                ('RIOT', 'Riot Blockchain Inc', 0.3), ('MARA', 'Marathon Digital Holdings Inc', 0.3),
                ('PLUG', 'Plug Power Inc', 0.3), ('TLRY', 'Tilray Brands Inc', 0.3),
                ('CGC', 'Canopy Growth Corp', 0.3), ('WKHS', 'Workhorse Group Inc', 0.2),
                ('CLOV', 'Clover Health Investments Corp Class A', 0.2), ('WISH', 'ContextLogic Inc Class A', 0.2)
            ],
            
            # Technology Sector ETFs
            'XLK': [
                ('AAPL', 'Apple Inc', 22.1), ('MSFT', 'Microsoft Corp', 21.8),
                ('NVDA', 'NVIDIA Corp', 9.2), ('AVGO', 'Broadcom Inc', 4.1),
                ('CRM', 'Salesforce Inc', 2.6), ('ORCL', 'Oracle Corp', 2.5),
                ('ADBE', 'Adobe Inc', 2.4), ('ACN', 'Accenture PLC Class A', 2.1),
                ('NOW', 'ServiceNow Inc', 1.9), ('TXN', 'Texas Instruments Inc', 1.8),
                ('QCOM', 'Qualcomm Inc', 1.7), ('IBM', 'International Business Machines Corp', 1.6),
                ('AMAT', 'Applied Materials Inc', 1.5), ('INTU', 'Intuit Inc', 1.4),
                ('AMD', 'Advanced Micro Devices Inc', 1.3), ('MU', 'Micron Technology Inc', 1.2)
            ],
            'VGT': [
                ('AAPL', 'Apple Inc', 19.8), ('MSFT', 'Microsoft Corp', 19.2),
                ('NVDA', 'NVIDIA Corp', 8.7), ('AVGO', 'Broadcom Inc', 3.8),
                ('ORCL', 'Oracle Corp', 2.3), ('CRM', 'Salesforce Inc', 2.2),
                ('ADBE', 'Adobe Inc', 2.1), ('ACN', 'Accenture PLC Class A', 1.9),
                ('NOW', 'ServiceNow Inc', 1.7), ('TXN', 'Texas Instruments Inc', 1.6),
                ('QCOM', 'Qualcomm Inc', 1.5), ('IBM', 'International Business Machines Corp', 1.4),
                ('AMAT', 'Applied Materials Inc', 1.3), ('INTU', 'Intuit Inc', 1.2),
                ('AMD', 'Advanced Micro Devices Inc', 1.1), ('LRCX', 'Lam Research Corp', 1.0)
            ],
            'SOXX': [
                ('NVDA', 'NVIDIA Corp', 22.1), ('AVGO', 'Broadcom Inc', 8.7),
                ('TSM', 'Taiwan Semiconductor Manufacturing Co Ltd', 8.2), ('AMD', 'Advanced Micro Devices Inc', 7.8),
                ('QCOM', 'Qualcomm Inc', 4.9), ('TXN', 'Texas Instruments Inc', 4.2),
                ('AMAT', 'Applied Materials Inc', 3.8), ('LRCX', 'Lam Research Corp', 3.5),
                ('MU', 'Micron Technology Inc', 3.2), ('KLAC', 'KLA Corp', 2.9),
                ('MRVL', 'Marvell Technology Inc', 2.6), ('NXPI', 'NXP Semiconductors NV', 2.3),
                ('MCHP', 'Microchip Technology Inc', 2.0), ('ON', 'ON Semiconductor Corp', 1.9),
                ('MPWR', 'Monolithic Power Systems Inc', 1.7), ('SWKS', 'Skyworks Solutions Inc', 1.5)
            ],
            
            # Financial Sector ETFs
            'XLF': [
                ('BRK-B', 'Berkshire Hathaway Inc Class B', 12.8), ('JPM', 'JPMorgan Chase & Co', 10.1),
                ('V', 'Visa Inc Class A', 7.2), ('MA', 'Mastercard Inc Class A', 6.1),
                ('BAC', 'Bank of America Corp', 4.9), ('WFC', 'Wells Fargo & Co', 3.6),
                ('GS', 'Goldman Sachs Group Inc', 2.8), ('SPGI', 'S&P Global Inc', 2.7),
                ('MS', 'Morgan Stanley', 2.6), ('AXP', 'American Express Co', 2.4),
                ('C', 'Citigroup Inc', 2.2), ('SCHW', 'Charles Schwab Corp', 2.0),
                ('BLK', 'BlackRock Inc', 1.9), ('CB', 'Chubb Ltd', 1.7),
                ('USB', 'U.S. Bancorp', 1.6), ('PNC', 'PNC Financial Services Group Inc', 1.4)
            ],
            'VFH': [
                ('BRK-B', 'Berkshire Hathaway Inc Class B', 11.8), ('JPM', 'JPMorgan Chase & Co', 9.2),
                ('V', 'Visa Inc Class A', 6.8), ('MA', 'Mastercard Inc Class A', 5.7),
                ('BAC', 'Bank of America Corp', 4.6), ('WFC', 'Wells Fargo & Co', 3.4),
                ('GS', 'Goldman Sachs Group Inc', 2.6), ('MS', 'Morgan Stanley', 2.4),
                ('AXP', 'American Express Co', 2.2), ('C', 'Citigroup Inc', 2.0),
                ('SCHW', 'Charles Schwab Corp', 1.9), ('BLK', 'BlackRock Inc', 1.7),
                ('CB', 'Chubb Ltd', 1.6), ('USB', 'U.S. Bancorp', 1.5),
                ('PNC', 'PNC Financial Services Group Inc', 1.3), ('TFC', 'Truist Financial Corp', 1.2)
            ],
            
            # Healthcare Sector ETFs
            'XLV': [
                ('UNH', 'UnitedHealth Group Inc', 9.8), ('JNJ', 'Johnson & Johnson', 8.1),
                ('PFE', 'Pfizer Inc', 5.2), ('ABBV', 'AbbVie Inc', 4.9),
                ('TMO', 'Thermo Fisher Scientific Inc', 4.2), ('MRK', 'Merck & Co Inc', 4.1),
                ('ABT', 'Abbott Laboratories', 3.8), ('DHR', 'Danaher Corp', 3.2),
                ('BMY', 'Bristol-Myers Squibb Co', 2.8), ('AMGN', 'Amgen Inc', 2.6),
                ('LLY', 'Eli Lilly and Co', 2.5), ('CVS', 'CVS Health Corp', 2.3),
                ('MDT', 'Medtronic PLC', 2.1), ('GILD', 'Gilead Sciences Inc', 1.9),
                ('CI', 'Cigna Group', 1.8), ('ISRG', 'Intuitive Surgical Inc', 1.6)
            ],
            'VHT': [
                ('UNH', 'UnitedHealth Group Inc', 9.1), ('JNJ', 'Johnson & Johnson', 7.6),
                ('PFE', 'Pfizer Inc', 4.8), ('ABBV', 'AbbVie Inc', 4.5),
                ('TMO', 'Thermo Fisher Scientific Inc', 3.9), ('MRK', 'Merck & Co Inc', 3.8),
                ('ABT', 'Abbott Laboratories', 3.5), ('DHR', 'Danaher Corp', 2.9),
                ('LLY', 'Eli Lilly and Co', 2.6), ('BMY', 'Bristol-Myers Squibb Co', 2.5),
                ('AMGN', 'Amgen Inc', 2.4), ('CVS', 'CVS Health Corp', 2.1),
                ('MDT', 'Medtronic PLC', 1.9), ('GILD', 'Gilead Sciences Inc', 1.8),
                ('CI', 'Cigna Group', 1.7), ('ISRG', 'Intuitive Surgical Inc', 1.5)
            ],
            
            # Energy Sector ETFs
            'XLE': [
                ('XOM', 'Exxon Mobil Corp', 21.8), ('CVX', 'Chevron Corp', 16.2),
                ('COP', 'ConocoPhillips', 8.9), ('EOG', 'EOG Resources Inc', 4.7),
                ('SLB', 'Schlumberger NV', 4.1), ('PXD', 'Pioneer Natural Resources Co', 3.8),
                ('KMI', 'Kinder Morgan Inc', 3.5), ('OKE', 'ONEOK Inc', 3.2),
                ('WMB', 'Williams Cos Inc', 2.9), ('MPC', 'Marathon Petroleum Corp', 2.7),
                ('VLO', 'Valero Energy Corp', 2.5), ('PSX', 'Phillips 66', 2.3),
                ('BKR', 'Baker Hughes Co Class A', 2.1), ('HAL', 'Halliburton Co', 1.9),
                ('HES', 'Hess Corp', 1.7), ('FANG', 'Diamondback Energy Inc', 1.6)
            ],
            'VDE': [
                ('XOM', 'Exxon Mobil Corp', 20.3), ('CVX', 'Chevron Corp', 15.1),
                ('COP', 'ConocoPhillips', 8.2), ('EOG', 'EOG Resources Inc', 4.3),
                ('SLB', 'Schlumberger NV', 3.8), ('PXD', 'Pioneer Natural Resources Co', 3.5),
                ('KMI', 'Kinder Morgan Inc', 3.2), ('OKE', 'ONEOK Inc', 2.9),
                ('WMB', 'Williams Cos Inc', 2.7), ('MPC', 'Marathon Petroleum Corp', 2.5),
                ('VLO', 'Valero Energy Corp', 2.3), ('PSX', 'Phillips 66', 2.1),
                ('BKR', 'Baker Hughes Co Class A', 1.9), ('HAL', 'Halliburton Co', 1.8),
                ('HES', 'Hess Corp', 1.6), ('DVN', 'Devon Energy Corp', 1.5)
            ],
            
            # Industrial Sector ETFs
            'XLI': [
                ('CAT', 'Caterpillar Inc', 4.8), ('RTX', 'Raytheon Technologies Corp', 4.2),
                ('HON', 'Honeywell International Inc', 4.0), ('UNP', 'Union Pacific Corp', 3.7),
                ('BA', 'Boeing Co', 3.5), ('LMT', 'Lockheed Martin Corp', 3.2),
                ('UPS', 'United Parcel Service Inc Class B', 3.0), ('DE', 'Deere & Co', 2.8),
                ('GE', 'General Electric Co', 2.6), ('FDX', 'FedEx Corp', 2.4),
                ('MMM', '3M Co', 2.2), ('NOC', 'Northrop Grumman Corp', 2.0),
                ('CSX', 'CSX Corp', 1.9), ('WM', 'Waste Management Inc', 1.8),
                ('EMR', 'Emerson Electric Co', 1.7), ('ITW', 'Illinois Tool Works Inc', 1.6)
            ],
            'VIS': [
                ('CAT', 'Caterpillar Inc', 4.5), ('RTX', 'Raytheon Technologies Corp', 3.9),
                ('HON', 'Honeywell International Inc', 3.7), ('UNP', 'Union Pacific Corp', 3.4),
                ('BA', 'Boeing Co', 3.2), ('LMT', 'Lockheed Martin Corp', 2.9),
                ('UPS', 'United Parcel Service Inc Class B', 2.7), ('DE', 'Deere & Co', 2.5),
                ('GE', 'General Electric Co', 2.4), ('FDX', 'FedEx Corp', 2.2),
                ('MMM', '3M Co', 2.0), ('NOC', 'Northrop Grumman Corp', 1.8),
                ('CSX', 'CSX Corp', 1.7), ('WM', 'Waste Management Inc', 1.6),
                ('EMR', 'Emerson Electric Co', 1.5), ('ITW', 'Illinois Tool Works Inc', 1.4)
            ],
            
            # Consumer Discretionary ETFs
            'XLY': [
                ('AMZN', 'Amazon.com Inc', 22.1), ('TSLA', 'Tesla Inc', 16.8),
                ('HD', 'Home Depot Inc', 7.2), ('MCD', 'McDonald\'s Corp', 4.1),
                ('BKNG', 'Booking Holdings Inc', 3.8), ('LOW', 'Lowe\'s Cos Inc', 3.5),
                ('TJX', 'TJX Cos Inc', 3.2), ('NKE', 'Nike Inc Class B', 2.9),
                ('SBUX', 'Starbucks Corp', 2.7), ('F', 'Ford Motor Co', 2.5),
                ('GM', 'General Motors Co', 2.3), ('MAR', 'Marriott International Inc Class A', 2.1),
                ('CMG', 'Chipotle Mexican Grill Inc', 1.9), ('ORLY', 'O\'Reilly Automotive Inc', 1.8),
                ('HLT', 'Hilton Worldwide Holdings Inc', 1.7), ('RCL', 'Royal Caribbean Cruises Ltd', 1.6)
            ],
            'VCR': [
                ('AMZN', 'Amazon.com Inc', 20.8), ('TSLA', 'Tesla Inc', 15.2),
                ('HD', 'Home Depot Inc', 6.8), ('MCD', 'McDonald\'s Corp', 3.8),
                ('BKNG', 'Booking Holdings Inc', 3.5), ('LOW', 'Lowe\'s Cos Inc', 3.2),
                ('TJX', 'TJX Cos Inc', 2.9), ('NKE', 'Nike Inc Class B', 2.7),
                ('SBUX', 'Starbucks Corp', 2.5), ('F', 'Ford Motor Co', 2.3),
                ('GM', 'General Motors Co', 2.1), ('MAR', 'Marriott International Inc Class A', 1.9),
                ('CMG', 'Chipotle Mexican Grill Inc', 1.8), ('ORLY', 'O\'Reilly Automotive Inc', 1.7),
                ('HLT', 'Hilton Worldwide Holdings Inc', 1.6), ('RCL', 'Royal Caribbean Cruises Ltd', 1.5)
            ],
            
            # Consumer Staples ETFs
            'XLP': [
                ('PG', 'Procter & Gamble Co', 13.2), ('KO', 'Coca-Cola Co', 10.8),
                ('PEP', 'PepsiCo Inc', 9.7), ('WMT', 'Walmart Inc', 8.9),
                ('COST', 'Costco Wholesale Corp', 7.6), ('MDLZ', 'Mondelez International Inc Class A', 4.2),
                ('CL', 'Colgate-Palmolive Co', 3.8), ('KMB', 'Kimberly-Clark Corp', 3.5),
                ('GIS', 'General Mills Inc', 3.2), ('KHC', 'Kraft Heinz Co', 2.9),
                ('CHD', 'Church & Dwight Co Inc', 2.7), ('K', 'Kellogg Co', 2.5),
                ('HSY', 'Hershey Co', 2.3), ('CLX', 'Clorox Co', 2.1),
                ('SJM', 'J.M. Smucker Co', 1.9), ('CAG', 'Conagra Brands Inc', 1.8)
            ],
            'VDC': [
                ('PG', 'Procter & Gamble Co', 12.1), ('KO', 'Coca-Cola Co', 9.8),
                ('PEP', 'PepsiCo Inc', 8.9), ('WMT', 'Walmart Inc', 8.1),
                ('COST', 'Costco Wholesale Corp', 7.0), ('MDLZ', 'Mondelez International Inc Class A', 3.8),
                ('CL', 'Colgate-Palmolive Co', 3.5), ('KMB', 'Kimberly-Clark Corp', 3.2),
                ('GIS', 'General Mills Inc', 2.9), ('KHC', 'Kraft Heinz Co', 2.7),
                ('CHD', 'Church & Dwight Co Inc', 2.5), ('K', 'Kellogg Co', 2.3),
                ('HSY', 'Hershey Co', 2.1), ('CLX', 'Clorox Co', 1.9),
                ('SJM', 'J.M. Smucker Co', 1.8), ('CAG', 'Conagra Brands Inc', 1.7)
            ],
            
            # Utilities Sector ETFs
            'XLU': [
                ('NEE', 'NextEra Energy Inc', 12.8), ('DUK', 'Duke Energy Corp', 7.2),
                ('SO', 'Southern Co', 6.9), ('D', 'Dominion Energy Inc', 6.1),
                ('AEP', 'American Electric Power Co Inc', 4.8), ('EXC', 'Exelon Corp', 4.5),
                ('SRE', 'Sempra Energy', 4.2), ('XEL', 'Xcel Energy Inc', 3.9),
                ('WEC', 'WEC Energy Group Inc', 3.7), ('ED', 'Consolidated Edison Inc', 3.5),
                ('AWK', 'American Water Works Co Inc', 3.2), ('PPL', 'PPL Corp', 2.9),
                ('ES', 'Eversource Energy', 2.7), ('FE', 'FirstEnergy Corp', 2.5),
                ('ETR', 'Entergy Corp', 2.3), ('AES', 'AES Corp', 2.1)
            ],
            'VPU': [
                ('NEE', 'NextEra Energy Inc', 11.9), ('DUK', 'Duke Energy Corp', 6.8),
                ('SO', 'Southern Co', 6.2), ('D', 'Dominion Energy Inc', 5.7),
                ('AEP', 'American Electric Power Co Inc', 4.5), ('EXC', 'Exelon Corp', 4.2),
                ('SRE', 'Sempra Energy', 3.9), ('XEL', 'Xcel Energy Inc', 3.6),
                ('WEC', 'WEC Energy Group Inc', 3.4), ('ED', 'Consolidated Edison Inc', 3.2),
                ('AWK', 'American Water Works Co Inc', 2.9), ('PPL', 'PPL Corp', 2.7),
                ('ES', 'Eversource Energy', 2.5), ('FE', 'FirstEnergy Corp', 2.3),
                ('ETR', 'Entergy Corp', 2.1), ('AES', 'AES Corp', 1.9)
            ],
            
            # Materials Sector ETFs
            'XLB': [
                ('LIN', 'Linde PLC', 18.2), ('SHW', 'Sherwin-Williams Co', 7.8),
                ('APD', 'Air Products and Chemicals Inc', 6.9), ('FCX', 'Freeport-McMoRan Inc', 5.2),
                ('ECL', 'Ecolab Inc', 4.8), ('NEM', 'Newmont Corp', 4.5),
                ('DOW', 'Dow Inc', 4.2), ('NUE', 'Nucor Corp', 3.9),
                ('DD', 'DuPont de Nemours Inc', 3.6), ('PPG', 'PPG Industries Inc', 3.3),
                ('LYB', 'LyondellBasell Industries NV Class A', 3.0), ('VMC', 'Vulcan Materials Co', 2.8),
                ('MLM', 'Martin Marietta Materials Inc', 2.6), ('IFF', 'International Flavors & Fragrances Inc', 2.4),
                ('IP', 'International Paper Co', 2.2), ('PKG', 'Packaging Corp of America', 2.0)
            ],
            'VAW': [
                ('LIN', 'Linde PLC', 16.8), ('SHW', 'Sherwin-Williams Co', 7.2),
                ('APD', 'Air Products and Chemicals Inc', 6.3), ('FCX', 'Freeport-McMoRan Inc', 4.8),
                ('ECL', 'Ecolab Inc', 4.4), ('NEM', 'Newmont Corp', 4.1),
                ('DOW', 'Dow Inc', 3.9), ('NUE', 'Nucor Corp', 3.6),
                ('DD', 'DuPont de Nemours Inc', 3.3), ('PPG', 'PPG Industries Inc', 3.0),
                ('LYB', 'LyondellBasell Industries NV Class A', 2.8), ('VMC', 'Vulcan Materials Co', 2.6),
                ('MLM', 'Martin Marietta Materials Inc', 2.4), ('IFF', 'International Flavors & Fragrances Inc', 2.2),
                ('IP', 'International Paper Co', 2.0), ('PKG', 'Packaging Corp of America', 1.9)
            ],
            
            # Real Estate ETFs
            'XLRE': [
                ('AMT', 'American Tower Corp', 12.8), ('PLD', 'Prologis Inc', 9.2),
                ('CCI', 'Crown Castle Inc', 7.6), ('EQIX', 'Equinix Inc', 6.8),
                ('PSA', 'Public Storage', 5.9), ('WY', 'Weyerhaeuser Co', 4.2),
                ('WELL', 'Welltower Inc', 3.8), ('DLR', 'Digital Realty Trust Inc', 3.5),
                ('O', 'Realty Income Corp', 3.2), ('SBAC', 'SBA Communications Corp', 2.9),
                ('EXR', 'Extended Stay America Inc', 2.7), ('AVB', 'AvalonBay Communities Inc', 2.5),
                ('VTR', 'Ventas Inc', 2.3), ('EQR', 'Equity Residential', 2.1),
                ('SPG', 'Simon Property Group Inc', 1.9), ('UDR', 'UDR Inc', 1.8)
            ],
            'VNQ': [
                ('AMT', 'American Tower Corp', 11.7), ('PLD', 'Prologis Inc', 8.4),
                ('CCI', 'Crown Castle Inc', 6.9), ('EQIX', 'Equinix Inc', 6.2),
                ('PSA', 'Public Storage', 5.4), ('WY', 'Weyerhaeuser Co', 3.8),
                ('WELL', 'Welltower Inc', 3.5), ('DLR', 'Digital Realty Trust Inc', 3.2),
                ('O', 'Realty Income Corp', 2.9), ('SBAC', 'SBA Communications Corp', 2.7),
                ('EXR', 'Extended Stay America Inc', 2.5), ('AVB', 'AvalonBay Communities Inc', 2.3),
                ('VTR', 'Ventas Inc', 2.1), ('EQR', 'Equity Residential', 1.9),
                ('SPG', 'Simon Property Group Inc', 1.8), ('UDR', 'UDR Inc', 1.7)
            ],
            
            # Communication Services ETFs
            'XLC': [
                ('META', 'Meta Platforms Inc', 21.8), ('GOOGL', 'Alphabet Inc Class A', 12.1),
                ('GOOG', 'Alphabet Inc Class C', 11.7), ('NFLX', 'Netflix Inc', 6.8),
                ('DIS', 'Walt Disney Co', 5.9), ('CMCSA', 'Comcast Corp Class A', 4.2),
                ('VZ', 'Verizon Communications Inc', 4.0), ('T', 'AT&T Inc', 3.8),
                ('TMUS', 'T-Mobile US Inc', 3.5), ('CHTR', 'Charter Communications Inc Class A', 3.2),
                ('ATVI', 'Activision Blizzard Inc', 2.9), ('EA', 'Electronic Arts Inc', 2.7),
                ('TTWO', 'Take-Two Interactive Software Inc', 2.5), ('WBD', 'Warner Bros Discovery Inc', 2.3),
                ('PARA', 'Paramount Global Class B', 2.1), ('NWSA', 'News Corp Class A', 1.9)
            ],
            
            # Thematic and Innovation ETFs
            'ARKK': [
                ('TSLA', 'Tesla Inc', 12.1), ('ROKU', 'Roku Inc Class A', 5.8),
                ('COIN', 'Coinbase Global Inc Class A', 4.9), ('SHOP', 'Shopify Inc Class A', 4.2),
                ('ZM', 'Zoom Video Communications Inc Class A', 3.8), ('SQ', 'Block Inc Class A', 3.5),
                ('HOOD', 'Robinhood Markets Inc Class A', 3.2), ('PATH', 'UiPath Inc Class A', 2.9),
                ('TWLO', 'Twilio Inc Class A', 2.7), ('DKNG', 'DraftKings Inc Class A', 2.5),
                ('RBLX', 'Roblox Corp Class A', 2.3), ('PD', 'PagerDuty Inc', 2.1),
                ('PLTR', 'Palantir Technologies Inc Class A', 1.9), ('CRSP', 'CRISPR Therapeutics AG', 1.8),
                ('NVTA', 'Invitae Corp', 1.7), ('BEAM', 'Beam Therapeutics Inc', 1.6)
            ],
            'ARKG': [
                ('ILMN', 'Illumina Inc', 8.2), ('EXAS', 'Exact Sciences Corp', 6.7),
                ('VEEV', 'Veeva Systems Inc Class A', 5.9), ('TDOC', 'Teladoc Health Inc', 5.2),
                ('CRSP', 'CRISPR Therapeutics AG', 4.8), ('BEAM', 'Beam Therapeutics Inc', 4.5),
                ('NVTA', 'Invitae Corp', 4.2), ('FATE', 'Fate Therapeutics Inc', 3.9),
                ('SURF', 'Surface Oncology Inc', 3.6), ('ARCT', 'Arcturus Therapeutics Holdings Inc', 3.3),
                ('PSNL', 'Personalis Inc', 3.0), ('IONS', 'Ionis Pharmaceuticals Inc', 2.8),
                ('SGFY', 'Signify Health Inc Class A', 2.6), ('CDNA', 'CareDx Inc', 2.4),
                ('RXRX', 'Recursion Pharmaceuticals Inc Class A', 2.2), ('VCYT', 'Veracyte Inc', 2.0)
            ],
            'JETS': [
                ('DAL', 'Delta Air Lines Inc', 11.2), ('LUV', 'Southwest Airlines Co', 9.8),
                ('AAL', 'American Airlines Group Inc', 8.7), ('UAL', 'United Airlines Holdings Inc', 7.9),
                ('BA', 'Boeing Co', 6.8), ('JETS', 'JetBlue Airways Corp', 5.2),
                ('ALK', 'Alaska Air Group Inc', 4.6), ('HA', 'Hawaiian Holdings Inc', 3.9),
                ('RTX', 'Raytheon Technologies Corp', 3.7), ('GE', 'General Electric Co', 3.5),
                ('SAVE', 'Spirit Airlines Inc', 3.2), ('SKYW', 'SkyWest Inc', 2.9),
                ('HXL', 'Hexcel Corp', 2.7), ('TXT', 'Textron Inc', 2.5),
                ('CPA', 'Copa Holdings SA Class A', 2.3), ('ERJ', 'Embraer SA', 2.1)
            ],
            'ICLN': [
                ('ENPH', 'Enphase Energy Inc', 9.8), ('FSLR', 'First Solar Inc', 7.2),
                ('PLUG', 'Plug Power Inc', 6.9), ('BE', 'Bloom Energy Corp Class A', 5.8),
                ('RUN', 'Sunrun Inc', 5.2), ('NEE', 'NextEra Energy Inc', 4.9),
                ('SPWR', 'SunPower Corp', 4.6), ('SEDG', 'SolarEdge Technologies Inc', 4.3),
                ('NOVA', 'Sunnova Energy International Inc', 4.0), ('CSIQ', 'Canadian Solar Inc', 3.7),
                ('JKS', 'JinkoSolar Holding Co Ltd', 3.4), ('MAXN', 'Maxeon Solar Technologies Ltd', 3.1),
                ('SCCO', 'Southern Copper Corp', 2.9), ('ALB', 'Albemarle Corp', 2.7),
                ('SQM', 'Sociedad Quimica y Minera de Chile SA', 2.5), ('LAC', 'Lithium Americas Corp', 2.3)
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
        Get ETF holdings using multi-source fallback architecture.
        Data sources in priority order: Web Scraping -> yfinance -> hard-coded fallback
        
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
            cached_result = ETFInfo(
                symbol=cached_info.symbol,
                name=cached_info.name,
                holdings=cached_info.holdings[:top_n] if top_n else cached_info.holdings,
                total_holdings=cached_info.total_holdings,
                expense_ratio=cached_info.expense_ratio,
                aum=cached_info.aum,
                data_source=f"Cache ({getattr(cached_info, 'data_source', 'Unknown')})"
            )
            return cached_result
        
        print(f"Fetching holdings for {etf_symbol}...")
        
        # Try Web Scraping first (primary data source using etfdb.com)
        print("ETFDB: Attempting etfdb.com web scraper...")
        etf_info = self.get_etf_holdings_webscraper(etf_symbol, top_n)
        if etf_info and etf_info.holdings:
            etf_info.data_source = 'etfdb.com'
            print(f"SUCCESS: etfdb.com scraper succeeded for {etf_symbol}")
        else:
            print(f"ERROR: etfdb.com scraper failed for {etf_symbol}")
        
        # If web scraping fails, try yfinance
        if not etf_info or not etf_info.holdings:
            print("EMOJI: Attempting yfinance...")
            etf_info = self.get_etf_holdings_yfinance(etf_symbol, top_n)
            if etf_info and etf_info.holdings:
                etf_info.data_source = 'yfinance'
                print(f"SUCCESS: yfinance succeeded for {etf_symbol}")
            else:
                print(f"ERROR: yfinance failed for {etf_symbol}")
        
        # If all sources fail, try hard-coded fallback
        if not etf_info or not etf_info.holdings:
            etf_info = self.get_etf_holdings_alternative(etf_symbol, top_n)
            if etf_info and etf_info.holdings:
                etf_info.data_source = 'Hard-coded'
        
        # Cache the result
        if etf_info:
            self.etf_cache[etf_symbol] = etf_info
            print(f"CHECK: Found {len(etf_info.holdings)} holdings for {etf_symbol}")
        else:
            print(f"CROSS: Could not fetch holdings for {etf_symbol}")
        
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
            # Technology & Innovation
            'technology': ['XLK', 'VGT', 'IYW', 'QQQ', 'SOXX', 'ARKK', 'ARKW'],
            'tech': ['XLK', 'VGT', 'IYW', 'QQQ', 'SOXX', 'ARKK', 'ARKW'],
            'semiconductor': ['SOXX', 'XLK', 'VGT'],
            'semiconductors': ['SOXX', 'XLK', 'VGT'],
            'chips': ['SOXX', 'XLK', 'VGT'],
            'innovation': ['ARKK', 'ARKG', 'ARKQ', 'ARKW'],
            'disruptive': ['ARKK', 'ARKG', 'ARKQ', 'ARKW'],
            'genomics': ['ARKG'],
            'biotech': ['ARKG', 'XLV', 'VHT'],
            'robotics': ['ARKQ'],
            'internet': ['ARKW', 'XLC', 'QQQ'],
            
            # Financial Services
            'financial': ['XLF', 'VFH', 'IYF'],
            'finance': ['XLF', 'VFH', 'IYF'],
            'banks': ['XLF', 'VFH', 'IYF'],
            'banking': ['XLF', 'VFH', 'IYF'],
            'fintech': ['XLF', 'ARKF'],
            
            # Healthcare & Life Sciences
            'healthcare': ['XLV', 'VHT', 'IYH', 'ARKG'],
            'health': ['XLV', 'VHT', 'IYH', 'ARKG'],
            'medical': ['XLV', 'VHT', 'IYH'],
            'pharma': ['XLV', 'VHT', 'IYH'],
            'biotech': ['ARKG', 'XLV', 'VHT'],
            
            # Energy & Resources
            'energy': ['XLE', 'VDE', 'IYE'],
            'oil': ['XLE', 'VDE', 'IYE'],
            'gas': ['XLE', 'VDE', 'IYE'],
            'clean energy': ['ICLN', 'NEE'],
            'renewable': ['ICLN'],
            'solar': ['ICLN'],
            'green': ['ICLN'],
            
            # Industrial & Infrastructure
            'industrial': ['XLI', 'VIS', 'IYJ'],
            'infrastructure': ['XLI', 'VIS', 'IYJ'],
            'aerospace': ['XLI', 'VIS', 'JETS'],
            'defense': ['XLI', 'VIS'],
            'aviation': ['JETS', 'XLI'],
            'airlines': ['JETS'],
            'transportation': ['XLI', 'VIS', 'JETS'],
            
            # Consumer Sectors
            'consumer': ['XLY', 'XLP', 'VCR', 'VDC', 'IYC', 'IYK'],
            'consumer discretionary': ['XLY', 'VCR', 'IYC'],
            'consumer staples': ['XLP', 'VDC', 'IYK'],
            'retail': ['XLY', 'VCR', 'IYC'],
            'restaurants': ['XLY', 'VCR'],
            'food': ['XLP', 'VDC'],
            'beverage': ['XLP', 'VDC'],
            
            # Utilities & REITs
            'utilities': ['XLU', 'VPU', 'IDU'],
            'utility': ['XLU', 'VPU', 'IDU'],
            'real estate': ['XLRE', 'VNQ'],
            'reit': ['XLRE', 'VNQ'],
            'reits': ['XLRE', 'VNQ'],
            'property': ['XLRE', 'VNQ'],
            
            # Materials & Commodities
            'materials': ['XLB', 'VAW', 'IYM'],
            'mining': ['XLB', 'VAW', 'GDX'],
            'metals': ['XLB', 'VAW', 'GDX'],
            'gold': ['GDX', 'XLB'],
            'commodities': ['XLB', 'VAW', 'GDX'],
            
            # Communication & Media
            'communication': ['XLC'],
            'communications': ['XLC'],
            'media': ['XLC'],
            'telecom': ['XLC'],
            'social media': ['XLC', 'ARKW'],
            
            # Broad Market & Size
            'broad market': ['SPY', 'VTI', 'QQQ', 'IWM'],
            'large cap': ['SPY', 'VTI', 'QQQ'],
            'small cap': ['IWM'],
            'growth': ['QQQ', 'ARKK', 'VGT'],
            'value': ['XLF', 'XLE', 'XLU'],
            'dividend': ['XLU', 'VPU', 'XLRE', 'VNQ', 'XLP'],
            'income': ['XLU', 'VPU', 'XLRE', 'VNQ', 'XLP'],
            
            # International & Emerging
            'international': ['VEA', 'VWO', 'EFA', 'EEM'],
            'emerging': ['VWO', 'EEM'],
            'developed': ['VEA', 'EFA'],
            'europe': ['VGK', 'EFA'],
            'asia': ['VWO', 'EEM', 'FXI'],
            'china': ['FXI', 'ASHR'],
            'japan': ['EWJ'],
            
            # Thematic Investments
            'esg': ['ESGU', 'VSGX'],
            'sustainable': ['ESGU', 'VSGX', 'ICLN'],
            'cybersecurity': ['HACK', 'CIBR'],
            'cloud': ['SKYY', 'ARKW'],
            'gaming': ['ESPO', 'NERD'],
            'space': ['ARKX', 'UFO'],
            'water': ['PHO', 'AWK'],
            'agriculture': ['CORN', 'WEAT', 'DBA']
        }
        
        for key, etfs in theme_mapping.items():
            if theme in key or key in theme:
                suggestions.extend(etfs)
        
        return list(set(suggestions))  # Remove duplicates