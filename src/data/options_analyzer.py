"""
Options Chain Analysis Module - POLYGON.IO PREMIUM ONLY

🚀 GO BIG OR GO HOME - Real Polygon.io data only, no fallbacks!

Analyze options chains to determine bullish/bearish sentiment and market positioning
for options-based portfolio construction strategies using premium Polygon.io API.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
import time
from .polygon_source import PolygonOptionsSource


@dataclass
class OptionsMetrics:
    symbol: str
    put_call_ratio_volume: float
    put_call_ratio_oi: float
    total_call_volume: int
    total_put_volume: int
    total_call_oi: int
    total_put_oi: int
    max_call_oi_strike: Optional[float]
    max_put_oi_strike: Optional[float]
    current_price: float
    upside_resistance: Optional[float]
    downside_support: Optional[float]
    
    @property
    def bullish_score(self) -> float:
        """
        Calculate bullish sentiment score (0-10).
        Higher scores indicate more bullish sentiment.
        """
        score = 5.0  # Base neutral score
        
        # P/C ratio analysis (volume)
        if self.put_call_ratio_volume < 0.5:
            score += 3.0  # Very bullish
        elif self.put_call_ratio_volume < 0.8:
            score += 2.0  # Bullish
        elif self.put_call_ratio_volume < 1.2:
            score += 0.0  # Neutral
        elif self.put_call_ratio_volume < 1.5:
            score -= 1.5  # Bearish
        else:
            score -= 3.0  # Very bearish
        
        # P/C ratio analysis (open interest)
        if self.put_call_ratio_oi < 0.6:
            score += 1.5
        elif self.put_call_ratio_oi < 1.0:
            score += 0.5
        elif self.put_call_ratio_oi > 1.8:
            score -= 1.0
        
        # Volume analysis
        total_volume = self.total_call_volume + self.total_put_volume
        if total_volume > 10000:  # High volume
            if self.total_call_volume > self.total_put_volume:
                score += 0.5
            else:
                score -= 0.5
        
        return max(0.0, min(10.0, score))


class OptionsAnalyzer:
    """Analyze options chains for sentiment and portfolio construction - POLYGON.IO ONLY."""
    
    def __init__(self):
        """Initialize the options analyzer with Polygon.io premium data source ONLY."""
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        self.polygon_source = PolygonOptionsSource()
        self.success_rate = {'polygon_data': 0, 'failed': 0}
        print("   🚀 POLYGON.IO PREMIUM Options Analyzer - GO BIG OR GO HOME!")
    
    def get_comprehensive_options_data(self, symbol: str) -> Optional[OptionsMetrics]:
        """
        Get options data using Polygon.io premium API ONLY.
        
        🚀 GO BIG OR GO HOME - Real Polygon.io data only, no fallbacks!
        
        Args:
            symbol: Stock symbol
            
        Returns:
            OptionsMetrics object or None if Polygon.io fails
        """
        print(f"   🚀 Polygon.io PREMIUM analysis for {symbol}...")
        
        # POLYGON.IO ONLY - REAL DATA OR NOTHING!
        try:
            options_data = self._try_polygon_api(symbol)
            if options_data:
                self.success_rate['polygon_data'] += 1
                print(f"   ✅ SUCCESS: Polygon.io PREMIUM data for {symbol}")
                return options_data
            else:
                print(f"   ❌ Polygon.io returned no data for {symbol} - GO BIG OR GO HOME!")
                self.success_rate['failed'] += 1
                return None
        except Exception as e:
            print(f"   ❌ Polygon.io FAILED for {symbol}: {str(e)[:80]}...")
            self.success_rate['failed'] += 1
            return None

    def _try_polygon_api(self, symbol: str) -> Optional[OptionsMetrics]:
        """Try to get options data using Polygon.io premium API with LEAPS prioritization."""
        try:
            print(f"     🚀 Polygon.io API for {symbol}")
            
            # Use the PolygonOptionsSource which prioritizes LEAPS
            options_data = self.polygon_source.get_options_data(symbol)
            
            if not options_data or 'calls' not in options_data or 'puts' not in options_data:
                print(f"     ❌ No options data from Polygon.io for {symbol}")
                return None
            
            calls_df = options_data['calls']
            puts_df = options_data['puts']
            current_price = options_data.get('stock_price', 100.0)
            
            if calls_df.empty and puts_df.empty:
                print(f"     ❌ Empty options chains from Polygon.io for {symbol}")
                return None
            
            # Handle cases where we only have calls OR puts (due to API pagination)
            if calls_df.empty:
                print(f"     ⚠️ No calls data - using puts only for {symbol}")
            if puts_df.empty:
                print(f"     ⚠️ No puts data - using calls only for {symbol}")
            
            # Calculate metrics from Polygon.io data
            call_volume = calls_df['volume'].sum() if 'volume' in calls_df.columns else 0
            put_volume = puts_df['volume'].sum() if 'volume' in puts_df.columns else 0
            call_oi = calls_df['open_interest'].sum() if 'open_interest' in calls_df.columns else 0
            put_oi = puts_df['open_interest'].sum() if 'open_interest' in puts_df.columns else 0
            
            # Avoid division by zero
            pc_ratio_volume = put_volume / max(call_volume, 1)
            pc_ratio_oi = put_oi / max(call_oi, 1)
            
            # Find max OI strikes
            max_call_oi_strike = None
            max_put_oi_strike = None
            
            if 'open_interest' in calls_df.columns and not calls_df.empty:
                max_call_idx = calls_df['open_interest'].idxmax()
                max_call_oi_strike = calls_df.loc[max_call_idx, 'strike']
            
            if 'open_interest' in puts_df.columns and not puts_df.empty:
                max_put_idx = puts_df['open_interest'].idxmax()
                max_put_oi_strike = puts_df.loc[max_put_idx, 'strike']
            
            print(f"     ✅ Polygon.io metrics: P/C Volume={pc_ratio_volume:.2f}, P/C OI={pc_ratio_oi:.2f}")
            
            return OptionsMetrics(
                symbol=symbol,
                put_call_ratio_volume=pc_ratio_volume,
                put_call_ratio_oi=pc_ratio_oi,
                total_call_volume=int(call_volume),
                total_put_volume=int(put_volume),
                total_call_oi=int(call_oi),
                total_put_oi=int(put_oi),
                max_call_oi_strike=max_call_oi_strike,
                max_put_oi_strike=max_put_oi_strike,
                current_price=current_price,
                upside_resistance=max_call_oi_strike - current_price if max_call_oi_strike else None,
                downside_support=current_price - max_put_oi_strike if max_put_oi_strike else None
            )
            
        except Exception as e:
            print(f"     ❌ Polygon.io API error for {symbol}: {e}")
            return None

    def rank_stocks_by_sentiment(self, symbols: List[str]) -> List[Tuple[str, float]]:
        """
        Rank stocks by options sentiment using POLYGON.IO PREMIUM data only.
        
        🚀 LEAPS-focused growth strategy with PREMIUM bonuses for bullish sentiment!
        
        Args:
            symbols: List of stock symbols to analyze
            
        Returns:
            List of (symbol, score) tuples sorted by bullish sentiment
        """
        print("🚀 POLYGON.IO PREMIUM SENTIMENT ANALYSIS - LEAPS GROWTH STRATEGY")
        
        scores = []
        
        for symbol in symbols:
            try:
                print(f"\n📊 Analyzing {symbol} for LEAPS growth potential...")
                
                # Get Polygon.io premium options data
                options_data = self.get_comprehensive_options_data(symbol)
                
                if not options_data:
                    print(f"   ❌ No Polygon.io data for {symbol} - SKIPPED")
                    continue
                
                # Base sentiment score from options
                base_score = options_data.bullish_score
                print(f"   📈 Base bullish score: {base_score:.1f}/10")
                
                # 🚀 PREMIUM GROWTH BONUSES
                growth_bonus = 0.0
                
                # Bonus for premium stock price (growth stocks)
                if options_data.current_price > 200:
                    growth_bonus += 1.0
                    print(f"   💰 Premium stock price bonus: +1.0")
                elif options_data.current_price > 100:
                    growth_bonus += 0.5
                    print(f"   💰 Growth stock price bonus: +0.5")
                
                # Bonus for strong bullish sentiment (P/C ratio)
                if options_data.put_call_ratio_volume < 0.7:
                    growth_bonus += 1.5
                    print(f"   🚀 Strong bullish sentiment bonus: +1.5")
                elif options_data.put_call_ratio_volume < 1.0:
                    growth_bonus += 0.8
                    print(f"   📈 Bullish sentiment bonus: +0.8")
                
                # Bonus for high options activity (LEAPS interest)
                total_volume = options_data.total_call_volume + options_data.total_put_volume
                if total_volume > 50000:
                    growth_bonus += 1.0
                    print(f"   📊 High LEAPS activity bonus: +1.0")
                elif total_volume > 20000:
                    growth_bonus += 0.5
                    print(f"   📊 Good LEAPS activity bonus: +0.5")
                
                # Check for LEAPS availability bonus
                try:
                    leaps_data = self.polygon_source.get_leaps_options(symbol)
                    if leaps_data is not None and not leaps_data.empty:
                        growth_bonus += 2.0
                        leaps_count = len(leaps_data)
                        print(f"   🎯 LEAPS AVAILABLE bonus: +2.0 ({leaps_count} contracts)")
                except Exception as e:
                    print(f"   ⚠️ LEAPS check skipped: {e}")
                
                # Final growth-adjusted score
                final_score = min(10.0, base_score + growth_bonus)
                print(f"   🏆 FINAL GROWTH SCORE: {final_score:.1f}/10 (Base: {base_score:.1f} + Growth: {growth_bonus:.1f})")
                
                scores.append((symbol, final_score))
                
            except Exception as e:
                print(f"   ❌ Error analyzing {symbol}: {e}")
                continue
        
        # Sort by score (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        print(f"\n🚀 POLYGON.IO PREMIUM RANKINGS:")
        for i, (symbol, score) in enumerate(scores[:10], 1):
            print(f"   {i:2d}. {symbol:6s} - {score:.1f}/10 {'🚀' if score >= 8 else '📈' if score >= 6 else '📊'}")
        
        print(f"\n📊 Success Rate: {self.success_rate['polygon_data']} Polygon.io / {self.success_rate['failed']} Failed")
        
        return scores

    def print_success_rate(self):
        """Print the data source success rate."""
        polygon_success = self.success_rate['polygon_data']
        failures = self.success_rate['failed']
        total_attempts = polygon_success + failures
        
        if total_attempts > 0:
            success_pct = (polygon_success / total_attempts) * 100
            print(f"\n🚀 POLYGON.IO PREMIUM SUCCESS RATE:")
            print(f"   ✅ Polygon.io Premium: {polygon_success}/{total_attempts} ({success_pct:.1f}%)")
            print(f"   ❌ Failed: {failures}/{total_attempts} ({100-success_pct:.1f}%)")
            
            if success_pct >= 80:
                print(f"   🚀 EXCELLENT - Premium data quality!")
            elif success_pct >= 60:
                print(f"   📈 GOOD - Strong data coverage!")
            else:
                print(f"   ⚠️  NEEDS ATTENTION - Check Polygon.io subscription")
        else:
            print("   📊 No data requests made yet")