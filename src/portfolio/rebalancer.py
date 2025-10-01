"""
Portfolio Rebalancing Module

Advanced rebalancing functionality for the portfolio management system.
Supports various rebalancing frequencies, thresholds, and strategies.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json


class RebalanceFrequency(Enum):
    """Rebalancing frequency options."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMI_ANNUAL = "Semi-Annual"
    ANNUAL = "Annual"


class RebalanceTrigger(Enum):
    """Rebalancing trigger types."""
    SCHEDULED = "Scheduled"
    THRESHOLD = "Threshold"
    MANUAL = "Manual"
    VOLATILITY = "Volatility"
    PERFORMANCE = "Performance"


@dataclass
class RebalanceEvent:
    """Record of a rebalancing event."""
    date: datetime
    trigger: RebalanceTrigger
    portfolio_name: str
    trades: List[Dict]
    cost: float
    reason: str
    before_weights: Dict[str, float]
    after_weights: Dict[str, float]


@dataclass
class RebalanceConfig:
    """Rebalancing configuration."""
    frequency: RebalanceFrequency
    threshold_percent: float
    auto_rebalance: bool
    trading_cost_percent: float
    min_trade_amount: float
    max_trades_per_period: int
    volatility_threshold: float
    performance_threshold: float


class PortfolioRebalancer:
    """Advanced portfolio rebalancing system."""
    
    def __init__(self, config: RebalanceConfig = None):
        """Initialize the rebalancer."""
        self.config = config or RebalanceConfig(
            frequency=RebalanceFrequency.MONTHLY,
            threshold_percent=5.0,
            auto_rebalance=False,
            trading_cost_percent=0.1,
            min_trade_amount=100.0,
            max_trades_per_period=20,
            volatility_threshold=0.02,
            performance_threshold=0.05
        )
        
        self.rebalance_history: List[RebalanceEvent] = []
        self.last_rebalance_date: Optional[datetime] = None
        
    def analyze_drift(self, current_weights: Dict[str, float], 
                     target_weights: Dict[str, float],
                     portfolio_value: float) -> Dict:
        """
        Analyze portfolio drift from target allocation.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with drift analysis
        """
        drift_analysis = {
            'total_drift': 0.0,
            'stock_drifts': {},
            'largest_drift': {'symbol': None, 'drift': 0.0},
            'rebalance_needed': False,
            'suggested_trades': [],
            'estimated_cost': 0.0
        }
        
        # Calculate drift for each stock
        for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
            current_weight = current_weights.get(symbol, 0.0)
            target_weight = target_weights.get(symbol, 0.0)
            
            drift = abs(current_weight - target_weight)
            drift_analysis['stock_drifts'][symbol] = {
                'current_weight': current_weight,
                'target_weight': target_weight,
                'drift': drift,
                'drift_percent': (drift / target_weight * 100) if target_weight > 0 else 0
            }
            
            # Track largest drift
            if drift > drift_analysis['largest_drift']['drift']:
                drift_analysis['largest_drift'] = {'symbol': symbol, 'drift': drift}
            
            # Accumulate total drift
            drift_analysis['total_drift'] += drift
        
        # Determine if rebalancing is needed
        max_drift_percent = max([stock['drift_percent'] for stock in drift_analysis['stock_drifts'].values()])
        drift_analysis['rebalance_needed'] = max_drift_percent > self.config.threshold_percent
        
        # Generate suggested trades if rebalancing is needed
        if drift_analysis['rebalance_needed']:
            trades, cost = self._generate_rebalance_trades(
                current_weights, target_weights, portfolio_value
            )
            drift_analysis['suggested_trades'] = trades
            drift_analysis['estimated_cost'] = cost
        
        return drift_analysis
    
    def _generate_rebalance_trades(self, current_weights: Dict[str, float],
                                 target_weights: Dict[str, float],
                                 portfolio_value: float) -> Tuple[List[Dict], float]:
        """Generate optimal rebalancing trades."""
        trades = []
        total_cost = 0.0
        
        # Calculate required trades
        for symbol in set(list(current_weights.keys()) + list(target_weights.keys())):
            current_weight = current_weights.get(symbol, 0.0)
            target_weight = target_weights.get(symbol, 0.0)
            
            weight_diff = target_weight - current_weight
            trade_value = weight_diff * portfolio_value
            
            # Only create trade if above minimum threshold
            if abs(trade_value) >= self.config.min_trade_amount:
                trade = {
                    'symbol': symbol,
                    'action': 'BUY' if weight_diff > 0 else 'SELL',
                    'current_weight': current_weight,
                    'target_weight': target_weight,
                    'trade_amount': abs(trade_value),
                    'trade_weight': abs(weight_diff)
                }
                trades.append(trade)
                
                # Calculate trading cost
                cost = abs(trade_value) * (self.config.trading_cost_percent / 100)
                total_cost += cost
        
        # Sort trades by impact (largest first)
        trades.sort(key=lambda x: x['trade_amount'], reverse=True)
        
        # Limit number of trades if necessary
        if len(trades) > self.config.max_trades_per_period:
            trades = trades[:self.config.max_trades_per_period]
            # Recalculate cost for limited trades
            total_cost = sum(trade['trade_amount'] * (self.config.trading_cost_percent / 100) 
                           for trade in trades)
        
        return trades, total_cost
    
    def should_rebalance(self, current_weights: Dict[str, float],
                        target_weights: Dict[str, float],
                        current_date: datetime = None,
                        market_volatility: float = None,
                        portfolio_performance: float = None) -> Tuple[bool, RebalanceTrigger, str]:
        """
        Determine if portfolio should be rebalanced.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            current_date: Current date
            market_volatility: Current market volatility
            portfolio_performance: Recent portfolio performance
            
        Returns:
            Tuple of (should_rebalance, trigger_type, reason)
        """
        if current_date is None:
            current_date = datetime.now()
        
        # Check scheduled rebalancing
        if self._is_scheduled_rebalance_due(current_date):
            return True, RebalanceTrigger.SCHEDULED, f"Scheduled {self.config.frequency.value} rebalancing"
        
        # Check threshold-based rebalancing
        drift_analysis = self.analyze_drift(current_weights, target_weights, 100000)  # Use dummy portfolio value
        if drift_analysis['rebalance_needed']:
            max_drift = max([stock['drift_percent'] for stock in drift_analysis['stock_drifts'].values()])
            return True, RebalanceTrigger.THRESHOLD, f"Drift threshold exceeded: {max_drift:.1f}%"
        
        # Check volatility-based rebalancing
        if market_volatility and market_volatility > self.config.volatility_threshold:
            return True, RebalanceTrigger.VOLATILITY, f"High market volatility: {market_volatility:.2%}"
        
        # Check performance-based rebalancing
        if portfolio_performance and abs(portfolio_performance) > self.config.performance_threshold:
            direction = "positive" if portfolio_performance > 0 else "negative"
            return True, RebalanceTrigger.PERFORMANCE, f"Significant {direction} performance: {portfolio_performance:.2%}"
        
        return False, None, "No rebalancing needed"
    
    def _is_scheduled_rebalance_due(self, current_date: datetime) -> bool:
        """Check if scheduled rebalancing is due."""
        if not self.last_rebalance_date:
            return True
        
        days_since_last = (current_date - self.last_rebalance_date).days
        
        frequency_days = {
            RebalanceFrequency.DAILY: 1,
            RebalanceFrequency.WEEKLY: 7,
            RebalanceFrequency.MONTHLY: 30,
            RebalanceFrequency.QUARTERLY: 90,
            RebalanceFrequency.SEMI_ANNUAL: 180,
            RebalanceFrequency.ANNUAL: 365
        }
        
        required_days = frequency_days.get(self.config.frequency, 30)
        return days_since_last >= required_days
    
    def execute_rebalance(self, current_weights: Dict[str, float],
                         target_weights: Dict[str, float],
                         portfolio_value: float,
                         portfolio_name: str,
                         trigger: RebalanceTrigger,
                         reason: str,
                         current_date: datetime = None) -> RebalanceEvent:
        """
        Execute portfolio rebalancing.
        
        Args:
            current_weights: Current portfolio weights
            target_weights: Target portfolio weights
            portfolio_value: Total portfolio value
            portfolio_name: Name of the portfolio
            trigger: Rebalancing trigger type
            reason: Reason for rebalancing
            current_date: Date of rebalancing
            
        Returns:
            RebalanceEvent record
        """
        if current_date is None:
            current_date = datetime.now()
        
        # Generate trades
        trades, cost = self._generate_rebalance_trades(current_weights, target_weights, portfolio_value)
        
        # Create rebalance event
        event = RebalanceEvent(
            date=current_date,
            trigger=trigger,
            portfolio_name=portfolio_name,
            trades=trades,
            cost=cost,
            reason=reason,
            before_weights=current_weights.copy(),
            after_weights=target_weights.copy()
        )
        
        # Record the event
        self.rebalance_history.append(event)
        self.last_rebalance_date = current_date
        
        return event
    
    def backtest_rebalancing(self, price_data: pd.DataFrame,
                           target_weights: Dict[str, float],
                           initial_value: float = 100000,
                           start_date: datetime = None,
                           end_date: datetime = None) -> Dict:
        """
        Backtest rebalancing strategy.
        
        Args:
            price_data: Historical price data
            target_weights: Target portfolio weights
            initial_value: Initial portfolio value
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Backtest results dictionary
        """
        if start_date is None:
            start_date = price_data.index[0]
        if end_date is None:
            end_date = price_data.index[-1]
        
        # Filter data to backtest period
        backtest_data = price_data.loc[start_date:end_date]
        
        # Initialize backtest
        portfolio_values = []
        rebalance_dates = []
        total_costs = 0.0
        current_shares = {}
        
        # Calculate initial shares
        for symbol, weight in target_weights.items():
            if symbol in backtest_data.columns:
                initial_price = backtest_data[symbol].iloc[0]
                shares = (initial_value * weight) / initial_price
                current_shares[symbol] = shares
        
        # Simulate portfolio over time
        for date, prices in backtest_data.iterrows():
            # Calculate current portfolio value and weights
            current_value = 0.0
            current_weights = {}
            
            for symbol, shares in current_shares.items():
                if symbol in prices and not pd.isna(prices[symbol]):
                    value = shares * prices[symbol]
                    current_value += value
                    current_weights[symbol] = value / max(current_value, 1e-10)
            
            portfolio_values.append(current_value)
            
            # Check if rebalancing is needed
            should_rebal, trigger, reason = self.should_rebalance(
                current_weights, target_weights, date
            )
            
            if should_rebal and len(rebalance_dates) < 100:  # Limit rebalances
                # Execute rebalance
                event = self.execute_rebalance(
                    current_weights, target_weights, current_value,
                    "Backtest Portfolio", trigger, reason, date
                )
                
                rebalance_dates.append(date)
                total_costs += event.cost
                
                # Update shares based on rebalancing
                for symbol, weight in target_weights.items():
                    if symbol in prices and not pd.isna(prices[symbol]):
                        target_value = current_value * weight
                        current_shares[symbol] = target_value / prices[symbol]
        
        # Calculate performance metrics
        portfolio_series = pd.Series(portfolio_values, index=backtest_data.index)
        
        # Buy and hold comparison (no rebalancing)
        buy_hold_values = []
        initial_shares_bh = {}
        for symbol, weight in target_weights.items():
            if symbol in backtest_data.columns:
                initial_price = backtest_data[symbol].iloc[0]
                shares = (initial_value * weight) / initial_price
                initial_shares_bh[symbol] = shares
        
        for date, prices in backtest_data.iterrows():
            bh_value = 0.0
            for symbol, shares in initial_shares_bh.items():
                if symbol in prices and not pd.isna(prices[symbol]):
                    bh_value += shares * prices[symbol]
            buy_hold_values.append(bh_value)
        
        buy_hold_series = pd.Series(buy_hold_values, index=backtest_data.index)
        
        # Calculate metrics
        results = {
            'start_date': start_date,
            'end_date': end_date,
            'initial_value': initial_value,
            'final_value': portfolio_values[-1],
            'total_return': (portfolio_values[-1] / initial_value) - 1,
            'annualized_return': ((portfolio_values[-1] / initial_value) ** (365 / len(backtest_data))) - 1,
            'volatility': portfolio_series.pct_change().std() * np.sqrt(252),
            'sharpe_ratio': (portfolio_series.pct_change().mean() * 252) / (portfolio_series.pct_change().std() * np.sqrt(252)),
            'max_drawdown': (portfolio_series / portfolio_series.expanding().max() - 1).min(),
            'num_rebalances': len(rebalance_dates),
            'total_costs': total_costs,
            'cost_drag': total_costs / initial_value,
            'rebalance_dates': rebalance_dates,
            'portfolio_values': portfolio_values,
            'buy_hold_return': (buy_hold_values[-1] / initial_value) - 1,
            'excess_return': ((portfolio_values[-1] / initial_value) - 1) - ((buy_hold_values[-1] / initial_value) - 1),
            'portfolio_series': portfolio_series,
            'buy_hold_series': buy_hold_series
        }
        
        return results
    
    def get_rebalance_calendar(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get scheduled rebalancing dates for a period."""
        dates = []
        current_date = start_date
        
        frequency_delta = {
            RebalanceFrequency.DAILY: timedelta(days=1),
            RebalanceFrequency.WEEKLY: timedelta(days=7),
            RebalanceFrequency.MONTHLY: timedelta(days=30),
            RebalanceFrequency.QUARTERLY: timedelta(days=90),
            RebalanceFrequency.SEMI_ANNUAL: timedelta(days=180),
            RebalanceFrequency.ANNUAL: timedelta(days=365)
        }
        
        delta = frequency_delta.get(self.config.frequency, timedelta(days=30))
        
        while current_date <= end_date:
            dates.append(current_date)
            current_date += delta
        
        return dates
    
    def export_rebalance_history(self, filename: str = None) -> str:
        """Export rebalancing history to JSON file."""
        if filename is None:
            filename = f"rebalance_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert events to serializable format
        history_data = []
        for event in self.rebalance_history:
            event_data = {
                'date': event.date.isoformat(),
                'trigger': event.trigger.value,
                'portfolio_name': event.portfolio_name,
                'trades': event.trades,
                'cost': event.cost,
                'reason': event.reason,
                'before_weights': event.before_weights,
                'after_weights': event.after_weights
            }
            history_data.append(event_data)
        
        export_data = {
            'config': {
                'frequency': self.config.frequency.value,
                'threshold_percent': self.config.threshold_percent,
                'auto_rebalance': self.config.auto_rebalance,
                'trading_cost_percent': self.config.trading_cost_percent,
                'min_trade_amount': self.config.min_trade_amount,
                'max_trades_per_period': self.config.max_trades_per_period,
                'volatility_threshold': self.config.volatility_threshold,
                'performance_threshold': self.config.performance_threshold
            },
            'history': history_data,
            'last_rebalance_date': self.last_rebalance_date.isoformat() if self.last_rebalance_date else None
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename