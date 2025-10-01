"""
Advanced Portfolio Analysis with Live Options Data

This example demonstrates the enhanced portfolio system with:
1. Live options chain data fetching
2. Multiple portfolio strategies
3. Monte Carlo simulations on various portfolios
4. Comprehensive analysis and reporting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from src.data.universe_manager import PortfolioUniverseManager
from src.data.market_data import MarketDataFetcher
from src.models.black_scholes import BlackScholesModel
from src.utils.helpers import format_percentage, format_currency


def main():
    """Main function demonstrating advanced portfolio analysis."""
    
    print("Advanced Portfolio Analysis with Live Options Data")
    print("=" * 60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Sample universe of stocks (you can replace this with your own list)
    sample_universe = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'NVDA', 'META', 'NFLX', 'AMD', 'CRM',
        'JPM', 'BAC', 'WMT', 'PG', 'JNJ',
        'V', 'MA', 'HD', 'DIS', 'ADBE'
    ]
    
    print(f"\nSample Universe: {len(sample_universe)} stocks")
    print("Note: Replace 'sample_universe' list with your preferred stocks")
    
    # Initialize the universe manager
    print("\n" + "="*60)
    print("1. INITIALIZING PORTFOLIO UNIVERSE MANAGER")
    print("="*60)
    
    universe_manager = PortfolioUniverseManager(risk_free_rate=0.045)  # Current ~4.5%
    
    # Add stocks to universe (with fundamental data)
    print("\nAdding stocks to universe and fetching fundamental data...")
    universe_manager.add_universe_stocks(sample_universe, fetch_fundamentals=True)
    
    # Fetch historical data
    print("\n" + "="*60)
    print("2. FETCHING HISTORICAL DATA")
    print("="*60)
    
    universe_data = universe_manager.fetch_universe_data(period="1y")
    
    if not universe_data:
        print("Error: Could not fetch universe data. Exiting.")
        return
    
    print(f"Successfully loaded data for {len(universe_data['symbols'])} stocks")
    
    # Build portfolio strategies
    print("\n" + "="*60)
    print("3. BUILDING PORTFOLIO STRATEGIES")
    print("="*60)
    
    strategies = universe_manager.build_portfolio_strategies()
    
    # Optimize strategies
    print("\n" + "="*60)
    print("4. OPTIMIZING STRATEGIES")
    print("="*60)
    
    universe_manager.optimize_strategies()
    
    # Run Monte Carlo simulations
    print("\n" + "="*60)
    print("5. RUNNING MONTE CARLO SIMULATIONS")
    print("="*60)
    
    universe_manager.run_monte_carlo_simulations(
        num_simulations=1000,
        time_horizon=252,  # 1 year
        initial_investment=100000  # $100k
    )
    
    # Display comprehensive results
    universe_manager.print_detailed_results()
    
    # Demonstrate options chain fetching
    print("\n" + "="*60)
    print("6. LIVE OPTIONS CHAIN ANALYSIS")
    print("="*60)
    
    demo_options_analysis(sample_universe[:3])  # Demo with first 3 stocks
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("- Review the portfolio strategies and their performance metrics")
    print("- Consider the Monte Carlo simulation results for risk assessment")
    print("- Use the options chain data for derivatives strategies")
    print("- Modify the universe list with your preferred stocks")
    print("- Adjust portfolio constraints and optimization parameters")


def demo_options_analysis(symbols: list):
    """Demonstrate options chain analysis."""
    fetcher = MarketDataFetcher()
    bs_model = BlackScholesModel()
    
    print(f"Fetching options chain data for: {', '.join(symbols)}")
    
    for symbol in symbols:
        print(f"\n--- {symbol} Options Analysis ---")
        
        try:
            # Get current stock price
            current_price = fetcher._get_current_price(symbol)
            if not current_price:
                print(f"Could not fetch current price for {symbol}")
                continue
                
            print(f"Current Price: {format_currency(current_price)}")
            
            # Fetch options chain
            options_data = fetcher.fetch_options_chain(symbol)
            
            if 'error' in options_data:
                print(f"Options data error: {options_data['error']}")
                continue
                
            if not options_data['chains']:
                print(f"No options chains available for {symbol}")
                continue
            
            # Get implied volatilities
            iv_data = fetcher.get_implied_volatilities(symbol)
            
            if 'error' not in iv_data and iv_data['iv_surface']:
                # Display IV for nearest expiration
                nearest_exp = min(iv_data['iv_surface'].keys())
                iv_info = iv_data['iv_surface'][nearest_exp]
                
                print(f"Nearest Expiration: {nearest_exp}")
                print(f"Days to Expiration: {iv_info.get('days_to_expiration', 'N/A')}")
                
                if iv_info['atm_call_iv']:
                    print(f"ATM Call IV: {iv_info['atm_call_iv']:.1%}")
                if iv_info['atm_put_iv']:
                    print(f"ATM Put IV: {iv_info['atm_put_iv']:.1%}")
                
                # Compare with Black-Scholes theoretical value
                if iv_info['atm_call_iv'] and iv_info['days_to_expiration']:
                    time_to_exp = iv_info['days_to_expiration'] / 365
                    if time_to_exp > 0:
                        theoretical_price = bs_model.calculate_price(
                            S=current_price,
                            K=current_price,  # ATM
                            T=time_to_exp,
                            r=0.045,  # Risk-free rate
                            sigma=iv_info['atm_call_iv'],
                            option_type='call'
                        )
                        print(f"Theoretical ATM Call Price: {format_currency(theoretical_price)}")
            
            # Show number of available options
            total_calls = sum(len(chain['calls']) for chain in options_data['chains'].values())
            total_puts = sum(len(chain['puts']) for chain in options_data['chains'].values())
            print(f"Available Options: {total_calls} calls, {total_puts} puts")
            print(f"Expiration Dates: {len(options_data['expiration_dates'])}")
            
        except Exception as e:
            print(f"Error analyzing options for {symbol}: {e}")
            continue


if __name__ == "__main__":
    main()