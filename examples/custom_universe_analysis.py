"""
Custom Universe Portfolio Analysis

Use this script to analyze your custom universe of stocks.
Simply replace the YOUR_UNIVERSE list below with your preferred stocks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.universe_manager import PortfolioUniverseManager
import warnings
warnings.filterwarnings('ignore')


def analyze_custom_universe():
    """Analyze your custom universe of stocks."""
    
    # ============================================================================
    # REPLACE THIS LIST WITH YOUR UNIVERSE OF TRADABLE EQUITIES
    # ============================================================================
    YOUR_UNIVERSE = [
        # Technology
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'ADBE', 'CRM',
        
        # Financial
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BRK-A', 'V', 'MA', 'AXP',
        
        # Healthcare
        'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN',
        
        # Consumer
        'WMT', 'HD', 'PG', 'KO', 'PEP', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST',
        
        # Industrial
        'BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'LMT', 'RTX', 'DE', 'UNP',
        
        # Energy
        'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PXD', 'KMI', 'OKE', 'WMB', 'PSX',
        
        # Add your own symbols here...
        # 'YOUR_SYMBOL_1', 'YOUR_SYMBOL_2', etc.
    ]
    # ============================================================================
    
    print("Custom Universe Portfolio Analysis")
    print("=" * 50)
    print(f"Analyzing {len(YOUR_UNIVERSE)} stocks")
    print("Stocks:", ', '.join(YOUR_UNIVERSE[:10]) + ('...' if len(YOUR_UNIVERSE) > 10 else ''))
    
    # Initialize universe manager
    manager = PortfolioUniverseManager(risk_free_rate=0.045)
    
    # Add stocks and fetch data
    print("\nStep 1: Adding stocks to universe...")
    manager.add_universe_stocks(YOUR_UNIVERSE, fetch_fundamentals=True)
    
    print("\nStep 2: Fetching historical data...")
    universe_data = manager.fetch_universe_data(period="1y")
    
    if not universe_data:
        print("Error fetching data. Please check your stock symbols.")
        return
    
    print("\nStep 3: Building portfolio strategies...")
    strategies = manager.build_portfolio_strategies()
    
    print("\nStep 4: Optimizing portfolios...")
    manager.optimize_strategies()
    
    print("\nStep 5: Running Monte Carlo simulations...")
    manager.run_monte_carlo_simulations(
        num_simulations=1000,
        time_horizon=252,  # 1 year
        initial_investment=100000  # $100k
    )
    
    # Display results
    manager.print_detailed_results()
    
    # Save results to CSV files
    print("\nSaving results to CSV files...")
    
    try:
        summary_df = manager.get_strategy_summary()
        summary_df.to_csv('portfolio_strategies_summary.csv', index=False)
        print("✓ Saved: portfolio_strategies_summary.csv")
        
        mc_df = manager.get_monte_carlo_summary()
        mc_df.to_csv('monte_carlo_results.csv', index=False)
        print("✓ Saved: monte_carlo_results.csv")
        
        # Save universe info
        universe_info = []
        for stock in manager.universe:
            universe_info.append({
                'Symbol': stock.symbol,
                'Sector': stock.sector,
                'Market_Cap': stock.market_cap,
                'Beta': stock.beta,
                'PE_Ratio': stock.pe_ratio,
                'Dividend_Yield': stock.dividend_yield
            })
        
        universe_df = pd.DataFrame(universe_info)
        universe_df.to_csv('universe_stocks_info.csv', index=False)
        print("✓ Saved: universe_stocks_info.csv")
        
    except Exception as e:
        print(f"Error saving CSV files: {e}")
    
    print("\nAnalysis complete!")
    print("\nFiles generated:")
    print("- portfolio_strategies_summary.csv: Strategy performance metrics")
    print("- monte_carlo_results.csv: Monte Carlo simulation results")
    print("- universe_stocks_info.csv: Stock fundamental data")


if __name__ == "__main__":
    import pandas as pd
    analyze_custom_universe()