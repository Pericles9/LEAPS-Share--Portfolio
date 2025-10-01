"""
Portfolio Optimization Module

Modern Portfolio Theory implementation for optimal asset allocation.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: np.ndarray
    symbols: List[str]


class PortfolioOptimizer:
    """Portfolio optimization using Modern Portfolio Theory."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize portfolio optimizer.
        
        Args:
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
        """
        self.risk_free_rate = risk_free_rate
        
    def calculate_portfolio_metrics(self, weights: np.ndarray, returns: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Calculate portfolio expected return, volatility, and Sharpe ratio.
        
        Args:
            weights: Portfolio weights
            returns: Historical returns DataFrame
            
        Returns:
            Tuple of (expected_return, volatility, sharpe_ratio)
        """
        # Calculate expected returns and covariance matrix
        mean_returns = returns.mean() * 252  # Annualized
        cov_matrix = returns.cov() * 252    # Annualized
        
        # Portfolio expected return
        portfolio_return = np.sum(weights * mean_returns)
        
        # Portfolio volatility
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Sharpe ratio
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        
        return portfolio_return, portfolio_volatility, sharpe_ratio
    
    def optimize_portfolio(self, returns: pd.DataFrame, 
                          optimization_target: str = 'sharpe',
                          min_weight: float = 0.0,
                          max_weight: float = 1.0) -> PortfolioMetrics:
        """
        Optimize portfolio weights.
        
        Args:
            returns: Historical returns DataFrame
            optimization_target: 'sharpe', 'min_volatility', or 'max_return'
            min_weight: Minimum weight constraint
            max_weight: Maximum weight constraint
            
        Returns:
            PortfolioMetrics object with optimal weights and metrics
        """
        n_assets = len(returns.columns)
        
        # Initial guess (equal weights)
        initial_weights = np.array([1/n_assets] * n_assets)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        
        # Define objective function based on target
        if optimization_target == 'sharpe':
            def objective(weights):
                _, _, sharpe = self.calculate_portfolio_metrics(weights, returns)
                return -sharpe  # Minimize negative Sharpe ratio
        elif optimization_target == 'min_volatility':
            def objective(weights):
                _, volatility, _ = self.calculate_portfolio_metrics(weights, returns)
                return volatility
        elif optimization_target == 'max_return':
            def objective(weights):
                expected_return, _, _ = self.calculate_portfolio_metrics(weights, returns)
                return -expected_return  # Minimize negative return
        else:
            raise ValueError("optimization_target must be 'sharpe', 'min_volatility', or 'max_return'")
        
        # Optimize
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'disp': False}
        )
        
        if not result.success:
            raise RuntimeError(f"Optimization failed: {result.message}")
        
        optimal_weights = result.x
        expected_return, volatility, sharpe_ratio = self.calculate_portfolio_metrics(
            optimal_weights, returns
        )
        
        return PortfolioMetrics(
            expected_return=expected_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            weights=optimal_weights,
            symbols=list(returns.columns)
        )
    
    def calculate_var(self, returns: pd.DataFrame, weights: np.ndarray, 
                     confidence_level: float = 0.05, 
                     time_horizon: int = 1) -> float:
        """
        Calculate Value at Risk (VaR) for a portfolio.
        
        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights
            confidence_level: Confidence level (e.g., 0.05 for 95% VaR)
            time_horizon: Time horizon in days
            
        Returns:
            VaR value
        """
        # Calculate portfolio returns
        portfolio_returns = (returns * weights).sum(axis=1)
        
        # Scale for time horizon
        portfolio_std = portfolio_returns.std() * np.sqrt(time_horizon)
        portfolio_mean = portfolio_returns.mean() * time_horizon
        
        # Calculate VaR using normal distribution assumption
        from scipy.stats import norm
        var = norm.ppf(confidence_level) * portfolio_std + portfolio_mean
        
        return -var  # VaR is typically expressed as a positive number
    
    def monte_carlo_simulation(self, returns: pd.DataFrame, weights: np.ndarray,
                             initial_investment: float = 10000,
                             time_horizon: int = 252,
                             num_simulations: int = 1000) -> Dict[str, np.ndarray]:
        """
        Run Monte Carlo simulation for portfolio performance.
        
        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights
            initial_investment: Initial investment amount
            time_horizon: Simulation time horizon in days
            num_simulations: Number of simulation runs
            
        Returns:
            Dictionary with simulation results
        """
        # Calculate portfolio statistics
        portfolio_returns = (returns * weights).sum(axis=1)
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        
        # Run simulations
        simulation_results = []
        
        for _ in range(num_simulations):
            # Generate random returns
            random_returns = np.random.normal(mean_return, std_return, time_horizon)
            
            # Calculate cumulative portfolio value
            portfolio_values = [initial_investment]
            for daily_return in random_returns:
                new_value = portfolio_values[-1] * (1 + daily_return)
                portfolio_values.append(new_value)
            
            simulation_results.append(portfolio_values)
        
        simulation_array = np.array(simulation_results)
        
        return {
            'simulations': simulation_array,
            'final_values': simulation_array[:, -1],
            'percentiles': {
                '5th': np.percentile(simulation_array[:, -1], 5),
                '25th': np.percentile(simulation_array[:, -1], 25),
                '50th': np.percentile(simulation_array[:, -1], 50),
                '75th': np.percentile(simulation_array[:, -1], 75),
                '95th': np.percentile(simulation_array[:, -1], 95)
            }
        }