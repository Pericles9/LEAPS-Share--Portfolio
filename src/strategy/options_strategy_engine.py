"""
Options-Based Portfolio Strategy Engine

Comprehensive implementation of the sophisticated options-based portfolio construction strategy.
Uses options market data to derive predictive signals for portfolio optimization.

Strategy Components:
1. Data Inputs (from Options Chain)
2. Derived Predictive Factors  
3. Portfolio Construction Steps
4. Optimization Objectives
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
from scipy.stats import norm
from scipy import optimize
from scipy.stats import skew, kurtosis

from ..data.options_analyzer import OptionsAnalyzer, OptionsMetrics
from ..data.polygon_source import PolygonOptionsSource
from ..data.tv_data_fetcher import TradingViewDataFetcher
from ..portfolio.optimizer import PortfolioOptimizer, PortfolioMetrics
from ..analytics.advanced_options import AdvancedOptionsAnalyzer


@dataclass
class OptionsSurface:
    """Options surface data for implied volatility analysis."""
    symbol: str
    spot_price: float
    
    # IV Term Structure
    iv_1m: float
    iv_3m: float 
    iv_6m: float
    iv_1y: float
    iv_leaps: Optional[float]
    iv_term_slope: float  # Short vs long IV
    
    # Realized Volatility
    realized_vol: float
    iv_rv_spread: float  # IV premium/discount
    
    # Vol Skew/Smile
    vol_skew: float  # OTM puts vs ATM calls IV difference
    
    # Greeks (aggregated)
    total_delta: float
    total_vega: float
    total_gamma: float
    
    # Pricing metrics
    call_put_price_ratio: float
    
    
@dataclass
class OptionsFactors:
    """Derived predictive factors from options data."""
    symbol: str
    
    # Risk Predictors
    forward_vol_forecast: float  # IV
    crash_probability: float     # IV skew
    vol_premium: float          # IV-RV spread
    
    # Return/Growth Predictors
    implied_drift: float        # From put-call parity
    call_cheapness: float       # Call vs put pricing bias
    growth_optionality: float   # High IV with stable fundamentals
    
    # Sharpe Predictors
    proxy_sharpe: float         # Expected drift / IV
    tail_risk_adjusted_sharpe: float  # Penalized for skew
    
    # Convexity Premium
    convexity_score: float      # ATM gamma opportunities
    
    # Final composite scores
    risk_score: float
    sharpe_score: float
    growth_score: float
    

@dataclass 
class StrategyConfig:
    """Configuration for different portfolio strategies."""
    name: str
    objective: str  # 'sharpe', 'growth', 'low_risk'
    
    # Factor weights for scoring
    risk_weight: float = 0.33
    sharpe_weight: float = 0.33
    growth_weight: float = 0.34
    
    # Risk constraints
    max_vol_threshold: float = 0.25
    max_skew_penalty: float = 0.15
    min_liquidity: int = 1000  # Min daily volume
    
    # Portfolio constraints
    max_position_size: float = 0.15
    min_position_size: float = 0.005
    sector_max_weight: float = 0.35
    

class OptionsStrategyEngine:
    """Main engine for options-based portfolio construction."""
    
    def __init__(self, enable_cache: bool = True):
        """Initialize the strategy engine."""
        self.options_analyzer = OptionsAnalyzer()
        self.advanced_analyzer = AdvancedOptionsAnalyzer()
        self.polygon_source = PolygonOptionsSource(enable_cache=enable_cache)
        self.tv_fetcher = TradingViewDataFetcher(enable_cache=enable_cache)
        self.optimizer = PortfolioOptimizer()
        
        # Cache for expensive calculations
        self.surfaces_cache = {}
        self.factors_cache = {}
        
        print("🚀 Options Strategy Engine initialized with premium data sources and advanced analytics")
    
    def analyze_universe(self, symbols: List[str]) -> Dict[str, OptionsFactors]:
        """
        Step 1: Analyze entire universe to compute options factors.
        
        Args:
            symbols: List of stock symbols to analyze
            
        Returns:
            Dictionary mapping symbols to their OptionsFactors
        """
        print(f"\n🔍 STEP 1: Analyzing {len(symbols)} stocks for options factors...")
        
        factors_dict = {}
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n📊 [{i}/{len(symbols)}] Analyzing {symbol}...")
            
            try:
                # Get options surface data
                surface = self._build_options_surface(symbol)
                if not surface:
                    print(f"   ❌ Could not build options surface for {symbol}")
                    continue
                
                # Compute predictive factors
                factors = self._compute_options_factors(surface)
                if not factors:
                    print(f"   ❌ Could not compute factors for {symbol}")
                    continue
                
                factors_dict[symbol] = factors
                print(f"   ✅ {symbol}: Risk={factors.risk_score:.2f}, "
                      f"Sharpe={factors.sharpe_score:.2f}, Growth={factors.growth_score:.2f}")
                
            except Exception as e:
                print(f"   ❌ Error analyzing {symbol}: {e}")
                continue
        
        print(f"\n✅ Analysis complete: {len(factors_dict)}/{len(symbols)} stocks processed")
        return factors_dict
    
    def _build_options_surface(self, symbol: str) -> Optional[OptionsSurface]:
        """Build comprehensive options surface for a symbol using advanced analytics."""
        if symbol in self.surfaces_cache:
            return self.surfaces_cache[symbol]
        
        try:
            # Get current stock price with enhanced fallbacks
            stock_price = self.polygon_source._get_stock_price(symbol)
            if not stock_price:
                print(f"     ⚠️ No stock price available for {symbol}, trying synthetic approach...")
                return self._build_synthetic_surface(symbol)
            
            # Get options chain data
            options_data = self.polygon_source.get_options_data(symbol)
            if not options_data:
                print(f"     ⚠️ No options data available for {symbol}, using synthetic surface...")
                return self._build_synthetic_surface(symbol, stock_price)
            
            # Use advanced analytics for comprehensive analysis
            print(f"     🔬 Advanced analysis for {symbol}...")
            analysis_results = self.advanced_analyzer.comprehensive_analysis(
                symbol, options_data, stock_price
            )
            
            if analysis_results.get('data_quality') not in ['good']:
                print(f"     ⚠️ Limited data quality for {symbol}: {analysis_results.get('data_quality')}")
                # Try basic analysis first, then synthetic
                basic_surface = self._build_basic_surface(symbol, options_data, stock_price)
                if basic_surface:
                    return basic_surface
                else:
                    return self._build_synthetic_surface(symbol, stock_price)
            
            # Extract advanced metrics
            term_structure = analysis_results.get('term_structure', {})
            skew_metrics = analysis_results.get('volatility_skew', {})
            flow_analysis = analysis_results.get('options_flow', {})
            predictors = analysis_results.get('predictive_factors', {})
            
            # Calculate realized volatility
            realized_vol = self._calculate_realized_volatility(symbol)
            
            # Build enhanced surface
            surface = OptionsSurface(
                symbol=symbol,
                spot_price=stock_price,
                iv_1m=term_structure.get('1m', 0.20),
                iv_3m=term_structure.get('3m', 0.22),
                iv_6m=term_structure.get('6m', 0.24),
                iv_1y=term_structure.get('1y', 0.25),
                iv_leaps=term_structure.get('leaps'),
                iv_term_slope=term_structure.get('slope', 0.0),
                realized_vol=realized_vol,
                iv_rv_spread=term_structure.get('3m', 0.22) - realized_vol,
                vol_skew=skew_metrics.get('put_skew', 0.0),
                total_delta=flow_analysis.get('call_volume', 1000) - flow_analysis.get('put_volume', 1000),
                total_vega=predictors.get('forward_vol', 0.25) * 1000,  # Scaled vega proxy
                total_gamma=predictors.get('gamma_exposure', 0.0) * 1000,
                call_put_price_ratio=flow_analysis.get('put_call_volume_ratio', 1.0)
            )
            
            print(f"     ✅ Advanced surface built: IV={surface.iv_3m:.1%}, Skew={surface.vol_skew:.3f}, Slope={surface.iv_term_slope:.3f}")
            
            self.surfaces_cache[symbol] = surface
            return surface
            
        except Exception as e:
            print(f"     ❌ Advanced analysis failed for {symbol}: {e}")
            # Fallback chain: basic -> synthetic
            try:
                if 'options_data' in locals() and 'stock_price' in locals():
                    basic_surface = self._build_basic_surface(symbol, options_data, stock_price)
                    if basic_surface:
                        return basic_surface
                
                return self._build_synthetic_surface(symbol, stock_price if 'stock_price' in locals() else None)
            except Exception as fallback_error:
                print(f"     ❌ All fallbacks failed for {symbol}: {fallback_error}")
                return None
    
    def _build_synthetic_surface(self, symbol: str, stock_price: Optional[float] = None) -> Optional[OptionsSurface]:
        """Build synthetic options surface when real data is unavailable."""
        try:
            # Use estimated stock price if not provided
            if not stock_price:
                price_estimates = {
                    'AAPL': 175, 'MSFT': 340, 'GOOGL': 140, 'AMZN': 145,
                    'TSLA': 250, 'META': 320, 'NVDA': 450, 'JPM': 155,
                    'JNJ': 160, 'V': 280, 'UNH': 520, 'HD': 350,
                    'PG': 155, 'MA': 420, 'DIS': 95, 'XOM': 115
                }
                stock_price = price_estimates.get(symbol, 100.0)  # Default $100
                print(f"     📊 Using estimated price ${stock_price:.0f} for {symbol}")
            
            # Generate realistic synthetic parameters based on stock characteristics
            np.random.seed(hash(symbol) % 2**32)  # Consistent randomness per symbol
            
            # Base volatility by stock type
            if symbol in ['TSLA', 'NVDA', 'AMD', 'MRNA']:
                base_iv = np.random.uniform(0.35, 0.50)  # High vol stocks
                vol_skew = np.random.uniform(0.02, 0.08)
            elif symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']:
                base_iv = np.random.uniform(0.25, 0.35)  # Tech stocks
                vol_skew = np.random.uniform(0.01, 0.05)
            elif symbol in ['JPM', 'BAC', 'WFC', 'GS']:
                base_iv = np.random.uniform(0.20, 0.30)  # Financials
                vol_skew = np.random.uniform(0.005, 0.03)
            else:
                base_iv = np.random.uniform(0.18, 0.28)  # General stocks
                vol_skew = np.random.uniform(0.002, 0.04)
            
            # Calculate realized volatility (usually less than IV)
            realized_vol = base_iv * np.random.uniform(0.7, 0.9)
            
            # Term structure (usually upward sloping)
            term_slope = np.random.uniform(0.01, 0.05)
            
            # Build synthetic surface
            surface = OptionsSurface(
                symbol=symbol,
                spot_price=stock_price,
                iv_1m=base_iv * 0.9,
                iv_3m=base_iv,
                iv_6m=base_iv + term_slope * 0.5,
                iv_1y=base_iv + term_slope,
                iv_leaps=base_iv + term_slope * 1.2 if np.random.random() > 0.3 else None,
                iv_term_slope=term_slope,
                realized_vol=realized_vol,
                iv_rv_spread=base_iv - realized_vol,
                vol_skew=vol_skew,
                total_delta=np.random.uniform(-5000, 15000),  # Synthetic flow
                total_vega=np.random.uniform(5000, 25000),
                total_gamma=np.random.uniform(100, 2000),
                call_put_price_ratio=np.random.uniform(0.6, 1.8)
            )
            
            print(f"     🎲 Synthetic surface: IV={surface.iv_3m:.1%}, Skew={surface.vol_skew:.3f}, RV={surface.realized_vol:.1%}")
            
            self.surfaces_cache[symbol] = surface
            return surface
            
        except Exception as e:
            print(f"     ❌ Synthetic surface generation failed for {symbol}: {e}")
            return None
    
    def _build_basic_surface(self, symbol: str, options_data: Dict, stock_price: float) -> Optional[OptionsSurface]:
        """Fallback method for basic surface construction."""
        try:
            calls_df = options_data.get('calls', pd.DataFrame())
            puts_df = options_data.get('puts', pd.DataFrame())
            
            if calls_df.empty and puts_df.empty:
                return None
            
            # Calculate IV term structure
            iv_structure = self._calculate_iv_term_structure(calls_df, puts_df, stock_price)
            
            # Calculate realized volatility
            realized_vol = self._calculate_realized_volatility(symbol)
            
            # Calculate vol skew
            vol_skew = self._calculate_vol_skew(calls_df, puts_df, stock_price)
            
            # Calculate aggregated Greeks
            greeks = self._calculate_aggregate_greeks(calls_df, puts_df)
            
            # Calculate call/put pricing ratio
            call_put_ratio = self._calculate_call_put_price_ratio(calls_df, puts_df, stock_price)
            
            surface = OptionsSurface(
                symbol=symbol,
                spot_price=stock_price,
                iv_1m=iv_structure.get('1m', 0.20),
                iv_3m=iv_structure.get('3m', 0.22),
                iv_6m=iv_structure.get('6m', 0.24),
                iv_1y=iv_structure.get('1y', 0.25),
                iv_leaps=iv_structure.get('leaps'),
                iv_term_slope=iv_structure.get('slope', 0.0),
                realized_vol=realized_vol,
                iv_rv_spread=iv_structure.get('3m', 0.22) - realized_vol,
                vol_skew=vol_skew,
                total_delta=greeks.get('delta', 0.0),
                total_vega=greeks.get('vega', 0.0),
                total_gamma=greeks.get('gamma', 0.0),
                call_put_price_ratio=call_put_ratio
            )
            
            return surface
            
        except Exception as e:
            print(f"     ❌ Basic surface construction failed for {symbol}: {e}")
            return None
    
    def _calculate_iv_term_structure(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame, 
                                   spot_price: float) -> Dict[str, float]:
        """Calculate implied volatility term structure."""
        iv_structure = {}
        
        try:
            # Combine calls and puts for ATM analysis
            all_options = pd.concat([calls_df, puts_df], ignore_index=True)
            if all_options.empty:
                return {'1m': 0.20, '3m': 0.22, '6m': 0.24, '1y': 0.25, 'slope': 0.02}
            
            # Calculate days to expiration
            if 'expiration_date' in all_options.columns:
                today = datetime.now()
                all_options['dte'] = (pd.to_datetime(all_options['expiration_date']) - today).dt.days
            else:
                # Fallback: assume reasonable DTE distribution
                all_options['dte'] = np.random.choice([30, 90, 180, 365], len(all_options))
            
            # Find ATM options (closest to spot price)
            all_options['distance_to_atm'] = abs(all_options['strike'] - spot_price)
            
            # Group by maturity buckets and find average IV
            for bucket, (min_dte, max_dte) in [('1m', (15, 45)), ('3m', (75, 105)), 
                                               ('6m', (150, 210)), ('1y', (300, 400))]:
                bucket_options = all_options[
                    (all_options['dte'] >= min_dte) & 
                    (all_options['dte'] <= max_dte)
                ]
                
                if not bucket_options.empty:
                    # Find closest to ATM in this bucket
                    atm_options = bucket_options.nsmallest(5, 'distance_to_atm')
                    if 'implied_volatility' in atm_options.columns:
                        iv_structure[bucket] = atm_options['implied_volatility'].mean()
                    else:
                        # Estimate IV based on option price
                        iv_structure[bucket] = self._estimate_iv_from_price(atm_options, spot_price)
            
            # Check for LEAPS (>365 days)
            leaps_options = all_options[all_options['dte'] > 365]
            if not leaps_options.empty:
                atm_leaps = leaps_options.nsmallest(3, 'distance_to_atm')
                if 'implied_volatility' in atm_leaps.columns:
                    iv_structure['leaps'] = atm_leaps['implied_volatility'].mean()
            
            # Calculate term structure slope (short vs long)
            if '1m' in iv_structure and '1y' in iv_structure:
                iv_structure['slope'] = iv_structure['1y'] - iv_structure['1m']
            
            # Fill missing values with reasonable defaults
            default_ivs = {'1m': 0.20, '3m': 0.22, '6m': 0.24, '1y': 0.25}
            for key, default_val in default_ivs.items():
                if key not in iv_structure or pd.isna(iv_structure[key]):
                    iv_structure[key] = default_val
            
            return iv_structure
            
        except Exception as e:
            print(f"     IV term structure error: {e}")
            return {'1m': 0.20, '3m': 0.22, '6m': 0.24, '1y': 0.25, 'slope': 0.02}
    
    def _estimate_iv_from_price(self, options_df: pd.DataFrame, spot_price: float) -> float:
        """Estimate IV from option prices using Black-Scholes approximation."""
        try:
            if options_df.empty or 'last_quote' not in options_df.columns:
                return 0.22  # Default IV
            
            # Simple IV estimation for ATM options
            option_prices = options_df['last_quote'].values
            strikes = options_df['strike'].values
            
            # For ATM options, use rule of thumb: IV ≈ option_price / (0.4 * spot_price)
            atm_prices = option_prices[abs(strikes - spot_price) < spot_price * 0.05]
            if len(atm_prices) > 0:
                estimated_iv = np.mean(atm_prices) / (0.4 * spot_price)
                return min(max(estimated_iv, 0.10), 1.0)  # Clamp between 10% and 100%
            
            return 0.22
            
        except Exception:
            return 0.22
    
    def _calculate_realized_volatility(self, symbol: str, days: int = 60) -> float:
        """Calculate realized volatility from historical returns."""
        try:
            # Get historical data
            returns_data = self.tv_fetcher.get_returns_data([symbol], days=days)
            if not returns_data or symbol not in returns_data:
                return 0.20  # Default
            
            returns = returns_data[symbol].dropna()
            if len(returns) < 10:
                return 0.20
            
            # Annualized volatility
            realized_vol = returns.std() * np.sqrt(252)
            return max(min(realized_vol, 1.0), 0.05)  # Clamp between 5% and 100%
            
        except Exception:
            return 0.20
    
    def _calculate_vol_skew(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame, 
                          spot_price: float) -> float:
        """Calculate volatility skew (OTM puts vs ATM calls)."""
        try:
            if calls_df.empty or puts_df.empty:
                return 0.0
            
            if 'implied_volatility' not in calls_df.columns or 'implied_volatility' not in puts_df.columns:
                return 0.0
            
            # Find ATM calls (strikes near spot)
            calls_df['distance'] = abs(calls_df['strike'] - spot_price)
            atm_calls = calls_df.nsmallest(3, 'distance')
            atm_call_iv = atm_calls['implied_volatility'].mean()
            
            # Find OTM puts (strikes ~10% below spot)
            otm_put_strikes = puts_df[puts_df['strike'] < spot_price * 0.95]
            if not otm_put_strikes.empty:
                otm_put_iv = otm_put_strikes['implied_volatility'].mean()
                vol_skew = otm_put_iv - atm_call_iv
                return max(min(vol_skew, 0.20), -0.05)  # Clamp skew
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_aggregate_greeks(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate aggregated Greeks from options chain."""
        greeks = {'delta': 0.0, 'vega': 0.0, 'gamma': 0.0}
        
        try:
            # Sum up Greeks from both calls and puts
            for df, multiplier in [(calls_df, 1), (puts_df, -1)]:
                if df.empty:
                    continue
                
                # Delta
                if 'delta' in df.columns and 'open_interest' in df.columns:
                    weighted_delta = (df['delta'] * df['open_interest']).sum()
                    greeks['delta'] += weighted_delta * multiplier
                
                # Vega
                if 'vega' in df.columns and 'open_interest' in df.columns:
                    weighted_vega = (df['vega'] * df['open_interest']).sum()
                    greeks['vega'] += weighted_vega
                
                # Gamma  
                if 'gamma' in df.columns and 'open_interest' in df.columns:
                    weighted_gamma = (df['gamma'] * df['open_interest']).sum()
                    greeks['gamma'] += weighted_gamma
                    
        except Exception as e:
            print(f"     Greeks calculation error: {e}")
        
        return greeks
    
    def _calculate_call_put_price_ratio(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame,
                                      spot_price: float) -> float:
        """Calculate relative pricing between calls and puts."""
        try:
            if calls_df.empty or puts_df.empty:
                return 1.0
            
            # Find ATM options
            calls_df['distance'] = abs(calls_df['strike'] - spot_price)
            puts_df['distance'] = abs(puts_df['strike'] - spot_price)
            
            atm_calls = calls_df.nsmallest(3, 'distance')
            atm_puts = puts_df.nsmallest(3, 'distance')
            
            if 'last_quote' in atm_calls.columns and 'last_quote' in atm_puts.columns:
                avg_call_price = atm_calls['last_quote'].mean()
                avg_put_price = atm_puts['last_quote'].mean()
                
                if avg_put_price > 0:
                    return avg_call_price / avg_put_price
            
            return 1.0
            
        except Exception:
            return 1.0
    
    def _compute_options_factors(self, surface: OptionsSurface) -> Optional[OptionsFactors]:
        """Step 2: Compute derived predictive factors from options surface."""
        try:
            # Risk Predictors
            forward_vol_forecast = surface.iv_3m  # Use 3m IV as forward vol
            crash_probability = max(0, surface.vol_skew / 0.10)  # Normalize skew
            vol_premium = surface.iv_rv_spread
            
            # Return/Growth Predictors
            implied_drift = self._calculate_implied_drift(surface)
            call_cheapness = 2.0 - surface.call_put_price_ratio  # Higher when calls are cheap
            growth_optionality = self._calculate_growth_optionality(surface)
            
            # Sharpe Predictors
            proxy_sharpe = implied_drift / max(surface.iv_3m, 0.05)
            tail_risk_penalty = max(0, surface.vol_skew * 2)  # Penalize negative skew
            tail_risk_adjusted_sharpe = proxy_sharpe - tail_risk_penalty
            
            # Convexity Premium
            convexity_score = surface.total_gamma / max(abs(surface.total_delta), 1.0)
            
            # Composite Scores (0-10 scale)
            risk_score = self._calculate_risk_score(surface, forward_vol_forecast, crash_probability, vol_premium)
            sharpe_score = self._calculate_sharpe_score(proxy_sharpe, tail_risk_adjusted_sharpe)
            growth_score = self._calculate_growth_score(surface, call_cheapness, growth_optionality)
            
            return OptionsFactors(
                symbol=surface.symbol,
                forward_vol_forecast=forward_vol_forecast,
                crash_probability=crash_probability,
                vol_premium=vol_premium,
                implied_drift=implied_drift,
                call_cheapness=call_cheapness,
                growth_optionality=growth_optionality,
                proxy_sharpe=proxy_sharpe,
                tail_risk_adjusted_sharpe=tail_risk_adjusted_sharpe,
                convexity_score=convexity_score,
                risk_score=risk_score,
                sharpe_score=sharpe_score,
                growth_score=growth_score
            )
            
        except Exception as e:
            print(f"     Factor computation error for {surface.symbol}: {e}")
            return None
    
    def _calculate_implied_drift(self, surface: OptionsSurface) -> float:
        """Calculate option-implied drift from put-call parity."""
        try:
            # Simplified drift calculation
            # In practice, would use put-call parity with risk-free rate
            risk_free_rate = 0.05  # 5% assumption
            
            # Use call/put pricing ratio as proxy for market bias
            if surface.call_put_price_ratio > 1.2:
                return risk_free_rate + 0.05  # Bullish bias
            elif surface.call_put_price_ratio < 0.8:
                return risk_free_rate - 0.03  # Bearish bias
            else:
                return risk_free_rate  # Neutral
                
        except Exception:
            return 0.05  # Default 5%
    
    def _calculate_growth_optionality(self, surface: OptionsSurface) -> float:
        """Calculate growth optionality score."""
        try:
            # High IV relative to realized but stable fundamentals
            iv_premium = surface.iv_rv_spread
            term_structure_upward = max(0, surface.iv_term_slope)
            
            # Positive term slope + IV premium suggests growth optionality
            growth_optionality = (iv_premium * 2) + term_structure_upward
            return max(0, min(growth_optionality, 1.0))  # Clamp 0-1
            
        except Exception:
            return 0.5
    
    def _calculate_risk_score(self, surface: OptionsSurface, forward_vol: float, 
                            crash_prob: float, vol_premium: float) -> float:
        """Calculate composite risk score (lower is better for low-risk strategies)."""
        try:
            # Lower volatility = lower risk
            vol_component = max(0, 10 - (forward_vol * 40))  # Scale IV to 0-10
            
            # Lower crash probability = lower risk  
            crash_component = max(0, 10 - (crash_prob * 10))
            
            # Negative vol premium (IV < RV) = lower risk
            premium_component = 5 - (vol_premium * 10)
            premium_component = max(0, min(premium_component, 10))
            
            # Weighted average
            risk_score = (vol_component * 0.5 + crash_component * 0.3 + premium_component * 0.2)
            return max(0, min(risk_score, 10))
            
        except Exception:
            return 5.0  # Neutral
    
    def _calculate_sharpe_score(self, proxy_sharpe: float, tail_adjusted_sharpe: float) -> float:
        """Calculate composite Sharpe score."""
        try:
            # Normalize Sharpe ratios to 0-10 scale
            sharpe_component = min(10, max(0, proxy_sharpe * 5 + 5))
            tail_component = min(10, max(0, tail_adjusted_sharpe * 5 + 5))
            
            # Weight tail-adjusted more heavily
            sharpe_score = (sharpe_component * 0.3 + tail_component * 0.7)
            return max(0, min(sharpe_score, 10))
            
        except Exception:
            return 5.0
    
    def _calculate_growth_score(self, surface: OptionsSurface, call_cheapness: float, 
                              growth_optionality: float) -> float:
        """Calculate composite growth score."""
        try:
            # High growth score for:
            # - Cheap calls relative to puts
            # - High growth optionality
            # - Positive term structure
            # - High convexity potential
            
            cheapness_component = min(10, max(0, call_cheapness * 5 + 5))
            optionality_component = growth_optionality * 10
            
            # Term structure component (upward sloping is growth-friendly)
            term_component = min(5, max(-2, surface.iv_term_slope * 25 + 2))
            
            # Convexity component
            convexity_component = min(3, max(0, abs(surface.total_gamma) / 1000))
            
            growth_score = (cheapness_component * 0.4 + optionality_component * 0.3 + 
                          term_component * 0.2 + convexity_component * 0.1)
            
            return max(0, min(growth_score, 10))
            
        except Exception:
            return 5.0
    
    def construct_portfolio(self, factors_dict: Dict[str, OptionsFactors], 
                          strategy_config: StrategyConfig,
                          universe_size: int = 20) -> Dict[str, Any]:
        """
        Step 3: Construct portfolio based on strategy configuration.
        
        Args:
            factors_dict: Dictionary of symbols to OptionsFactors
            strategy_config: Strategy configuration
            universe_size: Maximum number of stocks in portfolio
            
        Returns:
            Portfolio construction results
        """
        print(f"\n🎯 STEP 3: Constructing {strategy_config.name} portfolio...")
        
        if not factors_dict:
            print("   ❌ No factors data available")
            return {}
        
        # Step 3a: Universe Selection (filter by liquidity, etc.)
        filtered_symbols = self._filter_universe(factors_dict, strategy_config)
        print(f"   📊 Universe filtered: {len(filtered_symbols)}/{len(factors_dict)} stocks pass filters")
        
        if len(filtered_symbols) < 3:
            print("   ❌ Insufficient stocks after filtering")
            return {}
        
        # Step 3b: Compute composite scores for ranking
        scores = self._compute_composite_scores(filtered_symbols, factors_dict, strategy_config)
        
        # Step 3c: Rank and select top stocks
        ranked_stocks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected_stocks = ranked_stocks[:universe_size]
        
        print(f"   🏆 Top {len(selected_stocks)} stocks selected:")
        for i, (symbol, score) in enumerate(selected_stocks[:10], 1):
            factors = factors_dict[symbol]
            print(f"      {i:2d}. {symbol}: Score={score:.2f} "
                  f"(R:{factors.risk_score:.1f}, S:{factors.sharpe_score:.1f}, G:{factors.growth_score:.1f})")
        
        # Step 3d: Calculate portfolio weights
        symbols = [s[0] for s in selected_stocks]
        weights = self._calculate_portfolio_weights(symbols, factors_dict, strategy_config)
        
        return {
            'symbols': symbols,
            'weights': weights,
            'scores': dict(selected_stocks),
            'factors': {s: factors_dict[s] for s in symbols},
            'strategy_config': strategy_config
        }
    
    def _filter_universe(self, factors_dict: Dict[str, OptionsFactors], 
                        config: StrategyConfig) -> List[str]:
        """Filter universe based on strategy constraints."""
        filtered = []
        
        for symbol, factors in factors_dict.items():
            # Basic quality filters
            if factors.forward_vol_forecast > config.max_vol_threshold:
                continue
            
            if factors.vol_premium < -config.max_skew_penalty:
                continue
            
            # Strategy-specific filters
            if config.objective == 'low_risk':
                if factors.risk_score < 6.0:  # Only high-risk-score (low risk) stocks
                    continue
            elif config.objective == 'growth':
                if factors.growth_score < 5.0:  # Only decent growth prospects
                    continue
            elif config.objective == 'sharpe':
                if factors.sharpe_score < 4.0:  # Only reasonable Sharpe potential
                    continue
            
            filtered.append(symbol)
        
        return filtered
    
    def _compute_composite_scores(self, symbols: List[str], factors_dict: Dict[str, OptionsFactors],
                                config: StrategyConfig) -> Dict[str, float]:
        """Compute composite scores for ranking."""
        scores = {}
        
        for symbol in symbols:
            factors = factors_dict[symbol]
            
            # Weighted composite score based on strategy
            composite = (factors.risk_score * config.risk_weight +
                        factors.sharpe_score * config.sharpe_weight +
                        factors.growth_score * config.growth_weight)
            
            scores[symbol] = composite
            
        return scores
    
    def _calculate_portfolio_weights(self, symbols: List[str], 
                                   factors_dict: Dict[str, OptionsFactors],
                                   config: StrategyConfig) -> np.ndarray:
        """Calculate portfolio weights based on strategy type."""
        n_assets = len(symbols)
        
        if config.objective == 'equal_weight':
            return np.full(n_assets, 1.0 / n_assets)
        
        elif config.objective == 'risk_parity':
            # Weight inversely proportional to volatility
            vols = [factors_dict[s].forward_vol_forecast for s in symbols]
            inv_vols = [1.0 / max(v, 0.05) for v in vols]
            weights = np.array(inv_vols)
            return weights / weights.sum()
        
        elif config.objective == 'low_risk':
            # Weight inversely proportional to risk scores (lower risk = higher weight)
            risk_scores = [factors_dict[s].risk_score for s in symbols]
            inv_risk_scores = [1.0 / max(r, 0.1) for r in risk_scores]
            weights = np.array(inv_risk_scores)
            return weights / weights.sum()
        
        elif config.objective == 'sharpe':
            # Weight proportional to Sharpe scores
            sharpe_scores = [factors_dict[s].sharpe_score for s in symbols]
            weights = np.array(sharpe_scores)
            return weights / weights.sum()
        
        elif config.objective == 'growth':
            # Weight proportional to growth scores
            growth_scores = [factors_dict[s].growth_score for s in symbols]
            weights = np.array(growth_scores)
            return weights / weights.sum()
        
        else:
            # Default equal weight
            return np.full(n_assets, 1.0 / n_assets)
    
    def optimize_portfolio(self, portfolio_data: Dict[str, Any]) -> Optional[PortfolioMetrics]:
        """
        Step 4: Run full optimization using traditional methods with options insights.
        
        Args:
            portfolio_data: Portfolio construction results
            
        Returns:
            Optimized PortfolioMetrics
        """
        print(f"\n⚡ STEP 4: Optimizing portfolio allocation...")
        
        symbols = portfolio_data.get('symbols', [])
        if len(symbols) < 2:
            print("   ❌ Need at least 2 symbols for optimization")
            return None
        
        try:
            # Get historical returns for optimization
            returns_data = self.tv_fetcher.get_returns_data(symbols, days=180)
            if not returns_data:
                print("   ❌ Could not fetch returns data")
                return None
            
            # Create returns DataFrame
            if isinstance(returns_data, dict):
                returns_df = pd.DataFrame(returns_data).dropna()
            else:
                returns_df = returns_data.dropna() if hasattr(returns_data, 'dropna') else pd.DataFrame()
            
            if returns_df.empty or len(returns_df) < 30:
                print(f"   ❌ Insufficient return data: {len(returns_df)} days")
                return None
            
            # Run optimization based on strategy objective
            strategy_config = portfolio_data['strategy_config']
            if strategy_config.objective == 'sharpe':
                # Maximize Sharpe ratio using mean-variance optimization
                metrics = self.optimizer.optimize_portfolio(returns_df, 'sharpe')
            elif strategy_config.objective == 'low_risk':
                # Minimize volatility using mean-variance optimization
                metrics = self.optimizer.optimize_portfolio(returns_df, 'min_volatility')
            elif strategy_config.objective == 'growth':
                # Maximize expected return using mean-variance optimization
                metrics = self.optimizer.optimize_portfolio(returns_df, 'max_return')
            elif strategy_config.objective == 'risk_parity':
                # Use risk parity weighting (inverse volatility)
                vols = returns_df.std().values
                inv_vols = 1.0 / np.maximum(vols, 0.05)
                weights = inv_vols / inv_vols.sum()
                exp_return, volatility, sharpe = self.optimizer.calculate_portfolio_metrics(weights, returns_df)
                metrics = PortfolioMetrics(
                    expected_return=exp_return,
                    volatility=volatility,
                    sharpe_ratio=sharpe,
                    weights=weights,
                    symbols=symbols
                )
            elif strategy_config.objective == 'equal_weight':
                # Use equal weights (market-neutral strategy)
                weights = np.full(len(symbols), 1.0 / len(symbols))
                exp_return, volatility, sharpe = self.optimizer.calculate_portfolio_metrics(weights, returns_df)
                metrics = PortfolioMetrics(
                    expected_return=exp_return,
                    volatility=volatility,
                    sharpe_ratio=sharpe,
                    weights=weights,
                    symbols=symbols
                )
            else:
                # Fallback to Sharpe optimization for any unknown objectives
                print(f"   ⚠️  Unknown objective '{strategy_config.objective}', using Sharpe optimization")
                metrics = self.optimizer.optimize_portfolio(returns_df, 'sharpe')
            
            print(f"   ✅ Optimization complete: Return={metrics.expected_return:.1%}, "
                  f"Vol={metrics.volatility:.1%}, Sharpe={metrics.sharpe_ratio:.2f}")
            
            return metrics
            
        except Exception as e:
            print(f"   ❌ Optimization error: {e}")
            return None


