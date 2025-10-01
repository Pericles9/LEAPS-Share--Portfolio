"""Example usage of the portfolio options pricing system."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from src.models.black_scholes import BlackScholesModel
from src.portfolio.optimizer import PortfolioOptimizer
from src.data.market_data import MarketDataFetcher
from src.analysis.performance import PerformanceAnalyzer
from src.utils.helpers import format_percentage, format_currency


def main():
    """Main example demonstrating the portfolio system."""
    
    print("Portfolio Options Pricing System - Example Usage")
    print("=" * 50)
    
    # 1. Options Pricing Example
    print("\n1. Options Pricing with Black-Scholes Model")
    print("-" * 40)
    
    bs_model = BlackScholesModel()
    
    # Example option parameters
    S = 100    # Current stock price
    K = 105    # Strike price
    T = 0.25   # Time to expiration (3 months)
    r = 0.05   # Risk-free rate
    sigma = 0.2  # Volatility
    
    # Calculate call option price
    call_price = bs_model.calculate_price(S, K, T, r, sigma, 'call')
    put_price = bs_model.calculate_price(S, K, T, r, sigma, 'put')
    
    print(f"Call Option Price: {format_currency(call_price)}")
    print(f"Put Option Price: {format_currency(put_price)}")
    
    # Calculate Greeks
    call_greeks = bs_model.calculate_greeks(S, K, T, r, sigma, 'call')
    print(f"\nCall Option Greeks:")
    for greek, value in call_greeks.items():
        print(f"  {greek.capitalize()}: {value:.4f}")
    
    # 2. Market Data Example (using synthetic data)
    print("\n\n2. Market Data and Portfolio Analysis")
    print("-" * 40)
    
    # Create synthetic data for demonstration
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
    print(f"Creating synthetic data for: {', '.join(symbols)}")
    
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    synthetic_returns = {}
    for symbol in symbols:
        returns = np.random.normal(0.001, 0.02, len(dates))
        synthetic_returns[symbol] = returns
    
    returns_df = pd.DataFrame(synthetic_returns, index=dates)
    print(f"Generated returns data shape: {returns_df.shape}")
    
    # 3. Portfolio Optimization Example
    print("\n\n3. Portfolio Optimization")
    print("-" * 40)
    
    optimizer = PortfolioOptimizer(risk_free_rate=0.02)
    
    try:
        # Optimize for maximum Sharpe ratio
        optimal_portfolio = optimizer.optimize_portfolio(
            returns_df, 
            optimization_target='sharpe'
        )
        
        print("Optimal Portfolio (Max Sharpe Ratio):")
        print(f"  Expected Return: {format_percentage(optimal_portfolio.expected_return)}")
        print(f"  Volatility: {format_percentage(optimal_portfolio.volatility)}")
        print(f"  Sharpe Ratio: {optimal_portfolio.sharpe_ratio:.3f}")
        
        print("\n  Optimal Weights:")
        for symbol, weight in zip(optimal_portfolio.symbols, optimal_portfolio.weights):
            print(f"    {symbol}: {format_percentage(weight)}")
        
        # Calculate VaR
        var_95 = optimizer.calculate_var(returns_df, optimal_portfolio.weights)
        print(f"\n  VaR (95%): {format_percentage(var_95)}")
        
    except Exception as e:
        print(f"Error in portfolio optimization: {e}")
    
    # 4. Performance Analysis Example
    print("\n\n4. Performance Analysis")
    print("-" * 40)
    
    analyzer = PerformanceAnalyzer()
    
    # Analyze first stock's performance
    sample_returns = returns_df.iloc[:, 0].dropna()
    
    if len(sample_returns) > 0:
        metrics = analyzer.calculate_performance_metrics(sample_returns)
        
        print(f"Performance Metrics for {symbols[0]}:")
        print(f"  Total Return: {format_percentage(metrics.get('total_return', 0))}")
        print(f"  Annualized Return: {format_percentage(metrics.get('annualized_return', 0))}")
        print(f"  Annualized Volatility: {format_percentage(metrics.get('annualized_volatility', 0))}")
        print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"  Maximum Drawdown: {format_percentage(metrics.get('max_drawdown', 0))}")
        print(f"  VaR (95%): {format_percentage(metrics.get('var_95', 0))}")
    
    # 5. Monte Carlo Simulation Example
    print("\n\n5. Monte Carlo Simulation")
    print("-" * 40)
    
    if 'optimal_portfolio' in locals():
        try:
            simulation_results = optimizer.monte_carlo_simulation(
                returns_df, 
                optimal_portfolio.weights,
                initial_investment=10000,
                time_horizon=252,  # 1 year
                num_simulations=100  # Reduced for faster execution
            )
            
            print("Monte Carlo Simulation Results (1 Year, $10,000 initial):")
            print(f"  5th Percentile: {format_currency(simulation_results['percentiles']['5th'])}")
            print(f"  25th Percentile: {format_currency(simulation_results['percentiles']['25th'])}")
            print(f"  Median: {format_currency(simulation_results['percentiles']['50th'])}")
            print(f"  75th Percentile: {format_currency(simulation_results['percentiles']['75th'])}")
            print(f"  95th Percentile: {format_currency(simulation_results['percentiles']['95th'])}")
            
        except Exception as e:
            print(f"Error in Monte Carlo simulation: {e}")
    
    print("\n" + "=" * 50)
    print("Example completed successfully!")
    print("\nNext steps:")
    print("- Customize the configuration in config/settings.py")
    print("- Add your API keys for real market data")
    print("- Explore Jupyter notebooks for interactive analysis")
    print("- Run the test suite with: pytest tests/")


if __name__ == "__main__":
    main()