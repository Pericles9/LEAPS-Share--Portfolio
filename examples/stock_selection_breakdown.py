"""
Stock Selection Analyzer

Detailed breakdown of stock selection process for portfolio construction.
Shows which stocks are selected from ETFs, their characteristics, and how they're used.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from src.data.universe_manager import PortfolioUniverseManager
from src.data.etf_holdings import ETFHoldingsManager
from src.utils.helpers import format_percentage, format_currency
import warnings
warnings.filterwarnings('ignore')


class StockSelectionAnalyzer:
    """Analyze the stock selection process in detail."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.universe_manager = PortfolioUniverseManager()
        self.etf_manager = ETFHoldingsManager()
        self.selection_data = {}
    
    def analyze_etf_selection(self, etf_symbols: List[str], 
                            min_weight: float = 1.0,
                            top_n_per_etf: int = 20) -> Dict:
        """
        Analyze stock selection from ETFs in detail.
        
        Args:
            etf_symbols: List of ETF symbols
            min_weight: Minimum weight threshold
            top_n_per_etf: Top N holdings per ETF
            
        Returns:
            Dictionary with detailed selection analysis
        """
        print("STOCK SELECTION ANALYSIS")
        print("=" * 60)
        print(f"Source ETFs: {', '.join(etf_symbols)}")
        print(f"Minimum weight threshold: {min_weight}%")
        print(f"Maximum holdings per ETF: {top_n_per_etf}")
        
        analysis = {
            'etf_details': {},
            'stock_sources': {},
            'selection_stats': {},
            'filtered_stocks': {},
            'final_universe': []
        }
        
        # Step 1: Analyze each ETF's holdings
        print(f"\n1. ETF HOLDINGS BREAKDOWN")
        print("-" * 40)
        
        total_raw_holdings = 0
        total_filtered_holdings = 0
        
        for etf in etf_symbols:
            print(f"\n--- {etf} Analysis ---")
            
            # Get ETF info
            etf_info = self.etf_manager.get_etf_holdings(etf, top_n_per_etf)
            
            if not etf_info or not etf_info.holdings:
                print(f"❌ No holdings data for {etf}")
                analysis['etf_details'][etf] = {'error': 'No data available'}
                continue
            
            print(f"ETF Name: {etf_info.name}")
            print(f"Total available holdings: {len(etf_info.holdings)}")
            
            # Filter by weight threshold
            filtered_holdings = [h for h in etf_info.holdings if h.weight >= min_weight]
            valid_holdings = []
            
            for holding in filtered_holdings:
                # Additional filtering for valid stock symbols
                if (holding.symbol and 
                    len(holding.symbol) <= 5 and 
                    not any(char in holding.symbol for char in ['.', '=', '^', '-'])):
                    valid_holdings.append(holding)
            
            print(f"Holdings after weight filter (>{min_weight}%): {len(filtered_holdings)}")
            print(f"Valid stock symbols: {len(valid_holdings)}")
            
            total_raw_holdings += len(etf_info.holdings)
            total_filtered_holdings += len(valid_holdings)
            
            # Show top holdings
            print(f"Top holdings selected:")
            for i, holding in enumerate(valid_holdings[:10], 1):
                print(f"  {i:2d}. {holding.symbol:<6} - {holding.name:<25} ({holding.weight:.1f}%)")
            
            if len(valid_holdings) > 10:
                print(f"  ... and {len(valid_holdings) - 10} more")
            
            # Store detailed info
            analysis['etf_details'][etf] = {
                'name': etf_info.name,
                'total_holdings': len(etf_info.holdings),
                'filtered_holdings': len(filtered_holdings),
                'valid_holdings': len(valid_holdings),
                'selected_symbols': [h.symbol for h in valid_holdings],
                'weight_range': (
                    min(h.weight for h in valid_holdings) if valid_holdings else 0,
                    max(h.weight for h in valid_holdings) if valid_holdings else 0
                ),
                'holdings_details': [(h.symbol, h.name, h.weight) for h in valid_holdings]
            }
        
        # Step 2: Analyze stock overlap and sources
        print(f"\n2. STOCK SOURCE ANALYSIS")
        print("-" * 40)
        
        all_stocks = {}  # stock -> list of (etf, weight) tuples
        
        for etf, details in analysis['etf_details'].items():
            if 'error' in details:
                continue
                
            for symbol, name, weight in details['holdings_details']:
                if symbol not in all_stocks:
                    all_stocks[symbol] = []
                all_stocks[symbol].append((etf, weight, name))
        
        # Categorize stocks by overlap
        unique_stocks = {stock: sources for stock, sources in all_stocks.items() if len(sources) == 1}
        overlapping_stocks = {stock: sources for stock, sources in all_stocks.items() if len(sources) > 1}
        
        print(f"Total unique stock symbols found: {len(all_stocks)}")
        print(f"Stocks appearing in only 1 ETF: {len(unique_stocks)}")
        print(f"Stocks appearing in multiple ETFs: {len(overlapping_stocks)}")
        
        # Show most overlapped stocks
        if overlapping_stocks:
            print(f"\nMost overlapped stocks:")
            sorted_overlaps = sorted(overlapping_stocks.items(), 
                                   key=lambda x: len(x[1]), reverse=True)
            
            for stock, sources in sorted_overlaps[:10]:
                etf_list = [f"{etf}({weight:.1f}%)" for etf, weight, name in sources]
                print(f"  {stock:<6} - {len(sources)} ETFs: {', '.join(etf_list)}")
        
        analysis['stock_sources'] = all_stocks
        analysis['selection_stats'] = {
            'total_raw_holdings': total_raw_holdings,
            'total_filtered_holdings': total_filtered_holdings,
            'unique_stocks': len(all_stocks),
            'single_etf_stocks': len(unique_stocks),
            'multi_etf_stocks': len(overlapping_stocks),
            'max_overlap': max(len(sources) for sources in all_stocks.values()) if all_stocks else 0
        }
        
        # Step 3: Final universe selection
        print(f"\n3. FINAL UNIVERSE CONSTRUCTION")
        print("-" * 40)
        
        final_universe = sorted(list(all_stocks.keys()))
        analysis['final_universe'] = final_universe
        
        print(f"Final universe size: {len(final_universe)} stocks")
        print(f"Reduction from raw holdings: {total_raw_holdings} → {len(final_universe)} "
              f"({(1 - len(final_universe)/total_raw_holdings)*100:.1f}% reduction)")
        
        # Show universe by sector/characteristics (if we fetch fundamental data)
        print(f"\nFinal universe stocks:")
        for i, stock in enumerate(final_universe, 1):
            sources = all_stocks[stock]
            if len(sources) == 1:
                etf, weight, name = sources[0]
                print(f"  {i:2d}. {stock:<6} - {name[:30]:<30} (from {etf}: {weight:.1f}%)")
            else:
                etf_info = f"{len(sources)} ETFs"
                avg_weight = sum(weight for etf, weight, name in sources) / len(sources)
                name = sources[0][2]  # Take name from first source
                print(f"  {i:2d}. {stock:<6} - {name[:30]:<30} (from {etf_info}, avg: {avg_weight:.1f}%)")
        
        self.selection_data = analysis
        return analysis
    
    def analyze_portfolio_strategies_selection(self, analysis_data: Dict) -> None:
        """Analyze how selected stocks are used in different portfolio strategies."""
        
        if not analysis_data['final_universe']:
            print("No universe data to analyze")
            return
        
        print(f"\n4. PORTFOLIO STRATEGY STOCK USAGE")
        print("-" * 40)
        
        # Build universe in universe manager
        self.universe_manager.add_universe_stocks(
            analysis_data['final_universe'], 
            fetch_fundamentals=False  # Skip for speed
        )
        
        # Fetch data (shorter period for analysis)
        print("Fetching historical data for analysis...")
        try:
            universe_data = self.universe_manager.fetch_universe_data(period="6mo")
            if not universe_data:
                print("Could not fetch historical data")
                return
            
            print(f"Successfully loaded data for {len(universe_data['symbols'])} stocks")
            
            # Build strategies
            strategies = self.universe_manager.build_portfolio_strategies()
            self.universe_manager.optimize_strategies()
            
            print(f"\nStrategy stock usage breakdown:")
            
            for strategy in self.universe_manager.strategies:
                if not strategy.metrics:
                    continue
                    
                print(f"\n--- {strategy.name} ---")
                print(f"Total stocks used: {len(strategy.symbols)}")
                print(f"Description: {strategy.description}")
                
                # Show top weighted stocks in strategy
                if hasattr(strategy.metrics, 'weights') and strategy.metrics.weights is not None:
                    # Get stocks with their weights
                    stock_weights = list(zip(strategy.symbols, strategy.metrics.weights))
                    stock_weights.sort(key=lambda x: x[1], reverse=True)
                    
                    print(f"Top 10 weighted stocks:")
                    for i, (stock, weight) in enumerate(stock_weights[:10], 1):
                        # Find source ETFs for this stock
                        sources = analysis_data['stock_sources'].get(stock, [])
                        source_info = f"from {sources[0][0]}" if sources else "unknown source"
                        print(f"  {i:2d}. {stock:<6} - {weight:.1%} ({source_info})")
                
                # Show performance metrics
                if strategy.metrics:
                    print(f"Expected Return: {format_percentage(strategy.metrics.expected_return)}")
                    print(f"Volatility: {format_percentage(strategy.metrics.volatility)}")
                    print(f"Sharpe Ratio: {strategy.metrics.sharpe_ratio:.3f}")
            
        except Exception as e:
            print(f"Error in portfolio analysis: {e}")
    
    def generate_selection_report(self, etf_symbols: List[str], 
                                min_weight: float = 1.0,
                                top_n_per_etf: int = 20,
                                save_to_csv: bool = True) -> None:
        """Generate comprehensive stock selection report."""
        
        print("COMPREHENSIVE STOCK SELECTION REPORT")
        print("=" * 70)
        
        # Run analysis
        analysis = self.analyze_etf_selection(etf_symbols, min_weight, top_n_per_etf)
        
        # Analyze portfolio usage
        self.analyze_portfolio_strategies_selection(analysis)
        
        # Summary statistics
        print(f"\n5. SELECTION SUMMARY")
        print("-" * 40)
        
        stats = analysis['selection_stats']
        print(f"📊 Selection Statistics:")
        print(f"  • Raw ETF holdings processed: {stats['total_raw_holdings']}")
        print(f"  • Holdings after weight filter: {stats['total_filtered_holdings']}")
        print(f"  • Final unique stocks: {stats['unique_stocks']}")
        print(f"  • Stocks from single ETF: {stats['single_etf_stocks']}")
        print(f"  • Stocks from multiple ETFs: {stats['multi_etf_stocks']}")
        print(f"  • Maximum ETF overlap: {stats['max_overlap']} ETFs")
        
        efficiency = (stats['unique_stocks'] / stats['total_raw_holdings']) * 100
        print(f"\n📈 Selection Efficiency: {efficiency:.1f}%")
        print(f"   (Final stocks / Raw holdings)")
        
        # Save detailed results to CSV
        if save_to_csv:
            self.save_selection_analysis_to_csv(analysis)
    
    def save_selection_analysis_to_csv(self, analysis: Dict) -> None:
        """Save detailed selection analysis to CSV files."""
        
        print(f"\n6. SAVING DETAILED ANALYSIS")
        print("-" * 40)
        
        try:
            # 1. ETF Holdings Details
            etf_details_data = []
            for etf, details in analysis['etf_details'].items():
                if 'error' in details:
                    continue
                    
                for symbol, name, weight in details['holdings_details']:
                    etf_details_data.append({
                        'ETF': etf,
                        'ETF_Name': details['name'],
                        'Stock_Symbol': symbol,
                        'Stock_Name': name,
                        'Weight_in_ETF': weight,
                        'Meets_Threshold': 'Yes'
                    })
            
            etf_df = pd.DataFrame(etf_details_data)
            etf_df.to_csv('stock_selection_etf_holdings.csv', index=False)
            print("✓ Saved: stock_selection_etf_holdings.csv")
            
            # 2. Stock Source Analysis
            stock_sources_data = []
            for stock, sources in analysis['stock_sources'].items():
                for etf, weight, name in sources:
                    stock_sources_data.append({
                        'Stock_Symbol': stock,
                        'Stock_Name': name,
                        'Source_ETF': etf,
                        'Weight_in_ETF': weight,
                        'Overlap_Count': len(sources)
                    })
            
            sources_df = pd.DataFrame(stock_sources_data)
            sources_df.to_csv('stock_selection_sources.csv', index=False)
            print("✓ Saved: stock_selection_sources.csv")
            
            # 3. Final Universe Summary
            universe_data = []
            for stock in analysis['final_universe']:
                sources = analysis['stock_sources'][stock]
                universe_data.append({
                    'Stock_Symbol': stock,
                    'Stock_Name': sources[0][2],  # Name from first source
                    'Source_ETFs': ', '.join([etf for etf, weight, name in sources]),
                    'ETF_Count': len(sources),
                    'Avg_Weight': sum(weight for etf, weight, name in sources) / len(sources),
                    'Max_Weight': max(weight for etf, weight, name in sources),
                    'Min_Weight': min(weight for etf, weight, name in sources)
                })
            
            universe_df = pd.DataFrame(universe_data)
            universe_df.to_csv('stock_selection_final_universe.csv', index=False)
            print("✓ Saved: stock_selection_final_universe.csv")
            
            # 4. Selection Statistics
            stats_data = [{
                'Metric': key.replace('_', ' ').title(),
                'Value': value
            } for key, value in analysis['selection_stats'].items()]
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_csv('stock_selection_statistics.csv', index=False)
            print("✓ Saved: stock_selection_statistics.csv")
            
            print(f"\n📁 All selection analysis files saved to current directory")
            
        except Exception as e:
            print(f"Error saving CSV files: {e}")


def main():
    """Run stock selection analysis with sample ETFs."""
    
    # Sample ETF selection for analysis
    sample_etfs = ['SPY', 'XLK', 'XLF', 'QQQ']  # Broad market + sectors
    
    analyzer = StockSelectionAnalyzer()
    
    # Run comprehensive analysis
    analyzer.generate_selection_report(
        etf_symbols=sample_etfs,
        min_weight=2.0,      # Only stocks with >2% weight
        top_n_per_etf=15,    # Top 15 holdings per ETF
        save_to_csv=True     # Save detailed CSV reports
    )
    
    print(f"\n" + "=" * 70)
    print("STOCK SELECTION ANALYSIS COMPLETE!")
    print(f"\nKey Insights:")
    print(f"• Stock selection process is fully transparent")
    print(f"• Weight thresholds effectively filter holdings")
    print(f"• ETF overlap analysis shows diversification")
    print(f"• Portfolio strategies use stocks differently")
    print(f"• Detailed CSV reports available for further analysis")


if __name__ == "__main__":
    main()