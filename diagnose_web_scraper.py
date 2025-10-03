#!/usr/bin/env python3
"""
Comprehensive ETF Web Scraper Diagnostic Tool

This script performs extensive testing and debugging of the ETF web scraper
to identify exactly what's going wrong with the scraping process.
"""

import sys
import os
import time
from datetime import datetime

# Add the src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Import web scraper
from data.etf_web_scraper import ETFWebScraper
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

class ETFScraperDiagnostic:
    """Comprehensive diagnostic tool for ETF web scraper."""
    
    def __init__(self):
        self.results = []
        
    def log(self, message, level="INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.results.append(log_entry)
        
    def test_basic_imports(self):
        """Test if all required imports work."""
        self.log("=" * 60, "HEADER")
        self.log("TESTING BASIC IMPORTS", "HEADER")
        self.log("=" * 60, "HEADER")
        
        try:
            from selenium import webdriver
            self.log("SUCCESS: Selenium imported")
        except ImportError as e:
            self.log(f"ERROR: Selenium import failed: {e}", "ERROR")
            return False
            
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            self.log("SUCCESS: WebDriver Manager imported")
        except ImportError as e:
            self.log(f"ERROR: WebDriver Manager import failed: {e}", "ERROR")
            return False
            
        try:
            from data.etf_web_scraper import ETFWebScraper
            self.log("SUCCESS: ETFWebScraper imported")
        except ImportError as e:
            self.log(f"ERROR: ETFWebScraper import failed: {e}", "ERROR")
            return False
            
        return True
        
    def test_chrome_driver_setup(self):
        """Test Chrome driver initialization."""
        self.log("=" * 60, "HEADER")
        self.log("TESTING CHROME DRIVER SETUP", "HEADER")
        self.log("=" * 60, "HEADER")
        
        try:
            # Test ChromeDriverManager
            driver_path = ChromeDriverManager().install()
            self.log(f"SUCCESS: Chrome driver downloaded to: {driver_path}")
            
            # Test Chrome options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            self.log("SUCCESS: Chrome options configured")
            
            # Test driver initialization
            driver = webdriver.Chrome(options=options)
            self.log("SUCCESS: Chrome driver initialized")
            
            # Test basic navigation
            driver.get("https://www.google.com")
            title = driver.title
            self.log(f"SUCCESS: Navigation test completed - Page title: {title}")
            
            driver.quit()
            self.log("SUCCESS: Chrome driver cleanup completed")
            return True
            
        except Exception as e:
            self.log(f"ERROR: Chrome driver setup failed: {e}", "ERROR")
            return False
            
    def test_etf_website_access(self, driver):
        """Test access to etf.com website."""
        self.log("=" * 60, "HEADER")
        self.log("TESTING ETF.COM WEBSITE ACCESS", "HEADER")
        self.log("=" * 60, "HEADER")
        
        test_urls = [
            "https://www.etf.com/SPY",  # Most popular ETF
            "https://www.etf.com/VTI",  # Another popular ETF
            "https://www.etf.com/XHE",  # Healthcare equipment ETF (from user tests)
        ]
        
        for url in test_urls:
            try:
                self.log(f"Testing URL: {url}")
                driver.get(url)
                time.sleep(3)  # Allow page to load
                
                # Check if page loaded successfully
                title = driver.title
                self.log(f"Page title: {title}")
                
                # Check for common blocking indicators
                if "captcha" in title.lower() or "blocked" in title.lower():
                    self.log("WARNING: Possible CAPTCHA or blocking detected", "WARNING")
                elif "404" in title or "not found" in title.lower():
                    self.log("WARNING: Page not found (404)", "WARNING")
                elif title == "":
                    self.log("WARNING: Empty page title", "WARNING")
                else:
                    self.log("SUCCESS: Page loaded successfully")
                    
                # Check page source for blocking indicators
                page_source = driver.page_source[:1000]  # First 1000 chars
                if "captcha" in page_source.lower():
                    self.log("WARNING: CAPTCHA detected in page source", "WARNING")
                elif "cloudflare" in page_source.lower():
                    self.log("WARNING: Cloudflare protection detected", "WARNING")
                elif len(page_source) < 100:
                    self.log("WARNING: Very short page source - possible blocking", "WARNING")
                else:
                    self.log("SUCCESS: Page source looks normal")
                    
            except Exception as e:
                self.log(f"ERROR: Failed to access {url}: {e}", "ERROR")
                
    def test_xpath_elements(self, driver, etf_symbol="SPY"):
        """Test XPath element finding on actual ETF page."""
        self.log("=" * 60, "HEADER")
        self.log(f"TESTING XPATH ELEMENTS FOR {etf_symbol}", "HEADER")
        self.log("=" * 60, "HEADER")
        
        url = f"https://www.etf.com/{etf_symbol}"
        
        try:
            driver.get(url)
            time.sleep(5)  # Allow page to fully load
            
            # Test all XPath selectors from the scraper
            scraper = ETFWebScraper()
            xpaths = scraper.xpaths
            
            # Test holdings menu button
            self.log("Testing holdings menu button...")
            holdings_button_found = False
            try:
                element = driver.find_element(By.XPATH, xpaths['holdings_menu_button'])
                self.log("SUCCESS: Holdings menu button found")
                holdings_button_found = True
            except NoSuchElementException:
                self.log("WARNING: Holdings menu button not found", "WARNING")
                
            # Test holdings tab
            self.log("Testing holdings tab...")
            try:
                element = driver.find_element(By.XPATH, xpaths['holdings_tab'])
                self.log("SUCCESS: Holdings tab found")
            except NoSuchElementException:
                self.log("WARNING: Holdings tab not found", "WARNING")
                
            # Test dropdown elements
            self.log("Testing dropdown elements...")
            dropdown_found = False
            for i, xpath in enumerate(xpaths['show_all_dropdown']):
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    self.log(f"SUCCESS: Dropdown found with XPath #{i+1}: {xpath[:100]}...")
                    dropdown_found = True
                    break
                except NoSuchElementException:
                    continue
                    
            if not dropdown_found:
                self.log("WARNING: No dropdown elements found", "WARNING")
                
            # Test table elements
            self.log("Testing table elements...")
            table_found = False
            for i, xpath in enumerate(xpaths['holdings_table']):
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    self.log(f"SUCCESS: Holdings table found with XPath #{i+1}: {xpath[:100]}...")
                    table_found = True
                    break
                except NoSuchElementException:
                    continue
                    
            if not table_found:
                self.log("WARNING: No table elements found", "WARNING")
                
            # Test table rows
            self.log("Testing table rows...")
            rows_found = False
            for i, xpath in enumerate(xpaths['table_rows']):
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        self.log(f"SUCCESS: Found {len(elements)} table rows with XPath #{i+1}")
                        rows_found = True
                        break
                except NoSuchElementException:
                    continue
                    
            if not rows_found:
                self.log("WARNING: No table rows found", "WARNING")
                
        except Exception as e:
            self.log(f"ERROR: XPath testing failed: {e}", "ERROR")
            
    def inspect_page_structure(self, driver, etf_symbol="SPY"):
        """Inspect the actual page structure to understand the HTML."""
        self.log("=" * 60, "HEADER")
        self.log(f"INSPECTING PAGE STRUCTURE FOR {etf_symbol}", "HEADER")
        self.log("=" * 60, "HEADER")
        
        url = f"https://www.etf.com/{etf_symbol}"
        
        try:
            driver.get(url)
            time.sleep(5)
            
            # Look for any tables
            tables = driver.find_elements(By.TAG_NAME, "table")
            self.log(f"Found {len(tables)} table elements on page")
            
            for i, table in enumerate(tables[:3]):  # Check first 3 tables
                try:
                    table_class = table.get_attribute("class")
                    table_id = table.get_attribute("id")
                    self.log(f"Table {i+1}: id='{table_id}', class='{table_class}'")
                    
                    # Check if this table has holdings-like content
                    table_text = table.text[:200]  # First 200 chars
                    if any(keyword in table_text.lower() for keyword in ['holding', 'symbol', 'weight', '%']):
                        self.log(f"  POTENTIAL HOLDINGS TABLE: {table_text[:100]}...")
                except Exception as e:
                    self.log(f"  Error inspecting table {i+1}: {e}")
                    
            # Look for dropdown/select elements
            selects = driver.find_elements(By.TAG_NAME, "select")
            self.log(f"Found {len(selects)} select elements on page")
            
            for i, select in enumerate(selects[:5]):  # Check first 5 selects
                try:
                    select_class = select.get_attribute("class")
                    select_id = select.get_attribute("id")
                    select_name = select.get_attribute("name")
                    options = select.find_elements(By.TAG_NAME, "option")
                    self.log(f"Select {i+1}: id='{select_id}', class='{select_class}', name='{select_name}', options={len(options)}")
                    
                    # Check option values
                    option_values = []
                    for option in options[:3]:  # First 3 options
                        option_values.append(option.get_attribute("value"))
                    self.log(f"  Option values: {option_values}")
                except Exception as e:
                    self.log(f"  Error inspecting select {i+1}: {e}")
                    
            # Look for divs that might contain holdings data
            divs_with_holdings = driver.find_elements(By.XPATH, "//div[contains(@class, 'holding') or contains(@id, 'holding') or contains(text(), 'Holdings')]")
            self.log(f"Found {len(divs_with_holdings)} divs related to holdings")
            
            # Look for any elements containing percentage signs (likely holdings weights)
            percentage_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
            self.log(f"Found {len(percentage_elements)} elements containing '%' symbol")
            
            if percentage_elements:
                for i, elem in enumerate(percentage_elements[:5]):
                    try:
                        text = elem.text.strip()
                        if text and len(text) < 50:  # Short text likely to be weights
                            self.log(f"  Percentage element {i+1}: '{text}'")
                    except Exception:
                        pass
                        
        except Exception as e:
            self.log(f"ERROR: Page structure inspection failed: {e}", "ERROR")
            
    def test_full_scraping_process(self, etf_symbol="SPY"):
        """Test the full scraping process step by step."""
        self.log("=" * 60, "HEADER")
        self.log(f"TESTING FULL SCRAPING PROCESS FOR {etf_symbol}", "HEADER")
        self.log("=" * 60, "HEADER")
        
        try:
            scraper = ETFWebScraper(headless=False)  # Use visible browser for debugging
            self.log("ETF Web Scraper initialized")
            
            # Test the actual scraping
            holdings = scraper.get_etf_holdings(etf_symbol)
            
            if holdings:
                self.log(f"SUCCESS: Retrieved {len(holdings)} holdings")
                for i, holding in enumerate(holdings[:5]):
                    self.log(f"  {i+1}. {holding.get('symbol', 'N/A')} - {holding.get('name', 'N/A')[:30]} ({holding.get('weight', 0):.2f}%)")
            else:
                self.log("ERROR: No holdings retrieved", "ERROR")
                
            scraper.cleanup()
            
        except Exception as e:
            self.log(f"ERROR: Full scraping test failed: {e}", "ERROR")
            
    def generate_recommendations(self):
        """Generate recommendations based on diagnostic results."""
        self.log("=" * 60, "HEADER")
        self.log("DIAGNOSTIC RECOMMENDATIONS", "HEADER")
        self.log("=" * 60, "HEADER")
        
        # Analyze results and provide recommendations
        error_count = sum(1 for result in self.results if "ERROR:" in result)
        warning_count = sum(1 for result in self.results if "WARNING:" in result)
        
        self.log(f"Total errors found: {error_count}")
        self.log(f"Total warnings found: {warning_count}")
        
        if error_count > 0:
            self.log("RECOMMENDATION: Focus on resolving errors first")
        elif warning_count > 0:
            self.log("RECOMMENDATION: Investigate warnings - they may indicate the root cause")
        else:
            self.log("RECOMMENDATION: All basic tests passed - issue may be with specific XPaths or timing")
            
        # Specific recommendations based on common issues
        if any("CAPTCHA" in result for result in self.results):
            self.log("RECOMMENDATION: Website is using CAPTCHA protection - consider:")
            self.log("  - Adding delays between requests")
            self.log("  - Using different user agent strings")
            self.log("  - Implementing CAPTCHA solving")
            
        if any("ChromeDriverManager" in result and "ERROR" in result for result in self.results):
            self.log("RECOMMENDATION: Chrome driver issues - try:")
            self.log("  - Manually installing ChromeDriver")
            self.log("  - Checking Chrome browser version compatibility")
            
        if any("XPath" in result and "not found" in result for result in self.results):
            self.log("RECOMMENDATION: XPath selectors may be outdated - consider:")
            self.log("  - Inspecting current page HTML structure")
            self.log("  - Updating XPath selectors")
            self.log("  - Using more generic selectors")
            
    def run_full_diagnostic(self):
        """Run the complete diagnostic suite."""
        self.log("Starting comprehensive ETF Web Scraper diagnostic...")
        self.log(f"Timestamp: {datetime.now()}")
        
        # Test 1: Basic imports
        if not self.test_basic_imports():
            self.log("CRITICAL: Basic imports failed - cannot continue", "ERROR")
            return
            
        # Test 2: Chrome driver setup
        if not self.test_chrome_driver_setup():
            self.log("CRITICAL: Chrome driver setup failed - cannot continue", "ERROR")
            return
            
        # Create driver for remaining tests
        try:
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            # Use headless=False for visual debugging
            # options.add_argument('--headless')
            
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            
            # Test 3: Website access
            self.test_etf_website_access(driver)
            
            # Test 4: XPath elements
            self.test_xpath_elements(driver)
            
            # Test 5: Page structure inspection
            self.inspect_page_structure(driver)
            
            driver.quit()
            
        except Exception as e:
            self.log(f"ERROR: Failed to create driver for detailed tests: {e}", "ERROR")
            
        # Test 6: Full scraping process (creates its own driver)
        self.test_full_scraping_process()
        
        # Generate recommendations
        self.generate_recommendations()
        
        self.log("=" * 60, "HEADER")
        self.log("DIAGNOSTIC COMPLETE", "HEADER")
        self.log("=" * 60, "HEADER")

def main():
    """Main function to run the diagnostic."""
    diagnostic = ETFScraperDiagnostic()
    diagnostic.run_full_diagnostic()

if __name__ == "__main__":
    main()