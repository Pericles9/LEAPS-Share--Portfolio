"""
Black-Scholes Option Pricing Model

Implementation of the Black-Scholes formula for European option pricing.
"""

import numpy as np
from scipy.stats import norm
from typing import Union, Optional
from dataclasses import dataclass


@dataclass
class OptionParameters:
    """Parameters for option pricing."""
    S: float  # Current stock price
    K: float  # Strike price
    T: float  # Time to expiration (in years)
    r: float  # Risk-free interest rate
    sigma: float  # Volatility (annualized)
    option_type: str = 'call'  # 'call' or 'put'


class BlackScholesModel:
    """Black-Scholes option pricing model."""
    
    def __init__(self):
        """Initialize the Black-Scholes model."""
        pass
    
    def calculate_d1_d2(self, S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
        """
        Calculate d1 and d2 parameters for Black-Scholes formula.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            
        Returns:
            Tuple of (d1, d2)
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2
    
    def calculate_price(self, S: float, K: float, T: float, r: float, sigma: float, 
                       option_type: str = 'call') -> float:
        """
        Calculate option price using Black-Scholes formula.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free interest rate
            sigma: Volatility (annualized)
            option_type: 'call' or 'put'
            
        Returns:
            Option price
        """
        if T <= 0:
            # Option has expired
            if option_type.lower() == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        d1, d2 = self.calculate_d1_d2(S, K, T, r, sigma)
        
        if option_type.lower() == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type.lower() == 'put':
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError("option_type must be 'call' or 'put'")
            
        return price
    
    def calculate_greeks(self, S: float, K: float, T: float, r: float, sigma: float,
                        option_type: str = 'call') -> dict:
        """
        Calculate option Greeks (Delta, Gamma, Theta, Vega, Rho).
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Volatility
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary containing Greeks
        """
        if T <= 0:
            return {
                'delta': 0, 'gamma': 0, 'theta': 0, 
                'vega': 0, 'rho': 0
            }
        
        d1, d2 = self.calculate_d1_d2(S, K, T, r, sigma)
        
        # Common calculations
        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)
        
        if option_type.lower() == 'call':
            delta = cdf_d1
            rho = K * T * np.exp(-r * T) * cdf_d2
            theta = (-S * pdf_d1 * sigma / (2 * np.sqrt(T)) 
                    - r * K * np.exp(-r * T) * cdf_d2)
        else:  # put
            delta = cdf_d1 - 1
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
            theta = (-S * pdf_d1 * sigma / (2 * np.sqrt(T)) 
                    + r * K * np.exp(-r * T) * norm.cdf(-d2))
        
        # Gamma and Vega are the same for calls and puts
        gamma = pdf_d1 / (S * sigma * np.sqrt(T))
        vega = S * pdf_d1 * np.sqrt(T)
        
        # Convert to more practical units
        theta /= 365  # Per day
        vega /= 100   # Per 1% volatility change
        rho /= 100    # Per 1% rate change
        
        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
    
    def implied_volatility(self, market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str = 'call', 
                          max_iterations: int = 100, tolerance: float = 1e-6) -> Optional[float]:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            market_price: Observed market price of the option
            S: Current stock price
            K: Strike price
            T: Time to expiration
            r: Risk-free rate
            option_type: 'call' or 'put'
            max_iterations: Maximum iterations for convergence
            tolerance: Convergence tolerance
            
        Returns:
            Implied volatility or None if no convergence
        """
        # Initial guess
        sigma = 0.2
        
        for _ in range(max_iterations):
            # Calculate option price and vega
            price = self.calculate_price(S, K, T, r, sigma, option_type)
            greeks = self.calculate_greeks(S, K, T, r, sigma, option_type)
            vega = greeks['vega'] * 100  # Convert back to decimal form
            
            # Newton-Raphson update
            price_diff = price - market_price
            
            if abs(price_diff) < tolerance:
                return sigma
                
            if vega == 0:
                return None
                
            sigma = sigma - price_diff / vega
            
            # Ensure sigma stays positive
            if sigma <= 0:
                sigma = 0.001
                
        return None  # No convergence