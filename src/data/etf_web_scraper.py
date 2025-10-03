"""
ETF Web Scraper using Selenium

Advanced web scraping for ETF holdings from etf.com with dynamic dropdown handling.
Fully XPath-based for maximum reliability and findability.
"""

import time
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from selenium import webdriver
from selenium import __version__ as selenium_version
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
import warnings
warnings.filterwarnings('ignore')

# Import data types - handle relative vs absolute imports
try:
    from .etf_data_types import ETFInfo, ETFHolding
except ImportError:
    try:
        from etf_data_types import ETFInfo, ETFHolding
    except ImportError:
        # If neither works, we'll define minimal fallback classes
        from dataclasses import dataclass
        from typing import List, Optional
        
        @dataclass
        class ETFHolding:
            symbol: str
            name: str
            weight: float
            shares: Optional[int] = None
            market_value: Optional[float] = None
            sector: Optional[str] = None
        
        @dataclass
        class ETFInfo:
            symbol: str
            name: str
            holdings: List[ETFHolding]
            total_holdings: int = 0


@dataclass
class ScrapedHolding:
    """Individual holding scraped from ETF website."""
    symbol: str
    name: str
    weight: float
    shares: Optional[int] = None
    market_value: Optional[float] = None
    sector: Optional[str] = None
    
    
@dataclass
class ScrapedETFInfo:
    """ETF information scraped from website."""
    symbol: str
    name: str
    holdings: List[ScrapedHolding]
    total_holdings: int
    expense_ratio: Optional[float] = None
    aum: Optional[float] = None
    scraped_from: str = "etf.com"