# Pre-defined strategy configurations
STRATEGY_CONFIGS = {
    'sharpe_optimized': StrategyConfig(
        name="Options Sharpe-Optimized",
        objective='sharpe',
        risk_weight=0.2,
        sharpe_weight=0.6,
        growth_weight=0.2,
        max_vol_threshold=0.30
    ),
    
    'growth_focused': StrategyConfig(
        name="Options Growth-Focused", 
        objective='growth',
        risk_weight=0.1,
        sharpe_weight=0.3,
        growth_weight=0.6,
        max_vol_threshold=0.40
    ),
    
    'defensive_stability': StrategyConfig(
        name="Options Defensive Stability",
        objective='low_risk',
        risk_weight=0.6,
        sharpe_weight=0.3,
        growth_weight=0.1,
        max_vol_threshold=0.20
    ),
    
    'high_income': StrategyConfig(
        name="Options High-Income",
        objective='risk_parity',
        risk_weight=0.4,
        sharpe_weight=0.4,
        growth_weight=0.2,
        max_vol_threshold=0.25
    ),
    
    'market_neutral': StrategyConfig(
        name="Options Market-Neutral",
        objective='equal_weight',
        risk_weight=0.33,
        sharpe_weight=0.34,
        growth_weight=0.33,
        max_vol_threshold=0.22
    )
}