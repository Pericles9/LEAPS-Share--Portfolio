#!/usr/bin/env python3
"""
ETF.com Structure Analysis Tool
This script will analyze the structure of etf.com pages to help improve scraping
"""

import sys
import os
import time

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_etf_page_structure():
    """Analyze the structure of an ETF page on etf.com"""
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("🕷️ ANALYZING ETF.COM PAGE STRUCTURE")
        print("=" * 60)
        
        # Setup Chrome driver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to XHE page
        url = "https://www.etf.com/XHE"
        print(f"🌐 Loading: {url}")
        driver.get(url)
        time.sleep(3)
        
        print(f"📄 Page Title: {driver.title}")
        
        # Look for holdings-related elements
        print("\n🔍 SEARCHING FOR HOLDINGS ELEMENTS:")
        print("-" * 40)
        
        # 1. Look for holdings menu/button
        holdings_selectors = [
            "//a[contains(text(), 'Holdings')]",
            "//button[contains(text(), 'Holdings')]", 
            "//div[contains(text(), 'Holdings')]",
            "//*[@id='fp-menu-holdings']",  # Your provided XPath
            "//nav//a[contains(@href, 'holdings')]"
        ]
        
        for selector in holdings_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"✅ Found holdings element: {selector}")
                    for elem in elements[:3]:  # Show first 3
                        print(f"   Text: '{elem.text}' | Tag: {elem.tag_name} | Visible: {elem.is_displayed()}")
                else:
                    print(f"❌ Not found: {selector}")
            except Exception as e:
                print(f"⚠️ Error with {selector}: {e}")
        
        # 2. Click the holdings menu if found
        print(f"\n🖱️ ATTEMPTING TO CLICK HOLDINGS MENU:")
        print("-" * 40)
        
        try:
            holdings_button = driver.find_element(By.XPATH, "//*[@id='fp-menu-holdings']")
            if holdings_button:
                print("✅ Found holdings menu button")
                holdings_button.click()
                time.sleep(3)
                print("✅ Clicked holdings menu")
                
                # Look for dropdown after clicking
                print(f"\n🔍 SEARCHING FOR DROPDOWN AFTER CLICK:")
                print("-" * 40)
                
                dropdown_selectors = [
                    "//select",
                    "//div[contains(@class, 'dropdown')]",
                    "//div[contains(@class, 'select')]",
                    "/html/body/div[2]/div/div/main/div[2]/div[2]/main[4]/div[1]/div[1]/div[1]/div/div/div[7]",  # Your XPath
                    "//div[contains(text(), 'Show')]",
                    "//div[contains(text(), 'All')]"
                ]
                
                for selector in dropdown_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            print(f"✅ Found dropdown element: {selector}")
                            for elem in elements[:3]:
                                print(f"   Text: '{elem.text}' | Tag: {elem.tag_name} | Class: {elem.get_attribute('class')}")
                                # Get child elements
                                children = elem.find_elements(By.XPATH, "./*")
                                if children:
                                    print(f"   Children: {len(children)}")
                                    for child in children[:5]:
                                        print(f"     - {child.tag_name}: '{child.text}'")
                        else:
                            print(f"❌ Not found: {selector}")
                    except Exception as e:
                        print(f"⚠️ Error with {selector}: {e}")
                
                # Look for holdings table
                print(f"\n🔍 SEARCHING FOR HOLDINGS TABLE:")
                print("-" * 40)
                
                table_selectors = [
                    "//table",
                    "//div[contains(@class, 'table')]",
                    "//div[contains(@class, 'holdings')]",
                    "/html/body/div[2]/div/div/main/div[2]/div[2]/main[4]/div[1]/div[1]/div[1]/div/div/div[9]/div[2]/div[4]",  # Your XPath
                    "//tr[contains(@class, 'holding')]",
                    "//div[contains(@class, 'row')]//div[contains(text(), '%')]"
                ]
                
                for selector in table_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            print(f"✅ Found table element: {selector}")
                            for elem in elements[:2]:  # Show first 2
                                print(f"   Text preview: '{elem.text[:100]}...'")
                                print(f"   Tag: {elem.tag_name} | Class: {elem.get_attribute('class')}")
                                
                                # Look for ticker symbols in the table
                                ticker_elements = elem.find_elements(By.XPATH, ".//td | .//div")
                                ticker_count = 0
                                for ticker_elem in ticker_elements[:10]:  # Check first 10 elements
                                    text = ticker_elem.text.strip()
                                    if text and len(text) <= 6 and text.isupper() and text.isalpha():
                                        print(f"   Possible ticker: {text}")
                                        ticker_count += 1
                                if ticker_count > 0:
                                    print(f"   Found {ticker_count} possible tickers")
                        else:
                            print(f"❌ Not found: {selector}")
                    except Exception as e:
                        print(f"⚠️ Error with {selector}: {e}")
            
        except Exception as e:
            print(f"❌ Could not click holdings menu: {e}")
        
        # Get page source for analysis
        print(f"\n📄 PAGE SOURCE ANALYSIS:")
        print("-" * 40)
        
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)} characters")
        
        # Look for common patterns
        patterns = [
            "holdings",
            "ticker",
            "symbol", 
            "weight",
            "allocation",
            "%"
        ]
        
        for pattern in patterns:
            count = page_source.lower().count(pattern.lower())
            print(f"'{pattern}' appears {count} times")
        
        # Save a sample of the page source
        sample_file = "etf_page_sample.html"
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write(page_source)
        print(f"📁 Saved page source to: {sample_file}")
        
        driver.quit()
        print("\n✅ Analysis complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_etf_page_structure()