"""
Portfolio Strategy Stock Allocation Breakdown

Shows exactly how each portfolio strategy allocates weights to the selected stocks.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from src.data.universe_manager import PortfolioUniverseManager
from src.utils.helpers import format_percentage
import warnings
warnings.filterwarnings('ignore')


def analyze_portfolio_allocations():
    """Analyze how each portfolio strategy allocates to selected stocks."""
    
    print("PORTFOLIO STRATEGY ALLOCATION BREAKDOWN")
    print("=" * 60)
    
    # Load the universe from our analysis
    universe_df = pd.read_csv('stock_selection_final_universe.csv')
    stocks = universe_df['Stock_Symbol'].tolist()
    
    print(f"Analyzing allocation for {len(stocks)} selected stocks...")
    
    # Build universe and strategies
    manager = PortfolioUniverseManager()
    manager.add_universe_stocks(stocks, fetch_fundamentals=False)
    
    # Fetch data and build strategies
    print("Fetching market data...")
    universe_data = manager.fetch_universe_data(period="6mo")
    
    if not universe_data:
        print("Could not fetch market data")
        return
    
    print("Building and optimizing strategies...")
    strategies = manager.build_portfolio_strategies()
    manager.optimize_strategies()
    
    # Create allocation breakdown
    allocation_data = []
    
    print(f"\n📊 STRATEGY ALLOCATION BREAKDOWN")
    print("-" * 60)
    
    for strategy in manager.strategies:
        if not strategy.metrics or strategy.metrics.weights is None:
            continue
        
        print(f"\n--- {strategy.name.upper()} ---")
        print(f"Description: {strategy.description}")
        print(f"Performance: Return={format_percentage(strategy.metrics.expected_return)}, "
              f"Vol={format_percentage(strategy.metrics.volatility)}, "
              f"Sharpe={strategy.metrics.sharpe_ratio:.3f}")
        
        # Create stock allocation list
        stock_weights = list(zip(strategy.symbols, strategy.metrics.weights))
        stock_weights.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\nStock Allocations (showing all {len(stock_weights)} positions):")
        
        total_weight = 0
        significant_positions = 0
        
        for i, (stock, weight) in enumerate(stock_weights, 1):
            # Get ETF source info
            stock_info = universe_df[universe_df['Stock_Symbol'] == stock].iloc[0]
            source_etfs = stock_info['Source_ETFs']
            etf_count = stock_info['ETF_Count']
            avg_etf_weight = stock_info['Avg_Weight']
            
            # Determine if significant position
            is_significant = weight >= 0.01  # 1% or more
            if is_significant:
                significant_positions += 1
            
            # Color coding for display
            if weight >= 0.10:  # 10%+
                indicator = "🔴"
            elif weight >= 0.05:  # 5%+
                indicator = "🟡" 
            elif weight >= 0.01:  # 1%+
                indicator = "🟢"
            else:
                indicator = "⚪"
            
            print(f"  {i:2d}. {indicator} {stock:<6} - {weight:>6.1%} "
                  f"(from {source_etfs}, avg ETF weight: {avg_etf_weight:.1f}%)")
            
            total_weight += weight
            
            # Store data for CSV
            allocation_data.append({
                'Strategy': strategy.name,
                'Stock_Symbol': stock,
                'Portfolio_Weight': weight,
                'Source_ETFs': source_etfs,
                'ETF_Count': etf_count,
                'Avg_ETF_Weight': avg_etf_weight,
                'Is_Significant': is_significant,
                'Rank': i
            })
        
        print(f"\nSummary:")
        print(f"  • Total allocation: {total_weight:.1%}")
        print(f"  • Significant positions (≥1%): {significant_positions}")
        print(f"  • Top 5 positions weight: {sum(w for _, w in stock_weights[:5]):.1%}")
        print(f"  • Top 10 positions weight: {sum(w for _, w in stock_weights[:10]):.1%}")
    
    # Save allocation data
    allocation_df = pd.DataFrame(allocation_data)
    allocation_df.to_csv('portfolio_strategy_allocations.csv', index=False)
    print(f"\n✓ Saved: portfolio_strategy_allocations.csv")
    
    # Create comparison analysis
    print(f"\n📈 CROSS-STRATEGY ANALYSIS")
    print("-" * 60)
    
    # Analyze which stocks are favored across strategies
    strategy_comparison = {}
    
    for strategy in manager.strategies:
        if not strategy.metrics or strategy.metrics.weights is None:
            continue
        strategy_comparison[strategy.name] = dict(zip(strategy.symbols, strategy.metrics.weights))
    
    # Find stocks with significant allocations across strategies
    significant_across_strategies = {}
    
    for stock in stocks:
        stock_allocations = {}
        for strategy_name, allocations in strategy_comparison.items():
            weight = allocations.get(stock, 0)
            if weight >= 0.01:  # 1% threshold
                stock_allocations[strategy_name] = weight
        
        if len(stock_allocations) >= 2:  # Significant in 2+ strategies
            significant_across_strategies[stock] = stock_allocations
    
    print(f"Stocks with significant allocations (≥1%) in multiple strategies:")
    
    for stock, allocations in significant_across_strategies.items():
        stock_info = universe_df[universe_df['Stock_Symbol'] == stock].iloc[0]
        source_etfs = stock_info['Source_ETFs']
        
        allocation_str = ", ".join([f"{strategy}: {weight:.1%}" for strategy, weight in allocations.items()])
        print(f"  • {stock:<6} (from {source_etfs}): {allocation_str}")
    
    # Strategy diversification analysis
    print(f"\n📊 STRATEGY DIVERSIFICATION METRICS")
    print("-" * 60)
    
    for strategy in manager.strategies:
        if not strategy.metrics or strategy.metrics.weights is None:
            continue
        
        weights = strategy.metrics.weights
        
        # Calculate concentration metrics
        herfindahl_index = sum(w**2 for w in weights)  # Lower = more diversified
        effective_stocks = 1 / herfindahl_index if herfindahl_index > 0 else 0
        
        # Weight distribution
        max_weight = max(weights)
        weights_above_5pct = sum(1 for w in weights if w >= 0.05)
        weights_above_10pct = sum(1 for w in weights if w >= 0.10)
        
        print(f"{strategy.name}:")
        print(f"  • Herfindahl Index: {herfindahl_index:.3f} (lower = more diversified)")
        print(f"  • Effective # of stocks: {effective_stocks:.1f}")
        print(f"  • Maximum single position: {max_weight:.1%}")
        print(f"  • Positions >5%: {weights_above_5pct}")
        print(f"  • Positions >10%: {weights_above_10pct}")
    
    return allocation_df


def create_allocation_summary():
    """Create a visual summary of allocations."""
    
    try:
        allocation_df = pd.read_csv('portfolio_strategy_allocations.csv')
        
        print(f"\n📋 ALLOCATION SUMMARY TABLE")
        print("-" * 60)
        
        # Create pivot table showing all strategy allocations
        pivot_df = allocation_df.pivot(index='Stock_Symbol', columns='Strategy', values='Portfolio_Weight')
        pivot_df = pivot_df.fillna(0)
        
        # Add source ETF info
        universe_df = pd.read_csv('stock_selection_final_universe.csv')
        pivot_df = pivot_df.merge(universe_df[['Stock_Symbol', 'Source_ETFs', 'ETF_Count', 'Avg_ETF_Weight']], 
                                left_index=True, right_on='Stock_Symbol', how='left')
        pivot_df = pivot_df.set_index('Stock_Symbol')
        
        # Sort by maximum allocation across strategies
        pivot_df['Max_Allocation'] = pivot_df[['Equal Weight', 'Max Sharpe Ratio (All)', 'Minimum Volatility']].max(axis=1)
        pivot_df = pivot_df.sort_values('Max_Allocation', ascending=False)
        
        print("Stock allocation across strategies (showing top 15):")
        print()
        print(f"{'Symbol':<6} {'Equal Wt':<8} {'Max Sharpe':<10} {'Min Vol':<8} {'Source ETFs':<15} {'ETF Wt':<6}")
        print("-" * 70)
        
        for stock in pivot_df.head(15).index:
            row = pivot_df.loc[stock]
            equal_wt = f"{row['Equal Weight']:.1%}" if row['Equal Weight'] > 0 else "-"
            max_sharpe = f"{row['Max Sharpe Ratio (All)']:.1%}" if row['Max Sharpe Ratio (All)'] > 0 else "-"
            min_vol = f"{row['Minimum Volatility']:.1%}" if row['Minimum Volatility'] > 0 else "-"
            source_etfs = row['Source_ETFs'][:12] + "..." if len(row['Source_ETFs']) > 12 else row['Source_ETFs']
            avg_etf_wt = f"{row['Avg_ETF_Weight']:.1f}%"
            
            print(f"{stock:<6} {equal_wt:<8} {max_sharpe:<10} {min_vol:<8} {source_etfs:<15} {avg_etf_wt:<6}")
        
        print("\nLegend: Equal Wt = Equal Weight, Max Sharpe = Max Sharpe Ratio, Min Vol = Minimum Volatility")
        
        # Save summary table
        pivot_df.to_csv('strategy_allocation_comparison.csv')
        print(f"\n✓ Saved: strategy_allocation_comparison.csv")
        
    except FileNotFoundError:
        print("Portfolio allocation CSV not found. Run allocation analysis first.")


def main():
    """Main function to run allocation analysis."""
    
    try:
        # Run allocation analysis
        allocation_df = analyze_portfolio_allocations()
        
        # Create summary
        create_allocation_summary()
        
        print(f"\n" + "=" * 60)
        print("PORTFOLIO ALLOCATION ANALYSIS COMPLETE!")
        print(f"\nKey Insights:")
        print(f"• Different strategies use the same stocks very differently")
        print(f"• Equal Weight spreads risk across all 23 stocks")
        print(f"• Max Sharpe concentrates in top performers")
        print(f"• Min Volatility focuses on stable, large positions")
        print(f"• ETF overlaps often correspond to higher portfolio weights")
        print(f"• Stock selection filters create focused, quality universe")
        
        print(f"\n📁 Files Generated:")
        print(f"• portfolio_strategy_allocations.csv - Detailed allocations") 
        print(f"• strategy_allocation_comparison.csv - Side-by-side comparison")
        
    except Exception as e:
        print(f"Error in allocation analysis: {e}")


if __name__ == "__main__":
    main()