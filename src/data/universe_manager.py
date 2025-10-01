"""
Portfolio Universe Manager

Manages the universe of tradable equities and builds various portfolio strategies.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

from .market_data import MarketDataFetcher
from .etf_holdings import ETFHoldingsManager
from .tv_data_fetcher import TradingViewDataFetcher
from ..portfolio.optimizer import PortfolioOptimizer, PortfolioMetrics
from ..analysis.performance import PerformanceAnalyzer
from ..utils.helpers import format_percentage, format_currency


@dataclass
class UniverseStock:
    """Information about a stock in the universe."""
    symbol: str
    sector: str
    market_cap: float
    beta: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    avg_volume: Optional[float] = None


@dataclass 
class PortfolioStrategy:
    """Portfolio strategy definition."""
    name: str
    description: str
    symbols: List[str]
    weights: Optional[np.ndarray] = None
    metrics: Optional[PortfolioMetrics] = None
    monte_carlo_results: Optional[Dict] = None


class PortfolioUniverseManager:
    """Manage universe of stocks and build portfolio strategies."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize the universe manager.
        
        Args:
            risk_free_rate: Risk-free rate for calculations
        """
        self.risk_free_rate = risk_free_rate
        self.fetcher = MarketDataFetcher()
        self.etf_manager = ETFHoldingsManager()
        self.optimizer = PortfolioOptimizer(risk_free_rate)
        self.analyzer = PerformanceAnalyzer()
        self.universe: List[UniverseStock] = []
        self.universe_data: Dict = {}
        self.strategies: List[PortfolioStrategy] = []
        
    def add_universe_stocks(self, symbols: List[str], fetch_fundamentals: bool = True) -> None:
        """
        Add stocks to the trading universe.
        
        Args:
            symbols: List of stock symbols
            fetch_fundamentals: Whether to fetch fundamental data
        """
        print(f"Adding {len(symbols)} stocks to universe...")
        
        if fetch_fundamentals:
            self._fetch_stock_fundamentals(symbols)
        else:
            # Add stocks with minimal info
            for symbol in symbols:
                self.universe.append(UniverseStock(
                    symbol=symbol,
                    sector="Unknown",
                    market_cap=0.0
                ))
        
        print(f"Universe now contains {len(self.universe)} stocks")
    
    def add_universe_from_etfs(self, etf_symbols: List[str], 
                              min_weight: float = 0.5,
                              top_n_per_etf: Optional[int] = 20,
                              fetch_fundamentals: bool = True) -> None:
        """
        Add stocks to universe by extracting holdings from ETFs.
        
        Args:
            etf_symbols: List of ETF symbols
            min_weight: Minimum weight threshold for including stocks
            top_n_per_etf: Maximum holdings per ETF
            fetch_fundamentals: Whether to fetch fundamental data
        """
        print(f"Building universe from {len(etf_symbols)} ETFs...")
        
        # Get stock symbols from ETFs
        stock_symbols = self.etf_manager.build_universe_from_etfs(
            etf_symbols, min_weight, top_n_per_etf
        )
        
        if not stock_symbols:
            print("No stocks found in ETF holdings")
            return
        
        # Add stocks to universe
        self.add_universe_stocks(stock_symbols, fetch_fundamentals)
        
        # Store ETF source information
        self.etf_source_info = {
            'etf_symbols': etf_symbols,
            'min_weight': min_weight,
            'top_n_per_etf': top_n_per_etf,
            'extracted_stocks': len(stock_symbols)
        }
        
        print(f"✓ Successfully built universe from ETFs")
    
    def get_popular_etfs(self) -> Dict[str, str]:
        """Get dictionary of popular ETFs for reference."""
        return self.etf_manager.get_popular_sector_etfs()
    
    def suggest_etfs_by_theme(self, theme: str) -> List[str]:
        """Suggest ETFs based on investment theme."""
        return self.etf_manager.suggest_etfs_by_theme(theme)
    
    def print_etf_holdings(self, etf_symbol: str) -> None:
        """Print detailed ETF holdings information."""
        self.etf_manager.print_etf_info(etf_symbol)
    
    def _fetch_stock_fundamentals(self, symbols: List[str]) -> None:
        """Fetch fundamental data for stocks."""
        def fetch_single_stock(symbol: str) -> Optional[UniverseStock]:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                return UniverseStock(
                    symbol=symbol,
                    sector=info.get('sector', 'Unknown'),
                    market_cap=info.get('marketCap', 0),
                    beta=info.get('beta'),
                    pe_ratio=info.get('trailingPE'),
                    dividend_yield=info.get('dividendYield'),
                    avg_volume=info.get('averageVolume')
                )
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                return UniverseStock(symbol=symbol, sector="Unknown", market_cap=0.0)
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(fetch_single_stock, symbol): symbol 
                              for symbol in symbols}
            
            for future in as_completed(future_to_symbol):
                stock = future.result()
                if stock:
                    self.universe.append(stock)
    
    def fetch_universe_data(self, period: str = "1y", max_workers: int = 10) -> Dict:
        """
        Fetch historical data for all stocks in universe.
        
        Args:
            period: Data period
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary with stock data
        """
        symbols = [stock.symbol for stock in self.universe]
        print(f"Fetching historical data for {len(symbols)} stocks...")
        
        # Use TradingView data fetcher
        tv_fetcher = TradingViewDataFetcher()
        
        # Convert period to days
        if period == "1y":
            days = 365
        elif period == "6mo":
            days = 180
        elif period == "3mo":
            days = 90
        elif period == "1mo":
            days = 30
        else:
            days = 365  # Default to 1 year
        
        def fetch_stock_data(symbol: str) -> Tuple[str, Optional[pd.DataFrame]]:
            try:
                data = tv_fetcher.get_stock_data(symbol, days=days)
                if data is not None and len(data) > 30:
                    # Return close prices
                    if 'close' in data.columns:
                        return symbol, data['close']
                    elif 'Close' in data.columns:
                        return symbol, data['Close']
                return symbol, None
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                return symbol, None
        
        price_data = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(fetch_stock_data, symbol): symbol 
                              for symbol in symbols}
            
            for future in as_completed(future_to_symbol):
                symbol, data = future.result()
                if data is not None:
                    price_data[symbol] = data
        
        if price_data:
            # Create combined DataFrame
            prices_df = pd.DataFrame(price_data).dropna()
            returns_df = self.fetcher.calculate_returns(prices_df)
            
            self.universe_data = {
                'prices': prices_df,
                'returns': returns_df,
                'symbols': list(prices_df.columns)
            }
            
            print(f"Successfully fetched data for {len(prices_df.columns)} stocks")
            print(f"Date range: {prices_df.index[0].date()} to {prices_df.index[-1].date()}")
        
        return self.universe_data
    
    def build_portfolio_strategies(self) -> List[PortfolioStrategy]:
        """
        Build various portfolio strategies from the universe.
        
        Returns:
            List of portfolio strategies
        """
        if not self.universe_data or 'returns' not in self.universe_data:
            raise ValueError("Universe data not available. Call fetch_universe_data() first.")
        
        returns_df = self.universe_data['returns']
        strategies = []
        
        # Strategy 1: Equal Weight Portfolio
        strategies.append(PortfolioStrategy(
            name="Equal Weight",
            description="Equal weighting across all stocks in universe",
            symbols=list(returns_df.columns)
        ))
        
        # Strategy 2: Market Cap Weighted (if available)
        market_cap_stocks = [stock for stock in self.universe if stock.market_cap > 0]
        if len(market_cap_stocks) >= 5:
            market_cap_symbols = [stock.symbol for stock in market_cap_stocks]
            market_cap_symbols = [s for s in market_cap_symbols if s in returns_df.columns]
            
            if market_cap_symbols:
                strategies.append(PortfolioStrategy(
                    name="Market Cap Weighted",
                    description="Portfolio weighted by market capitalization",
                    symbols=market_cap_symbols
                ))
        
        # Strategy 3: Maximum Sharpe Ratio (full universe)
        if len(returns_df.columns) >= 3:
            strategies.append(PortfolioStrategy(
                name="Max Sharpe Ratio (All)",
                description="Maximum Sharpe ratio optimization using all stocks",
                symbols=list(returns_df.columns)
            ))
        
        # Strategy 4: Minimum Volatility
        if len(returns_df.columns) >= 3:
            strategies.append(PortfolioStrategy(
                name="Minimum Volatility",
                description="Minimum volatility portfolio using all stocks", 
                symbols=list(returns_df.columns)
            ))
        
        # Strategy 5: Sector Diversified (if sector data available)
        sector_groups = self._group_by_sector()
        if len(sector_groups) >= 3:
            sector_symbols = []
            for sector, stocks in sector_groups.items():
                # Take top 2-3 stocks per sector by market cap
                sector_stocks = sorted(stocks, key=lambda x: x.market_cap, reverse=True)[:2]
                sector_symbols.extend([s.symbol for s in sector_stocks if s.symbol in returns_df.columns])
            
            if len(sector_symbols) >= 5:
                strategies.append(PortfolioStrategy(
                    name="Sector Diversified",
                    description="Diversified portfolio with representation from each sector",
                    symbols=sector_symbols
                ))
        
        # Strategy 6: High Beta Portfolio
        high_beta_stocks = [stock for stock in self.universe 
                          if stock.beta and stock.beta > 1.2 and stock.symbol in returns_df.columns]
        if len(high_beta_stocks) >= 5:
            high_beta_symbols = [stock.symbol for stock in high_beta_stocks[:10]]  # Top 10
            strategies.append(PortfolioStrategy(
                name="High Beta",
                description="Portfolio of high-beta (>1.2) stocks",
                symbols=high_beta_symbols
            ))
        
        # Strategy 7: Low Beta Portfolio  
        low_beta_stocks = [stock for stock in self.universe 
                         if stock.beta and stock.beta < 0.8 and stock.symbol in returns_df.columns]
        if len(low_beta_stocks) >= 5:
            low_beta_symbols = [stock.symbol for stock in low_beta_stocks[:10]]  # Top 10
            strategies.append(PortfolioStrategy(
                name="Low Beta",
                description="Portfolio of low-beta (<0.8) stocks",
                symbols=low_beta_symbols
            ))
        
        # Strategy 8: Dividend Focused
        dividend_stocks = [stock for stock in self.universe 
                         if stock.dividend_yield and stock.dividend_yield > 0.02 
                         and stock.symbol in returns_df.columns]
        if len(dividend_stocks) >= 5:
            dividend_symbols = [stock.symbol for stock in 
                              sorted(dividend_stocks, key=lambda x: x.dividend_yield, reverse=True)[:15]]
            strategies.append(PortfolioStrategy(
                name="Dividend Focused",
                description="Portfolio focused on dividend-paying stocks (>2% yield)",
                symbols=dividend_symbols
            ))
        
        self.strategies = strategies
        print(f"Built {len(strategies)} portfolio strategies")
        
        return strategies
    
    def _group_by_sector(self) -> Dict[str, List[UniverseStock]]:
        """Group stocks by sector."""
        sectors = {}
        for stock in self.universe:
            if stock.sector not in sectors:
                sectors[stock.sector] = []
            sectors[stock.sector].append(stock)
        return sectors
    
    def optimize_strategies(self) -> None:
        """Optimize all portfolio strategies."""
        if not self.strategies:
            raise ValueError("No strategies available. Call build_portfolio_strategies() first.")
        
        returns_df = self.universe_data['returns']
        
        print("Optimizing portfolio strategies...")
        
        for i, strategy in enumerate(self.strategies):
            try:
                # Filter returns for strategy symbols
                strategy_returns = returns_df[strategy.symbols].dropna()
                
                if len(strategy_returns.columns) < 2:
                    print(f"Skipping {strategy.name}: insufficient data")
                    continue
                
                # Determine optimization approach
                if strategy.name == "Equal Weight":
                    # Equal weights
                    n_assets = len(strategy.symbols)
                    weights = np.array([1/n_assets] * n_assets)
                    
                    # Calculate metrics manually
                    portfolio_return, volatility, sharpe = self.optimizer.calculate_portfolio_metrics(
                        weights, strategy_returns
                    )
                    
                    strategy.metrics = PortfolioMetrics(
                        expected_return=portfolio_return,
                        volatility=volatility,
                        sharpe_ratio=sharpe,
                        weights=weights,
                        symbols=strategy.symbols
                    )
                    
                elif strategy.name == "Market Cap Weighted":
                    # Market cap weights
                    market_caps = []
                    for symbol in strategy.symbols:
                        stock = next((s for s in self.universe if s.symbol == symbol), None)
                        market_caps.append(stock.market_cap if stock else 1.0)
                    
                    weights = np.array(market_caps)
                    weights = weights / weights.sum()  # Normalize
                    
                    portfolio_return, volatility, sharpe = self.optimizer.calculate_portfolio_metrics(
                        weights, strategy_returns
                    )
                    
                    strategy.metrics = PortfolioMetrics(
                        expected_return=portfolio_return,
                        volatility=volatility,
                        sharpe_ratio=sharpe,
                        weights=weights,
                        symbols=strategy.symbols
                    )
                    
                elif "Max Sharpe" in strategy.name:
                    # Optimize for maximum Sharpe ratio
                    strategy.metrics = self.optimizer.optimize_portfolio(
                        strategy_returns, optimization_target='sharpe'
                    )
                    
                elif "Minimum Volatility" in strategy.name:
                    # Optimize for minimum volatility
                    strategy.metrics = self.optimizer.optimize_portfolio(
                        strategy_returns, optimization_target='min_volatility'
                    )
                    
                else:
                    # Default to equal weight for other strategies
                    n_assets = len(strategy.symbols)
                    weights = np.array([1/n_assets] * n_assets)
                    
                    portfolio_return, volatility, sharpe = self.optimizer.calculate_portfolio_metrics(
                        weights, strategy_returns
                    )
                    
                    strategy.metrics = PortfolioMetrics(
                        expected_return=portfolio_return,
                        volatility=volatility,
                        sharpe_ratio=sharpe,
                        weights=weights,
                        symbols=strategy.symbols
                    )
                
                print(f"✓ Optimized {strategy.name}: Sharpe={strategy.metrics.sharpe_ratio:.3f}")
                
            except Exception as e:
                print(f"Error optimizing {strategy.name}: {e}")
                continue
    
    def run_monte_carlo_simulations(self, num_simulations: int = 1000, 
                                  time_horizon: int = 252, 
                                  initial_investment: float = 10000) -> None:
        """
        Run Monte Carlo simulations for all optimized strategies.
        
        Args:
            num_simulations: Number of simulation runs
            time_horizon: Time horizon in days
            initial_investment: Initial investment amount
        """
        if not self.strategies:
            raise ValueError("No strategies available")
        
        returns_df = self.universe_data['returns']
        
        print(f"Running Monte Carlo simulations ({num_simulations} runs, {time_horizon} days)...")
        
        for strategy in self.strategies:
            if not strategy.metrics:
                continue
                
            try:
                strategy_returns = returns_df[strategy.symbols].dropna()
                
                results = self.optimizer.monte_carlo_simulation(
                    strategy_returns,
                    strategy.metrics.weights,
                    initial_investment=initial_investment,
                    time_horizon=time_horizon,
                    num_simulations=num_simulations
                )
                
                strategy.monte_carlo_results = results
                
                median_return = (results['percentiles']['50th'] - initial_investment) / initial_investment
                print(f"✓ {strategy.name}: Median return = {format_percentage(median_return)}")
                
            except Exception as e:
                print(f"Error in Monte Carlo for {strategy.name}: {e}")
                continue
    
    def get_strategy_summary(self) -> pd.DataFrame:
        """Get summary of all strategies."""
        summary_data = []
        
        for strategy in self.strategies:
            if strategy.metrics:
                summary_data.append({
                    'Strategy': strategy.name,
                    'Description': strategy.description,
                    'Num_Assets': len(strategy.symbols),
                    'Expected_Return': strategy.metrics.expected_return,
                    'Volatility': strategy.metrics.volatility,
                    'Sharpe_Ratio': strategy.metrics.sharpe_ratio,
                    'Top_Holdings': ', '.join(strategy.symbols[:5]) + ('...' if len(strategy.symbols) > 5 else '')
                })
        
        return pd.DataFrame(summary_data)
    
    def get_monte_carlo_summary(self) -> pd.DataFrame:
        """Get Monte Carlo simulation summary."""
        mc_data = []
        
        for strategy in self.strategies:
            if strategy.monte_carlo_results:
                results = strategy.monte_carlo_results
                mc_data.append({
                    'Strategy': strategy.name,
                    '5th_Percentile': results['percentiles']['5th'],
                    '25th_Percentile': results['percentiles']['25th'],
                    'Median': results['percentiles']['50th'],
                    '75th_Percentile': results['percentiles']['75th'],
                    '95th_Percentile': results['percentiles']['95th']
                })
        
        return pd.DataFrame(mc_data)
    
    def print_detailed_results(self) -> None:
        """Print detailed results for all strategies."""
        print("\n" + "="*80)
        print("PORTFOLIO STRATEGIES ANALYSIS RESULTS")
        print("="*80)
        
        # Strategy Summary
        print("\n1. STRATEGY SUMMARY")
        print("-" * 50)
        summary_df = self.get_strategy_summary()
        if not summary_df.empty:
            for _, row in summary_df.iterrows():
                print(f"\n{row['Strategy']}:")
                print(f"  Description: {row['Description']}")
                print(f"  Assets: {row['Num_Assets']}")
                print(f"  Expected Return: {format_percentage(row['Expected_Return'])}")
                print(f"  Volatility: {format_percentage(row['Volatility'])}")
                print(f"  Sharpe Ratio: {row['Sharpe_Ratio']:.3f}")
                print(f"  Top Holdings: {row['Top_Holdings']}")
        
        # Monte Carlo Results
        print("\n\n2. MONTE CARLO SIMULATION RESULTS")
        print("-" * 50)
        mc_df = self.get_monte_carlo_summary()
        if not mc_df.empty:
            for _, row in mc_df.iterrows():
                print(f"\n{row['Strategy']}:")
                print(f"  5th Percentile: {format_currency(row['5th_Percentile'])}")
                print(f"  25th Percentile: {format_currency(row['25th_Percentile'])}")
                print(f"  Median: {format_currency(row['Median'])}")
                print(f"  75th Percentile: {format_currency(row['75th_Percentile'])}")
                print(f"  95th Percentile: {format_currency(row['95th_Percentile'])}")
        
        # Best Performing Strategies
        print("\n\n3. BEST PERFORMING STRATEGIES")
        print("-" * 50)
        if not summary_df.empty:
            best_sharpe = summary_df.loc[summary_df['Sharpe_Ratio'].idxmax()]
            best_return = summary_df.loc[summary_df['Expected_Return'].idxmax()]
            lowest_vol = summary_df.loc[summary_df['Volatility'].idxmin()]
            
            print(f"Best Sharpe Ratio: {best_sharpe['Strategy']} ({best_sharpe['Sharpe_Ratio']:.3f})")
            print(f"Highest Expected Return: {best_return['Strategy']} ({format_percentage(best_return['Expected_Return'])})")
            print(f"Lowest Volatility: {lowest_vol['Strategy']} ({format_percentage(lowest_vol['Volatility'])})")
        
        print("\n" + "="*80)