class ETFWebScraper:
    """Advanced ETF holdings web scraper using Selenium."""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """Initialize the web scraper.
        
        Args:
            headless: Run browser in headless mode
            timeout: Maximum wait time for elements (seconds)
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.wait = None
        
        # XPath selectors for etfdb.com - much simpler!
        self.xpaths = {
            # Holdings table - directly accessible, no navigation needed
            'holdings_table_body': "//*[@id='etf-holdings']/tbody",
            'table_rows': "//*[@id='etf-holdings']/tbody/tr",
            
            # Cell data (relative to row) - etfdb.com format:
            # Column 1: Symbol
            # Column 2: Holding (company name) 
            # Column 3: % Assets
            'symbol_cell': ".//td[1]",        # First column: Symbol
            'company_cell': ".//td[2]",       # Second column: Company name
            'weight_cell': ".//td[3]"         # Third column: % Assets
        }
        
        print(f"DEBUG: ETF Web Scraper initialized (Selenium {selenium_version})")
    
    def company_name_to_ticker(self, company_name: str) -> str:
        """Convert company name to ticker symbol.
        
        This maps company names from etf.com to their ticker symbols.
        Uses known mappings and heuristics as fallback.
        
        Args:
            company_name: Full company name from etf.com
            
        Returns:
            str: Ticker symbol (best guess)
        """
        name = company_name.strip()
        
        # Known mappings for medical device companies (from XHE holdings)
        known_mappings = {
            "Abbott Laboratories": "ABT",
            "Medtronic Plc": "MDT", 
            "Boston Scientific Corporation": "BSX",
            "Stryker Corporation": "SYK",
            "Becton, Dickinson and Company": "BDX",
            "Baxter International Inc.": "BAX",
            "Edwards Lifesciences Corporation": "EW",
            "Intuitive Surgical, Inc.": "ISRG",
            "Zimmer Biomet Holdings, Inc.": "ZBH",
            "DexCom, Inc.": "DXCM",
            "ResMed Inc.": "RMD",
            "IDEXX Laboratories, Inc.": "IDXX",
            "Hologic, Inc.": "HOLX",
            "Align Technology, Inc.": "ALGN",
            "Teleflex Incorporated": "TFX",
            "Cooper Companies, Inc.": "COO",
            "Insulet Corporation": "PODD",
            "Tandem Diabetes Care, Inc.": "TNDM",
            "GE Healthcare Technologies Inc.": "GEHC",
            "STERIS plc": "STE",
            "Masimo Corporation": "MASI",
            "NovoCure Ltd.": "NVCR",
            "TransMedics Group, Inc.": "TMDX",
            "ICU Medical, Inc.": "ICUI",
            "Penumbra, Inc.": "PEN"
        }
        
        # Exact match
        if name in known_mappings:
            return known_mappings[name]
        
        # Try without suffixes
        for suffix in [" Inc.", " Corporation", " Corp.", " Plc", " Ltd.", " Company", " Co."]:
            base_name = name.replace(suffix, "").strip()
            for mapped_name, ticker in known_mappings.items():
                if base_name.lower() == mapped_name.replace(suffix, "").strip().lower():
                    return ticker
        
        # Create ticker from name (heuristic)
        words = name.replace(",", "").split()
        if len(words) >= 2:
            # Use first letter of first two main words
            ticker = words[0][:2].upper() + words[1][:2].upper()
        else:
            ticker = words[0][:4].upper()
        
        return ticker[:5]  # Max 5 characters
    
    def setup_driver(self) -> bool:
        """Set up Chrome WebDriver with optimal settings.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # Performance and stability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")  # We'll enable if needed
            chrome_options.add_argument("--window-size=1920,1080")
            
            # User agent to avoid bot detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Install and setup ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(5)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            print("SUCCESS: Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to setup WebDriver: {e}")
            return False
    
    def find_element_by_xpaths(self, xpaths: List[str], timeout: int = None) -> Optional[object]:
        """Find element using multiple XPath options.
        
        Args:
            xpaths: List of XPath selectors to try
            timeout: Custom timeout (uses default if None)
            
        Returns:
            WebElement if found, None otherwise
        """
        if timeout is None:
            timeout = self.timeout
        
        for xpath in xpaths:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                print(f"SUCCESS: Found element with XPath: {xpath}")
                return element
            except TimeoutException:
                continue
            except Exception as e:
                print(f"WARNING: Error with XPath {xpath}: {e}")
                continue
        
        return None
    
    def click_element_by_xpaths(self, xpaths: List[str], timeout: int = None) -> bool:
        """Click element using multiple XPath options.
        
        Args:
            xpaths: List of XPath selectors to try
            timeout: Custom timeout (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        element = self.find_element_by_xpaths(xpaths, timeout)
        if element:
            try:
                # Try regular click
                element.click()
                return True
            except ElementClickInterceptedException:
                # Try JavaScript click if regular click fails
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e:
                    print(f"ERROR: JavaScript click failed: {e}")
                    
        return False
    
    def scrape_etf_holdings(self, etf_symbol: str, max_holdings: Optional[int] = None) -> Optional[ScrapedETFInfo]:
        """Scrape ETF holdings from etfdb.com.
        
        Args:
            etf_symbol: ETF symbol (e.g., 'VHT')
            max_holdings: Maximum number of holdings to return (up to 15 from etfdb.com)
            
        Returns:
            ScrapedETFInfo object or None if failed
        """
        etf_symbol = etf_symbol.upper().strip()
        url = f"https://etfdb.com/etf/{etf_symbol}/#holdings"
        
        print(f"WEB: Scraping holdings for {etf_symbol} from {url}")
        
        if not self.setup_driver():
            return None
        
        try:
            # Navigate to ETF holdings page on etfdb.com
            self.driver.get(url)
            time.sleep(5)  # Let page load completely
            
            print(f"PAGE: Loaded: {self.driver.title}")
            
            # Check for valid ETF page
            if "404" in self.driver.title or "Not Found" in self.driver.title or "Error" in self.driver.title:
                print(f"ERROR: ETF page not found for {etf_symbol}")
                return None
            
            # etfdb.com is much simpler - just find the holdings table directly!
            print("SIMPLE: Looking for holdings table...")
            holdings = []
            
            try:
                # Wait for the holdings table to load
                table_body = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, self.xpaths['holdings_table_body']))
                )
                print("SUCCESS: Found holdings table body")
                
                # Get all rows in the table
                rows = table_body.find_elements(By.XPATH, "./tr")
                print(f"FOUND: {len(rows)} holding rows in table")
                
                for i, row in enumerate(rows):
                    try:
                        # Extract data from each column
                        # Column 1: Symbol
                        symbol_cell = row.find_element(By.XPATH, self.xpaths['symbol_cell'])
                        symbol = symbol_cell.text.strip()
                        
                        # Column 2: Company name
                        company_cell = row.find_element(By.XPATH, self.xpaths['company_cell'])
                        company_name = company_cell.text.strip()
                        
                        # Column 3: % Assets
                        weight_cell = row.find_element(By.XPATH, self.xpaths['weight_cell'])
                        weight_text = weight_cell.text.strip()
                        
                        # Parse weight percentage
                        weight = 0.0
                        if weight_text and '%' in weight_text:
                            try:
                                weight = float(weight_text.replace('%', '').strip())
                            except ValueError:
                                print(f"WARNING: Could not parse weight '{weight_text}' for {symbol}")
                        
                        if symbol and company_name:
                            holding = ScrapedHolding(
                                symbol=symbol,
                                name=company_name,
                                weight=weight,
                                shares=None,  # Not available from etfdb.com
                                market_value=None  # Not available from etfdb.com
                            )
                            holdings.append(holding)
                            print(f"EXTRACTED: {symbol} - {company_name[:30]} ({weight:.2f}%)")
                            
                            # Respect max_holdings limit
                            if max_holdings and len(holdings) >= max_holdings:
                                break
                                
                    except Exception as e:
                        print(f"WARNING: Error parsing row {i+1}: {e}")
                        continue
                        
            except Exception as e:
                print(f"ERROR: Could not find or parse holdings table: {e}")
                return None
            
            # Create ETF info object
            if holdings:
                print(f"SUCCESS: Extracted {len(holdings)} holdings from etfdb.com")
                
                # Get ETF name from page title if possible
                etf_name = f"{etf_symbol} ETF"
                try:
                    title = self.driver.title
                    if title and etf_symbol in title:
                        etf_name = title.split('|')[0].strip()
                except:
                    pass
                
                etf_info = ScrapedETFInfo(
                    symbol=etf_symbol,
                    name=etf_name,
                    holdings=holdings,
                    total_holdings=len(holdings),
                    expense_ratio=None,  # Not easily available from etfdb.com
                    aum=None  # Not easily available from etfdb.com
                )
                
                return etf_info
            else:
                print("ERROR: No holdings found")
                return None
                
        except Exception as e:
            print(f"ERROR: Error scraping {etf_symbol}: {e}")
            return None
        
        finally:
            if self.driver:
                self.driver.quit()
                print("CLEANUP: Browser closed")
    
    def scrape_multiple_etfs(self, etf_symbols: List[str], max_holdings_per_etf: Optional[int] = None) -> Dict[str, ScrapedETFInfo]:
        """Scrape multiple ETFs in sequence.
        
        Args:
            etf_symbols: List of ETF symbols to scrape
            max_holdings_per_etf: Maximum holdings per ETF
            
        Returns:
            Dictionary mapping ETF symbols to ScrapedETFInfo objects
        """
        results = {}
        
        print(f"LAUNCH: Starting batch scrape of {len(etf_symbols)} ETFs...")
        
        for i, symbol in enumerate(etf_symbols, 1):
            print(f"\nDATA: [{i}/{len(etf_symbols)}] Scraping {symbol}...")
            
            etf_info = self.scrape_etf_holdings(symbol, max_holdings_per_etf)
            if etf_info:
                results[symbol] = etf_info
                print(f"SUCCESS: {symbol}: {len(etf_info.holdings)} holdings")
            else:
                print(f"ERROR: {symbol}: Failed to scrape")
            
            # Brief pause between requests to be respectful
            if i < len(etf_symbols):
                time.sleep(2)
        
        print(f"\nCOMPLETE: Batch scraping complete: {len(results)}/{len(etf_symbols)} successful")
        return results
    
    def convert_to_etf_holdings_format(self, scraped_info: ScrapedETFInfo) -> Optional['ETFInfo']:
        """Convert scraped data to standard ETFInfo format.
        
        Args:
            scraped_info: ScrapedETFInfo object
            
        Returns:
            ETFInfo object compatible with existing system
        """
        try:
            # Convert holdings
            holdings = []
            for scraped_holding in scraped_info.holdings:
                holding = ETFHolding(
                    symbol=scraped_holding.symbol,
                    name=scraped_holding.name,
                    weight=scraped_holding.weight,
                    shares=scraped_holding.shares
                )
                holdings.append(holding)
            
            # Create ETFInfo
            etf_info = ETFInfo(
                symbol=scraped_info.symbol,
                name=scraped_info.name,
                holdings=holdings,
                total_holdings=scraped_info.total_holdings,
                expense_ratio=scraped_info.expense_ratio,
                aum=scraped_info.aum
            )
            
            return etf_info
            
        except ImportError:
            print("WARNING: ETFHolding/ETFInfo classes not available for conversion")
            return None
    
    def get_etf_holdings(self, etf_symbol: str) -> Optional[List[Dict[str, any]]]:
        """
        Get ETF holdings in the expected format for the portfolio system.
        
        Args:
            etf_symbol: ETF ticker symbol
            
        Returns:
            List of holdings in dict format with 'symbol', 'name', 'weight' keys
        """
        scraped_info = self.scrape_etf_holdings(etf_symbol)
        
        if not scraped_info or not scraped_info.holdings:
            return None
            
        # Convert to expected format
        holdings = []
        for holding in scraped_info.holdings:
            holdings.append({
                'symbol': holding.symbol,
                'name': holding.name,
                'weight': holding.weight
            })
            
        return holdings
    
    def cleanup(self):
        """Clean up the web driver resources."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"WARNING: Error closing web driver: {e}")
            finally:
                self.driver = None
                self.wait = None


def test_scraper():
    """Test the ETF web scraper."""
    print("TEST: Testing ETF Web Scraper")
    print("=" * 50)
    
    scraper = ETFWebScraper(headless=False)  # Show browser for testing
    
    # Test with VHT (Healthcare ETF)
    etf_info = scraper.scrape_etf_holdings("VHT", max_holdings=10)
    
    if etf_info:
        print(f"\nSUCCESS: Successfully scraped {etf_info.symbol}:")
        print(f"   Name: {etf_info.name}")
        print(f"   Total Holdings: {etf_info.total_holdings}")
        print(f"   Top Holdings:")
        
        for i, holding in enumerate(etf_info.holdings[:5], 1):
            print(f"      {i}. {holding.symbol} ({holding.weight:.2f}%) - {holding.name}")
    else:
        print("ERROR: Scraping failed")


if __name__ == "__main__":
    test_scraper()