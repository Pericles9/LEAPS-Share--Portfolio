"""
ETF Universe Builder

Simple script to build and analyze portfolios from ETFs.
Just specify your ETFs and run!
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.universe_manager import PortfolioUniverseManager
import warnings
warnings.filterwarnings('ignore')


def main():
    """Build and analyze portfolios from ETFs."""
    
    # ============================================================================
    # SPECIFY YOUR ETFs HERE - Just add the ETF symbols you want to analyze
    # ============================================================================
    
    YOUR_ETFS = [
        # Sector ETFs (choose sectors you want exposure to)
        'XLK',    # Technology
        'XLF',    # Financial  
        'XLV',    # Healthcare
        'XLE',    # Energy
        'XLI',    # Industrial
        
        # Or use broad market ETFs
        # 'SPY',    # S&P 500
        # 'QQQ',    # NASDAQ 100
        
        # Or thematic ETFs
        # 'ARKK',   # Innovation
        # 'SOXX',   # Semiconductors
        # 'JETS',   # Airlines
        
        # Add more ETFs as needed...
    ]
    
    # Configuration
    MIN_WEIGHT = 1.0        # Only include stocks with >1% weight in ETF
    TOP_N_PER_ETF = 15      # Take top 15 holdings from each ETF
    
    # ============================================================================
    
    print("ETF Universe Portfolio Builder")
    print("=" * 40)
    print(f"Source ETFs: {', '.join(YOUR_ETFS)}")
    print(f"Minimum weight: {MIN_WEIGHT}%")
    print(f"Max holdings per ETF: {TOP_N_PER_ETF}")
    
    # Initialize universe manager
    manager = PortfolioUniverseManager(risk_free_rate=0.045)
    
    # Build universe from ETFs
    print(f"\nStep 1: Extracting holdings from {len(YOUR_ETFS)} ETFs...")
    try:
        manager.add_universe_from_etfs(
            etf_symbols=YOUR_ETFS,
            min_weight=MIN_WEIGHT,
            top_n_per_etf=TOP_N_PER_ETF,
            fetch_fundamentals=True  # Get sector, market cap, etc.
        )
        
        if not manager.universe:
            print("Error: No stocks found in ETF holdings. Check ETF symbols.")
            return
            
        print(f"✓ Created universe with {len(manager.universe)} unique stocks")
        
        # Show breakdown by ETF
        etf_breakdown = manager.etf_manager.extract_symbols_from_etfs(
            YOUR_ETFS, MIN_WEIGHT, TOP_N_PER_ETF
        )
        
        print("\nStocks extracted by ETF:")
        for etf, stocks in etf_breakdown.items():
            print(f"  {etf}: {len(stocks)} stocks")
        
    except Exception as e:
        print(f"Error building universe: {e}")
        return
    
    # Fetch historical data  
    print(f"\nStep 2: Fetching historical data...")
    try:
        universe_data = manager.fetch_universe_data(period="1y")
        
        if not universe_data:
            print("Error: Could not fetch historical data")
            return
            
        print(f"✓ Loaded data for {len(universe_data['symbols'])} stocks")
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    # Build portfolio strategies
    print(f"\nStep 3: Building portfolio strategies...")
    try:
        strategies = manager.build_portfolio_strategies()
        print(f"✓ Created {len(strategies)} strategies")
        
        for strategy in strategies:
            print(f"  - {strategy.name}: {len(strategy.symbols)} assets")
    
    except Exception as e:
        print(f"Error building strategies: {e}")
        return
    
    # Optimize portfolios
    print(f"\nStep 4: Optimizing portfolios...")
    try:
        manager.optimize_strategies()
        
        # Quick summary
        summary_df = manager.get_strategy_summary()
        if not summary_df.empty:
            print("✓ Optimization complete")
            best_sharpe = summary_df.loc[summary_df['Sharpe_Ratio'].idxmax()]
            print(f"  Best Sharpe ratio: {best_sharpe['Strategy']} ({best_sharpe['Sharpe_Ratio']:.3f})")
    
    except Exception as e:
        print(f"Error optimizing: {e}")
        return
    
    # Run Monte Carlo simulations
    print(f"\nStep 5: Running Monte Carlo simulations...")
    try:
        manager.run_monte_carlo_simulations(
            num_simulations=1000,
            time_horizon=252,  # 1 year
            initial_investment=100000  # $100k
        )
        print("✓ Monte Carlo simulations complete")
    
    except Exception as e:
        print(f"Error in simulations: {e}")
        return
    
    # Display comprehensive results
    print(f"\nStep 6: Generating results...")
    manager.print_detailed_results()
    
    # Save results
    print(f"\nStep 7: Saving results to CSV files...")
    try:
        # Strategy summary
        summary_df = manager.get_strategy_summary()
        summary_df.to_csv('etf_portfolio_strategies.csv', index=False)
        print("✓ Saved: etf_portfolio_strategies.csv")
        
        # Monte Carlo results
        mc_df = manager.get_monte_carlo_summary()
        mc_df.to_csv('etf_monte_carlo_results.csv', index=False)
        print("✓ Saved: etf_monte_carlo_results.csv")
        
        # Universe breakdown
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
        
        import pandas as pd
        universe_df = pd.DataFrame(universe_info)
        universe_df.to_csv('etf_universe_stocks.csv', index=False)
        print("✓ Saved: etf_universe_stocks.csv")
        
        # ETF source mapping
        etf_mapping = []
        for etf, stocks in etf_breakdown.items():
            for stock in stocks:
                etf_mapping.append({'ETF': etf, 'Stock': stock})
        
        mapping_df = pd.DataFrame(etf_mapping)
        mapping_df.to_csv('etf_stock_mapping.csv', index=False)
        print("✓ Saved: etf_stock_mapping.csv")
        
    except Exception as e:
        print(f"Error saving files: {e}")
    
    print(f"\n" + "=" * 40)
    print("ETF PORTFOLIO ANALYSIS COMPLETE!")
    print(f"\nYour universe: {len(manager.universe)} stocks from {len(YOUR_ETFS)} ETFs")
    print(f"Strategies analyzed: {len(manager.strategies)}")
    print(f"Files generated: 4 CSV files with detailed results")
    
    print(f"\nTo modify:")
    print(f"- Edit YOUR_ETFS list with different ETF symbols") 
    print(f"- Adjust MIN_WEIGHT and TOP_N_PER_ETF parameters")
    print(f"- Change time horizon and investment amounts")


if __name__ == "__main__":
    main()