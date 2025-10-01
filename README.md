# 🚀 LEAPS Portfolio Management System

## 📊 **Advanced Options-Based Portfolio Construction with Real-Time Market Intelligence**

A sophisticated portfolio management system that leverages **options market data** and **advanced analytics** to build superior investment portfolios. Unlike traditional systems that rely solely on historical price data, this system incorporates the collective wisdom of options traders to predict future market movements.

## 🎯 **Key Features**

### 🔬 **Options-Based Intelligence**
- **Real-time Options Analysis**: Live implied volatility, Greeks, and term structure analysis
- **Market Sentiment Detection**: Volatility skew analysis reveals fear/greed levels  
- **Forward-Looking Predictions**: Options-implied drift and crash probability forecasting
- **Advanced Black-Scholes**: Comprehensive pricing models with volatility surfaces

### 📈 **Multiple Strategy Types**
- **🚀 Growth-Focused**: Emphasizes growth optionality and call option cheapness
- **🛡️ Defensive/Stability**: Prioritizes low volatility and risk parity weighting
- **⚖️ Sharpe-Optimized**: Maximizes risk-adjusted returns using options insights
- **💰 High-Income**: Targets premium-rich opportunities with risk parity
- **🔄 Market-Neutral**: Equal-weight baseline for comparison

### 🎮 **Interactive GUI Features**
- **ETF Universe Builder**: Select ETFs to automatically build diversified stock universes
- **Portfolio Creation Wizard**: Step-by-step guided portfolio construction
- **Custom Allocation Editor**: Interactive sliders for manual portfolio adjustments
- **Monte Carlo Simulation**: Risk assessment with customizable parameters
- **Real-time Performance Tracking**: Live metrics and rebalancing alerts

### 📊 **Data Sources & Analytics**
- **Polygon.io Integration**: Premium options data with full Greeks
- **TradingView Integration**: Multi-exchange price data with fallbacks
- **Advanced Caching System**: High-performance data management
- **Volatility Surface Analysis**: 3D implied volatility modeling
- **Risk Factor Decomposition**: Systematic vs idiosyncratic risk analysis

## 🛠️ **Technical Architecture**

### **Core Modules**
```
src/
├── analytics/          # Advanced options analytics & Black-Scholes
├── data/              # Data sources (Polygon, TradingView, ETF managers)
├── portfolio/         # Modern portfolio theory optimization
├── strategy/          # Options-based strategy engine
└── utils/             # Helpers and utilities
```

### **Key Technologies**
- **Python 3.11+** with advanced scientific computing stack
- **Real-time APIs**: Polygon.io Options API, TradingView data feeds
- **Mathematical Libraries**: NumPy, SciPy, Pandas for quantitative analysis
- **GUI Framework**: Tkinter with custom widgets and charting
- **Optimization**: SLSQP algorithm for portfolio optimization

## 📋 **Prerequisites**

### **Python Environment**
```bash
Python 3.11+
Virtual environment (recommended)
```

### **Required Packages**
```bash
numpy>=1.24.0
pandas>=1.5.0
scipy>=1.10.0
matplotlib>=3.6.0
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
tvDatafeed>=2.0.0
```

### **Optional but Recommended**
- **Polygon.io API Key**: For premium options data
- **Alpha Vantage API Key**: For additional market data

## 🚀 **Quick Start**

