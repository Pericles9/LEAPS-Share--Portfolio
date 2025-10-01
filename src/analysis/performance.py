"""
Analysis Tools

Comprehensive analysis tools for financial data and portfolio performance.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    
from typing import Dict, List, Optional, Tuple
from scipy import stats
import seaborn as sns


class PerformanceAnalyzer:
    """Analyze portfolio and stock performance."""
    
    def __init__(self):
        """Initialize the performance analyzer."""
        pass
    
    def calculate_performance_metrics(self, returns: pd.Series, 
                                    risk_free_rate: float = 0.02) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            returns: Return series
            risk_free_rate: Risk-free rate for calculations
            
        Returns:
            Dictionary of performance metrics
        """
        if len(returns) == 0:
            return {}
            
        # Basic statistics
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + returns.mean())**252 - 1
        annualized_volatility = returns.std() * np.sqrt(252)
        
        # Risk-adjusted metrics
        if annualized_volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        else:
            sharpe_ratio = 0
        
        # Calculate Sortino ratio (downside deviation)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_deviation = negative_returns.std() * np.sqrt(252)
            sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else np.inf
        else:
            sortino_ratio = np.inf
        
        # Maximum drawdown
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else np.inf
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
        
        # Conditional Value at Risk (Expected Shortfall)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        
        # Skewness and Kurtosis
        skewness = stats.skew(returns) if len(returns) > 1 else 0
        kurtosis = stats.kurtosis(returns) if len(returns) > 1 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'skewness': skewness,
            'kurtosis': kurtosis
        }