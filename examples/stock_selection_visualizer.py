"""
Stock Selection Process Summary

Visual breakdown of how stocks are selected and used in portfolio construction.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings
warnings.filterwarnings('ignore')


def create_selection_visualizations():
    """Create visualizations of the stock selection process."""
    
    # Read the CSV files created by the analysis
    try:
        sources_df = pd.read_csv('stock_selection_sources.csv')
        universe_df = pd.read_csv('stock_selection_final_universe.csv')
        holdings_df = pd.read_csv('stock_selection_etf_holdings.csv')
        
        print("📊 CREATING STOCK SELECTION VISUALIZATIONS")
        print("=" * 50)
        
        # Set up the plotting style
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Stock Selection Process Breakdown', fontsize=16, fontweight='bold')
        
        # 1. ETF Holdings Count
        etf_counts = holdings_df['ETF'].value_counts()
        axes[0, 0].bar(etf_counts.index, etf_counts.values, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
        axes[0, 0].set_title('Holdings Selected by ETF')
        axes[0, 0].set_ylabel('Number of Stocks Selected')
        for i, v in enumerate(etf_counts.values):
            axes[0, 0].text(i, v + 0.1, str(v), ha='center', va='bottom')
        
        # 2. Overlap Distribution
        overlap_counts = universe_df['ETF_Count'].value_counts().sort_index()
        axes[0, 1].pie(overlap_counts.values, labels=[f'{i} ETF{"s" if i>1 else ""}' for i in overlap_counts.index], 
                      autopct='%1.1f%%', colors=['#ff9999', '#66b3ff'])
        axes[0, 1].set_title('Stock Overlap Distribution')
        
        # 3. Weight Distribution
        axes[1, 0].hist(universe_df['Avg_Weight'], bins=10, color='lightblue', alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('Average Weight Distribution')
        axes[1, 0].set_xlabel('Average Weight in ETFs (%)')
        axes[1, 0].set_ylabel('Number of Stocks')
        axes[1, 0].axvline(universe_df['Avg_Weight'].mean(), color='red', linestyle='--', 
                          label=f'Mean: {universe_df["Avg_Weight"].mean():.1f}%')
        axes[1, 0].legend()
        
        # 4. Top Stocks by Weight Range
        top_stocks = universe_df.nlargest(10, 'Max_Weight')
        x_pos = range(len(top_stocks))
        axes[1, 1].bar(x_pos, top_stocks['Max_Weight'], alpha=0.7, color='lightgreen', label='Max Weight')
        axes[1, 1].bar(x_pos, top_stocks['Min_Weight'], alpha=0.7, color='orange', label='Min Weight')
        axes[1, 1].set_title('Top 10 Stocks by Weight Range')
        axes[1, 1].set_xlabel('Stocks')
        axes[1, 1].set_ylabel('Weight in ETF (%)')
        axes[1, 1].set_xticks(x_pos)
        axes[1, 1].set_xticklabels(top_stocks['Stock_Symbol'], rotation=45)
        axes[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig('stock_selection_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        print("✓ Saved: stock_selection_analysis.png")
        
        # Create detailed summary table
        print("\n📋 DETAILED STOCK SELECTION BREAKDOWN")
        print("=" * 50)
        
        print("1. SELECTION FILTERS APPLIED:")
        print(f"   • Minimum weight threshold: 2.0%")
        print(f"   • Maximum holdings per ETF: 15")
        print(f"   • Valid symbol filtering: Yes")
        print(f"   • Duplicate removal: Automatic")
        
        print("\n2. ETF CONTRIBUTION:")
        for etf in ['SPY', 'XLK', 'XLF', 'QQQ']:
            etf_stocks = holdings_df[holdings_df['ETF'] == etf]
            if len(etf_stocks) > 0:
                avg_weight = etf_stocks['Weight_in_ETF'].mean()
                print(f"   • {etf}: {len(etf_stocks)} stocks (avg weight: {avg_weight:.1f}%)")
        
        print("\n3. OVERLAP ANALYSIS:")
        single_etf = len(universe_df[universe_df['ETF_Count'] == 1])
        multi_etf = len(universe_df[universe_df['ETF_Count'] > 1])
        print(f"   • Single ETF stocks: {single_etf} ({single_etf/len(universe_df)*100:.1f}%)")
        print(f"   • Multi-ETF stocks: {multi_etf} ({multi_etf/len(universe_df)*100:.1f}%)")
        
        # Show most overlapped stocks
        most_overlapped = universe_df.nlargest(5, 'ETF_Count')
        print(f"\n   Top overlapped stocks:")
        for _, row in most_overlapped.iterrows():
            print(f"     - {row['Stock_Symbol']}: {row['ETF_Count']} ETFs (avg: {row['Avg_Weight']:.1f}%)")
        
        print("\n4. WEIGHT CHARACTERISTICS:")
        print(f"   • Average weight across all stocks: {universe_df['Avg_Weight'].mean():.1f}%")
        print(f"   • Highest individual weight: {universe_df['Max_Weight'].max():.1f}%")
        print(f"   • Lowest individual weight: {universe_df['Min_Weight'].min():.1f}%")
        print(f"   • Weight standard deviation: {universe_df['Avg_Weight'].std():.1f}%")
        
        print("\n5. FINAL UNIVERSE COMPOSITION:")
        print(f"   • Total stocks selected: {len(universe_df)}")
        print(f"   • From raw ETF holdings: 40 → {len(universe_df)} (57.5% efficiency)")
        
        # Sector breakdown (approximation based on ETF source)
        sector_approx = {
            'Technology': len(holdings_df[holdings_df['ETF'].isin(['XLK', 'QQQ'])]['Stock_Symbol'].unique()),
            'Financial': len(holdings_df[holdings_df['ETF'] == 'XLF']['Stock_Symbol'].unique()),
            'Broad Market': len(holdings_df[holdings_df['ETF'] == 'SPY']['Stock_Symbol'].unique())
        }
        
        print(f"\n   Approximate sector distribution:")
        for sector, count in sector_approx.items():
            print(f"     - {sector}: {count} stocks")
        
        return True
        
    except FileNotFoundError as e:
        print(f"Error: CSV files not found. Please run the stock selection analysis first.")
        return False
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        return False


def print_selection_flow():
    """Print a visual flow of the selection process."""
    
    print("\n🔄 STOCK SELECTION FLOW DIAGRAM")
    print("=" * 50)
    print("""
    ┌─────────────────┐
    │   INPUT ETFs    │
    │  SPY, XLK,      │ 
    │  XLF, QQQ       │
    └─────┬───────────┘
          │
          ▼
    ┌─────────────────┐
    │ FETCH HOLDINGS  │
    │  40 total       │
    │  holdings       │
    └─────┬───────────┘
          │
          ▼
    ┌─────────────────┐
    │ APPLY FILTERS   │
    │ • Weight >2.0%  │
    │ • Valid symbols │
    │ • Top 15/ETF    │
    └─────┬───────────┘
          │
          ▼
    ┌─────────────────┐
    │ REMOVE DUPES    │
    │ 34 holdings →   │
    │ 23 unique       │
    └─────┬───────────┘
          │
          ▼
    ┌─────────────────┐
    │ FINAL UNIVERSE  │
    │  23 stocks      │
    │  8 overlapped   │
    │  15 unique      │
    └─────┬───────────┘
          │
          ▼
    ┌─────────────────┐
    │ BUILD PORTFOLIOS│
    │ • Equal Weight  │
    │ • Max Sharpe    │
    │ • Min Volatility│
    └─────────────────┘
    """)


def main():
    """Main function to run all visualizations and summaries."""
    
    print("STOCK SELECTION BREAKDOWN VISUALIZER")
    print("=" * 60)
    
    # Print the selection flow
    print_selection_flow()
    
    # Create visualizations
    success = create_selection_visualizations()
    
    if success:
        print(f"\n✅ STOCK SELECTION BREAKDOWN COMPLETE!")
        print(f"\nKey Takeaways:")
        print(f"• ETF-based selection is efficient and transparent")
        print(f"• Weight thresholds ensure meaningful positions")
        print(f"• Overlap analysis shows natural diversification")
        print(f"• Multiple portfolio strategies utilize stocks differently")
        print(f"• Process is fully auditable with detailed CSV exports")
        
        print(f"\n📁 Files Generated:")
        print(f"• stock_selection_analysis.png - Visual charts")
        print(f"• stock_selection_sources.csv - Stock-ETF mapping")  
        print(f"• stock_selection_final_universe.csv - Final universe")
        print(f"• stock_selection_etf_holdings.csv - ETF holdings detail")
        print(f"• stock_selection_statistics.csv - Summary statistics")
    else:
        print(f"\n❌ Could not create visualizations. Run stock selection analysis first.")


if __name__ == "__main__":
    main()