### **1. Installation**
```bash
# Clone the repository
git clone https://github.com/yourusername/leaps-portfolio-system.git
cd leaps-portfolio-system

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration (Optional)**
```bash
# Copy example config and add your API keys
cp config/example_config.json config/config.json
# Edit config/config.json with your API keys
```

### **3. Launch Application**
```bash
python portfolio_gui.py
```

## 📖 **Usage Guide**

### **Basic Workflow**
1. **🎯 ETF Selection**: Enter ETF symbols (e.g., `SPY, QQQ, XLK, XLF`)
2. **🏗️ Build Universe**: Click "Build Universe" to extract constituent stocks
3. **🚀 Create Portfolios**: Use the Portfolio Creation Wizard to select strategies
4. **📊 Analyze Results**: Review allocations, metrics, and risk assessments
5. **⚖️ Custom Adjustments**: Use allocation sliders for manual fine-tuning
6. **🎲 Risk Assessment**: Run Monte Carlo simulations for stress testing

### **Advanced Features**
- **Custom Allocation Tab**: Interactive portfolio weight adjustment
- **Monte Carlo Simulation**: Comprehensive risk analysis with 1000+ scenarios
- **Performance Metrics**: Sharpe ratio, VaR, maximum drawdown analysis
- **Rebalancing Tools**: Automated drift detection and rebalancing recommendations

## 🔬 **How It Works**

### **Options-Based Analysis Pipeline**

#### **Phase 1: Options Surface Construction**
```python
# For each stock, build comprehensive options surface
surface = OptionsSurface(
    iv_term_structure,    # 1M, 3M, 6M, 1Y implied volatility
    volatility_skew,      # Put/call IV differential (fear gauge)
    realized_volatility,  # Historical price volatility
    greeks_analysis      # Delta, gamma, vega, theta aggregation
)
```

#### **Phase 2: Predictive Factor Computation**
```python
factors = OptionsFactors(
    forward_vol_forecast,     # IV-based volatility prediction
    crash_probability,        # Tail risk from put skew
    implied_drift,           # Expected return from put-call parity
    growth_optionality,      # Growth potential from options
    sharpe_prediction       # Risk-adjusted return forecast
)
```

#### **Phase 3: Strategy-Specific Portfolio Construction**
```python
# Different strategies emphasize different factors
growth_portfolio = weight_by_growth_optionality(factors)
defensive_portfolio = weight_by_inverse_risk(factors)  
sharpe_portfolio = optimize_risk_adjusted_returns(factors)
```

## 📊 **Sample Output**

### **Portfolio Allocations (Growth Strategy)**
```
🚀 Options Growth-Focused Portfolio:
   MSFT: 31.2% (High growth optionality, cheap calls)
   NVDA: 24.8% (Strong implied drift, bullish sentiment)  
   AAPL: 18.5% (Stable vol premium, positive skew)
   GOOGL: 15.1% (Balanced risk/reward profile)
   TSLA: 10.4% (High volatility, growth potential)

Expected Return: 14.2% | Volatility: 18.9% | Sharpe: 0.75
```

### **Risk Metrics**
```
📈 Monte Carlo Results (1000 simulations):
   Mean Return: 12.8% ± 3.2%
   Value at Risk (5%): -$8,420
   Maximum Drawdown: -15.3%
   Probability of Loss: 23.1%
```

## 🔧 **Configuration**

### **API Configuration**
```json
{
  "polygon_io": {
    "api_key": "your_polygon_api_key_here",
    "tier": "starter"
  },
  "alpha_vantage": {
    "api_key": "your_alpha_vantage_key_here"
  },
  "settings": {
    "cache_enabled": true,
    "risk_free_rate": 0.05,
    "default_period": "1y"
  }
}
```

### **Performance Tuning**
- **Enable Caching**: Significantly improves performance for repeated analysis
- **Parallel Processing**: Configure CPU cores for concurrent analysis
- **Memory Management**: Automatic cleanup of large datasets

## 🧪 **Testing**

```bash
# Run allocation logic tests
python test_allocation_logic.py

# Test complete system integration
python test_complete_system.py

# Test options analytics
python test_enhanced_options.py
```

## 📚 **Documentation**

- **[User Manual](USER_MANUAL.md)**: Comprehensive usage guide
- **[System Summary](SYSTEM_SUMMARY.md)**: Technical overview and architecture

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ **Disclaimer**

This software is for educational and research purposes only. Past performance does not guarantee future results. Always consult with qualified financial advisors before making investment decisions. The authors are not responsible for any financial losses incurred through the use of this software.

## 🙏 **Acknowledgments**

- **Polygon.io** for comprehensive options data
- **TradingView** for reliable market data feeds
- **Scientific Python Community** for excellent mathematical libraries
- **Modern Portfolio Theory** pioneers for foundational concepts

---

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/yourusername/leaps-portfolio-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/leaps-portfolio-system/discussions)

**Built with ❤️ for quantitative finance enthusiasts**