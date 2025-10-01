"""
Enhanced Options Analytics Module

Advanced options calculations including Black-Scholes pricing, Greeks computation,
and volatility surface analysis for sophisticated portfolio construction.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize_scalar
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings


class BlackScholesCalculator:
    """Black-Scholes option pricing and Greeks calculations."""
    
    @staticmethod
    def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
        """Calculate d1 and d2 for Black-Scholes formula."""
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma*np.sqrt(T)
        return d1, d2
    
    @classmethod
    def call_price(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate Black-Scholes call option price."""
        if T <= 0:
            return max(0, S - K)
        
        d1, d2 = cls.calculate_d1_d2(S, K, T, r, sigma)
        
        price = S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
        return max(0, price)
    
    @classmethod
    def put_price(cls, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate Black-Scholes put option price."""
        if T <= 0:
            return max(0, K - S)
        
        d1, d2 = cls.calculate_d1_d2(S, K, T, r, sigma)
        
        price = K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return max(0, price)
    
    @classmethod
    def calculate_greeks(cls, S: float, K: float, T: float, r: float, sigma: float, 
                        option_type: str = 'call') -> Dict[str, float]:
        """Calculate all Greeks for an option."""
        if T <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0}
        
        d1, d2 = cls.calculate_d1_d2(S, K, T, r, sigma)
        
        # Common terms
        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)
        
        if option_type.lower() == 'call':
            delta = cdf_d1
            rho = K * T * np.exp(-r*T) * cdf_d2
            theta = (-S * pdf_d1 * sigma / (2*np.sqrt(T)) 
                    - r * K * np.exp(-r*T) * cdf_d2)
        else:  # put
            delta = cdf_d1 - 1
            rho = -K * T * np.exp(-r*T) * norm.cdf(-d2)
            theta = (-S * pdf_d1 * sigma / (2*np.sqrt(T)) 
                    + r * K * np.exp(-r*T) * norm.cdf(-d2))
        
        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        vega = S * pdf_d1 * np.sqrt(T)
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta / 365,  # Per day
            'vega': vega / 100,    # Per 1% vol change
            'rho': rho / 100       # Per 1% rate change
        }
    
    @classmethod
    def implied_volatility(cls, market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str = 'call') -> Optional[float]:
        """Calculate implied volatility using Brent's method."""
        if T <= 0 or market_price <= 0:
            return None
        
        def objective(sigma):
            if option_type.lower() == 'call':
                theoretical_price = cls.call_price(S, K, T, r, sigma)
            else:
                theoretical_price = cls.put_price(S, K, T, r, sigma)
            return abs(theoretical_price - market_price)
        
        try:
            result = minimize_scalar(objective, bounds=(0.01, 5.0), method='bounded')
            if result.success:
                return result.x
        except:
            pass
        
        return None


class VolatilitySurfaceAnalyzer:
    """Analyze implied volatility surfaces and term structures."""
    
    def __init__(self):
        self.bs_calc = BlackScholesCalculator()
    
    def build_iv_surface(self, options_df: pd.DataFrame, spot_price: float, 
                        risk_free_rate: float = 0.05) -> pd.DataFrame:
        """Build implied volatility surface from options data."""
        surface_data = []
        
        for _, option in options_df.iterrows():
            try:
                # Extract option details
                strike = option.get('strike', 0)
                expiry = option.get('expiration_date')
                market_price = option.get('last_quote', option.get('bid', 0))
                option_type = option.get('contract_type', 'call').lower()
                
                if not all([strike, expiry, market_price]) or market_price <= 0:
                    continue
                
                # Calculate time to expiration
                if isinstance(expiry, str):
                    expiry_date = pd.to_datetime(expiry)
                else:
                    expiry_date = expiry
                
                today = datetime.now()
                dte = (expiry_date - today).days
                T = max(dte / 365.0, 1/365)  # Minimum 1 day
                
                # Calculate moneyness
                moneyness = strike / spot_price
                
                # Calculate implied volatility
                iv = self.bs_calc.implied_volatility(
                    market_price, spot_price, strike, T, risk_free_rate, option_type
                )
                
                if iv and 0.05 <= iv <= 2.0:  # Reasonable IV range
                    surface_data.append({
                        'strike': strike,
                        'expiry': expiry_date,
                        'dte': dte,
                        'time_to_expiry': T,
                        'moneyness': moneyness,
                        'market_price': market_price,
                        'implied_vol': iv,
                        'option_type': option_type
                    })
                    
            except Exception as e:
                continue
        
        return pd.DataFrame(surface_data)
    
    def calculate_term_structure(self, surface_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate IV term structure from surface data."""
        if surface_df.empty:
            return {}
        
        # Group by expiry and calculate ATM IV
        term_structure = {}
        
        # Define maturity buckets
        buckets = {
            '1m': (15, 45),
            '3m': (75, 105), 
            '6m': (150, 210),
            '1y': (300, 400),
            'leaps': (400, 1000)
        }
        
        for bucket_name, (min_dte, max_dte) in buckets.items():
            bucket_data = surface_df[
                (surface_df['dte'] >= min_dte) & 
                (surface_df['dte'] <= max_dte) &
                (surface_df['moneyness'] >= 0.95) &  # Near ATM
                (surface_df['moneyness'] <= 1.05)
            ]
            
            if not bucket_data.empty:
                # Weight by proximity to ATM
                bucket_data = bucket_data.copy()
                bucket_data['atm_distance'] = abs(bucket_data['moneyness'] - 1.0)
                bucket_data['weight'] = 1.0 / (bucket_data['atm_distance'] + 0.01)
                
                weighted_iv = (bucket_data['implied_vol'] * bucket_data['weight']).sum() / bucket_data['weight'].sum()
                term_structure[bucket_name] = weighted_iv
        
        # Calculate term structure slope
        if '1m' in term_structure and '1y' in term_structure:
            term_structure['slope'] = term_structure['1y'] - term_structure['1m']
        
        return term_structure
    
    def calculate_volatility_skew(self, surface_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility skew metrics."""
        if surface_df.empty:
            return {}
        
        skew_metrics = {}
        
        # Focus on shorter-term options (1-3 months)
        short_term = surface_df[
            (surface_df['dte'] >= 15) & 
            (surface_df['dte'] <= 90)
        ]
        
        if short_term.empty:
            return {}
        
        # Calculate skew for different moneyness levels
        moneyness_buckets = {
            'otm_puts': (0.80, 0.95),    # 5-20% OTM puts
            'atm': (0.95, 1.05),         # ATM options
            'otm_calls': (1.05, 1.20)    # 5-20% OTM calls
        }
        
        bucket_ivs = {}
        for bucket_name, (min_money, max_money) in moneyness_buckets.items():
            bucket_data = short_term[
                (short_term['moneyness'] >= min_money) &
                (short_term['moneyness'] <= max_money)
            ]
            
            if not bucket_data.empty:
                bucket_ivs[bucket_name] = bucket_data['implied_vol'].mean()
        
        # Calculate skew metrics
        if 'otm_puts' in bucket_ivs and 'atm' in bucket_ivs:
            skew_metrics['put_skew'] = bucket_ivs['otm_puts'] - bucket_ivs['atm']
        
        if 'otm_calls' in bucket_ivs and 'atm' in bucket_ivs:
            skew_metrics['call_skew'] = bucket_ivs['otm_calls'] - bucket_ivs['atm']
        
        if 'put_skew' in skew_metrics and 'call_skew' in skew_metrics:
            skew_metrics['total_skew'] = skew_metrics['put_skew'] - skew_metrics['call_skew']
        
        return skew_metrics


class AdvancedOptionsAnalyzer:
    """Advanced options analysis combining multiple analytical techniques."""
    
    def __init__(self):
        self.bs_calc = BlackScholesCalculator()
        self.vol_analyzer = VolatilitySurfaceAnalyzer()
    
    def comprehensive_analysis(self, symbol: str, options_data: Dict, 
                             stock_price: float, risk_free_rate: float = 0.05) -> Dict:
        """Perform comprehensive options analysis."""
        
        analysis_results = {
            'symbol': symbol,
            'stock_price': stock_price,
            'analysis_timestamp': datetime.now(),
            'data_quality': 'unknown'
        }
        
        try:
            # Extract options dataframes
            calls_df = options_data.get('calls', pd.DataFrame())
            puts_df = options_data.get('puts', pd.DataFrame())
            
            if calls_df.empty and puts_df.empty:
                analysis_results['data_quality'] = 'no_data'
                return analysis_results
            
            # Combine options for surface analysis
            all_options = []
            
            if not calls_df.empty:
                calls_copy = calls_df.copy()
                calls_copy['contract_type'] = 'call'
                all_options.append(calls_copy)
            
            if not puts_df.empty:
                puts_copy = puts_df.copy()
                puts_copy['contract_type'] = 'put'
                all_options.append(puts_copy)
            
            combined_options = pd.concat(all_options, ignore_index=True)
            
            # Build IV surface
            surface_df = self.vol_analyzer.build_iv_surface(
                combined_options, stock_price, risk_free_rate
            )
            
            if surface_df.empty:
                analysis_results['data_quality'] = 'no_iv_data'
                return analysis_results
            
            analysis_results['data_quality'] = 'good'
            analysis_results['total_contracts'] = len(surface_df)
            
            # 1. Term Structure Analysis
            term_structure = self.vol_analyzer.calculate_term_structure(surface_df)
            analysis_results['term_structure'] = term_structure
            
            # 2. Volatility Skew Analysis
            skew_metrics = self.vol_analyzer.calculate_volatility_skew(surface_df)
            analysis_results['volatility_skew'] = skew_metrics
            
            # 3. Options Flow Analysis
            flow_analysis = self._analyze_options_flow(calls_df, puts_df)
            analysis_results['options_flow'] = flow_analysis
            
            # 4. Risk/Return Predictors
            predictors = self._calculate_predictive_factors(
                surface_df, term_structure, skew_metrics, flow_analysis, stock_price
            )
            analysis_results['predictive_factors'] = predictors
            
            # 5. Portfolio Construction Scores
            scores = self._calculate_portfolio_scores(predictors, term_structure, skew_metrics)
            analysis_results['portfolio_scores'] = scores
            
            return analysis_results
            
        except Exception as e:
            analysis_results['error'] = str(e)
            analysis_results['data_quality'] = 'error'
            return analysis_results
    
    def _analyze_options_flow(self, calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> Dict:
        """Analyze options flow patterns."""
        flow_metrics = {}
        
        try:
            # Volume analysis
            total_call_volume = calls_df['volume'].sum() if 'volume' in calls_df.columns else 0
            total_put_volume = puts_df['volume'].sum() if 'volume' in puts_df.columns else 0
            
            flow_metrics['call_volume'] = int(total_call_volume)
            flow_metrics['put_volume'] = int(total_put_volume)
            flow_metrics['total_volume'] = int(total_call_volume + total_put_volume)
            
            if total_call_volume > 0:
                flow_metrics['put_call_volume_ratio'] = total_put_volume / total_call_volume
            
            # Open Interest analysis
            total_call_oi = calls_df['open_interest'].sum() if 'open_interest' in calls_df.columns else 0
            total_put_oi = puts_df['open_interest'].sum() if 'open_interest' in puts_df.columns else 0
            
            flow_metrics['call_oi'] = int(total_call_oi)
            flow_metrics['put_oi'] = int(total_put_oi)
            flow_metrics['total_oi'] = int(total_call_oi + total_put_oi)
            
            if total_call_oi > 0:
                flow_metrics['put_call_oi_ratio'] = total_put_oi / total_call_oi
            
            # Sentiment indicators
            if 'put_call_volume_ratio' in flow_metrics:
                pc_vol = flow_metrics['put_call_volume_ratio']
                if pc_vol < 0.7:
                    flow_metrics['volume_sentiment'] = 'bullish'
                elif pc_vol > 1.3:
                    flow_metrics['volume_sentiment'] = 'bearish'
                else:
                    flow_metrics['volume_sentiment'] = 'neutral'
            
        except Exception as e:
            flow_metrics['error'] = str(e)
        
        return flow_metrics
    
    def _calculate_predictive_factors(self, surface_df: pd.DataFrame, term_structure: Dict,
                                    skew_metrics: Dict, flow_analysis: Dict, 
                                    stock_price: float) -> Dict:
        """Calculate predictive factors for portfolio construction."""
        
        factors = {}
        
        try:
            # Risk Predictors
            factors['forward_vol'] = term_structure.get('3m', 0.25)  # 3-month IV as forward vol
            factors['crash_risk'] = abs(skew_metrics.get('put_skew', 0)) / 0.05  # Normalized put skew
            
            # Return/Growth Predictors  
            factors['term_slope'] = term_structure.get('slope', 0)
            factors['call_put_flow_bias'] = self._calculate_flow_bias(flow_analysis)
            
            # Convexity measures
            factors['gamma_exposure'] = self._estimate_gamma_exposure(surface_df, stock_price)
            
            # Sharpe predictors
            if factors['forward_vol'] > 0:
                factors['vol_adjusted_return'] = 0.08 / factors['forward_vol']  # Assume 8% expected return
            else:
                factors['vol_adjusted_return'] = 0
            
            # Risk-adjusted measures
            crash_penalty = min(factors['crash_risk'] * 0.1, 0.05)
            factors['tail_adjusted_sharpe'] = factors['vol_adjusted_return'] - crash_penalty
            
        except Exception as e:
            factors['error'] = str(e)
        
        return factors
    
    def _calculate_flow_bias(self, flow_analysis: Dict) -> float:
        """Calculate flow bias from options activity."""
        try:
            pc_vol_ratio = flow_analysis.get('put_call_volume_ratio', 1.0)
            pc_oi_ratio = flow_analysis.get('put_call_oi_ratio', 1.0)
            
            # Lower ratios indicate more bullish bias
            vol_bias = 2.0 - pc_vol_ratio    # Bullish when > 1
            oi_bias = 2.0 - pc_oi_ratio
            
            # Combined bias score
            combined_bias = (vol_bias * 0.6 + oi_bias * 0.4)
            return max(-2, min(4, combined_bias))  # Clamp between -2 and 4
            
        except:
            return 1.0  # Neutral
    
    def _estimate_gamma_exposure(self, surface_df: pd.DataFrame, stock_price: float) -> float:
        """Estimate aggregate gamma exposure."""
        try:
            # Focus on near-term, near-money options
            gamma_options = surface_df[
                (surface_df['dte'] <= 45) &  # Short term
                (surface_df['moneyness'] >= 0.95) &  # Near ATM
                (surface_df['moneyness'] <= 1.05)
            ]
            
            if gamma_options.empty:
                return 0
            
            # Estimate gamma using Black-Scholes
            total_gamma = 0
            for _, option in gamma_options.iterrows():
                try:
                    greeks = self.bs_calc.calculate_greeks(
                        stock_price, option['strike'], option['time_to_expiry'],
                        0.05, option['implied_vol'], option['option_type']
                    )
                    total_gamma += greeks['gamma']
                except:
                    continue
            
            return total_gamma / len(gamma_options)  # Average gamma
            
        except:
            return 0
    
    def _calculate_portfolio_scores(self, factors: Dict, term_structure: Dict, 
                                  skew_metrics: Dict) -> Dict:
        """Calculate final portfolio construction scores."""
        
        scores = {}
        
        try:
            # Risk Score (0-10, higher = lower risk)
            base_risk = 5.0
            
            if factors.get('forward_vol', 0) < 0.20:
                base_risk += 2.0  # Low vol = lower risk
            elif factors.get('forward_vol', 0) > 0.35:
                base_risk -= 2.0  # High vol = higher risk
            
            if abs(skew_metrics.get('put_skew', 0)) > 0.05:
                base_risk -= 1.5  # High put skew = higher crash risk
            
            scores['risk_score'] = max(0, min(10, base_risk))
            
            # Growth Score (0-10, higher = better growth prospects)
            base_growth = 5.0
            
            if factors.get('call_put_flow_bias', 1) > 1.5:
                base_growth += 2.0  # Bullish flow = growth potential
            
            if factors.get('term_slope', 0) > 0.02:
                base_growth += 1.5  # Upward term structure = growth optionality
            
            if factors.get('gamma_exposure', 0) > 0.1:
                base_growth += 1.0  # High gamma = asymmetric upside
            
            scores['growth_score'] = max(0, min(10, base_growth))
            
            # Sharpe Score (0-10, higher = better risk-adjusted returns)
            base_sharpe = 5.0
            
            vol_adj_return = factors.get('vol_adjusted_return', 0)
            if vol_adj_return > 0.4:
                base_sharpe += 2.0
            elif vol_adj_return < 0.2:
                base_sharpe -= 1.0
            
            tail_adj_sharpe = factors.get('tail_adjusted_sharpe', 0)
            if tail_adj_sharpe > vol_adj_return:
                base_sharpe += 1.0  # Low tail risk penalty
            else:
                base_sharpe -= 1.0  # High tail risk penalty
            
            scores['sharpe_score'] = max(0, min(10, base_sharpe))
            
        except Exception as e:
            scores = {'risk_score': 5.0, 'growth_score': 5.0, 'sharpe_score': 5.0, 'error': str(e)}
        
        return scores