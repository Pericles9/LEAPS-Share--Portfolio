"""Utility functions for the portfolio system."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any


def validate_weights(weights: List[float], tolerance: float = 1e-6) -> bool:
    """
    Validate that portfolio weights sum to 1.
    
    Args:
        weights: List of portfolio weights
        tolerance: Tolerance for sum validation
        
    Returns:
        True if weights are valid
    """
    return abs(sum(weights) - 1.0) <= tolerance


def annualize_returns(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Annualize returns.
    
    Args:
        returns: Return series
        periods_per_year: Number of periods per year
        
    Returns:
        Annualized return
    """
    return (1 + returns.mean()) ** periods_per_year - 1


def annualize_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Annualize volatility.
    
    Args:
        returns: Return series
        periods_per_year: Number of periods per year
        
    Returns:
        Annualized volatility
    """
    return returns.std() * np.sqrt(periods_per_year)


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a decimal value as percentage.
    
    Args:
        value: Decimal value
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: float, currency: str = "$") -> str:
    """
    Format a value as currency.
    
    Args:
        value: Numeric value
        currency: Currency symbol
        
    Returns:
        Formatted currency string
    """
    return f"{currency}{value:,.2f}"


def generate_report_summary(metrics: Dict[str, float]) -> str:
    """
    Generate a summary report from performance metrics.
    
    Args:
        metrics: Dictionary of performance metrics
        
    Returns:
        Formatted summary string
    """
    summary = "Portfolio Performance Summary\n"
    summary += "=" * 30 + "\n\n"
    
    summary += f"Total Return: {format_percentage(metrics.get('total_return', 0))}\n"
    summary += f"Annualized Return: {format_percentage(metrics.get('annualized_return', 0))}\n"
    summary += f"Annualized Volatility: {format_percentage(metrics.get('annualized_volatility', 0))}\n"
    summary += f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}\n"
    summary += f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}\n"
    summary += f"Maximum Drawdown: {format_percentage(metrics.get('max_drawdown', 0))}\n"
    summary += f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}\n"
    summary += f"VaR (95%): {format_percentage(metrics.get('var_95', 0))}\n"
    summary += f"CVaR (95%): {format_percentage(metrics.get('cvar_95', 0))}\n"
    
    return summary