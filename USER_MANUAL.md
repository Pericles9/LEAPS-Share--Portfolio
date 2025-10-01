# Portfolio Management System - User Manual

## 🚀 Getting Started

### System Requirements
- **Operating System**: Windows 10/11, macOS, or Linux
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 500MB free space for application and data
- **Internet**: Required for market data fetching

### Quick Launch
1. **Simple Launch**: Double-click `launch_gui.py` or run:
   ```bash
   python launch_gui.py
   ```

2. **Direct Launch** (skip splash screen):
   ```bash
   python launch_gui.py --direct
   ```

3. **Show Quick Start Guide**:
   ```bash
   python launch_gui.py --guide
   ```

## 📊 Main Interface Overview

The Portfolio Management System features a tabbed interface with six main sections:

### 1. 📊 ETF Selection Tab
**Purpose**: Build your investment universe from ETF holdings

**Key Features**:
- **ETF Input Field**: Enter comma-separated ETF symbols (e.g., `SPY, QQQ, XLF, XLK`)
- **Browse ETFs Button**: Open database of 60+ available ETFs with descriptions
- **Universe Configuration**:
  - Min Weight Threshold: Only include stocks above this percentage in ETFs
  - Max Holdings per ETF: Limit number of stocks from each ETF
- **Universe Analysis Tree**: View selected stocks with source ETFs and weights

**Workflow**:
1. Enter or browse for ETF symbols
2. Adjust weight threshold (recommended: 2-5%)
3. Set max holdings (recommended: 15-25)
4. Click "Build Universe"
5. Review the resulting stock universe

### 2. 💼 Portfolio Overview Tab
**Purpose**: View and analyze your optimized portfolios

**Key Features**:
- **Portfolio Selector**: Choose from optimized strategies
- **Allocation Chart**: Interactive pie chart showing portfolio weights
- **Performance Metrics**: Expected return, volatility, Sharpe ratio, VaR, max drawdown
- **Holdings Table**: Top positions with weights and dollar values

**Available Portfolio Strategies**:
- **Equal Weight**: 1/N allocation across all stocks
- **Max Sharpe Ratio**: Optimized for best risk-adjusted returns
- **Minimum Volatility**: Lowest risk portfolio
- **Risk Parity**: Equal risk contribution from each stock
- **Maximum Diversification**: Optimized diversification ratio

**Key Metrics Explained**:
- **Expected Return**: Annualized expected portfolio return
- **Volatility**: Annualized standard deviation of returns
- **Sharpe Ratio**: Risk-adjusted return measure
- **VaR (95%)**: Maximum expected loss with 95% confidence
- **Max Drawdown**: Largest peak-to-trough decline

### 3. 🎲 Simulation Tab
**Purpose**: Run Monte Carlo simulations for risk analysis

**Key Features**:
- **Simulation Parameters**:
  - Number of Simulations: 100-10,000 (default: 1,000)
  - Time Horizon: 30-1,260 days (default: 252 = 1 year)
  - Initial Investment: Dollar amount to simulate
- **Results Visualization**:
  - Portfolio value paths over time
  - Final value distribution histogram
  - Returns distribution
  - Drawdown analysis
- **Statistics Panel**: Mean, median, standard deviation, VaR, probability of loss

**Best Practices**:
- Use 1,000+ simulations for reliable results
- Test multiple time horizons (90, 180, 252, 504 days)
- Compare different portfolio strategies
- Pay attention to tail risks (VaR metrics)

### 4. 📈 Metrics Tab
**Purpose**: Track performance and compare strategies over time

**Key Features**:
- **Period Selector**: Choose analysis timeframe (3mo, 6mo, 1y, 2y, 5y, max)
- **Performance Chart**: Multi-line chart showing strategy performance over time
- **Strategy Comparison Table**: Side-by-side metrics comparison
- **Risk Analysis**: Drawdown periods, volatility clustering

**Performance Analysis**:
- **Cumulative Returns**: Total return over selected period  
- **Rolling Metrics**: Time-varying Sharpe ratios and volatility
- **Correlation Analysis**: How strategies move together
- **Risk Attribution**: Sources of portfolio risk

### 5. ⚖️ Rebalancing Tab
**Purpose**: Manage portfolio rebalancing and drift analysis

**Key Features**:
- **Rebalancing Configuration**:
  - Frequency: Daily, Weekly, Monthly, Quarterly, Semi-Annual, Annual
  - Threshold: Percentage drift before rebalancing
  - Auto-rebalancing: Enable automatic execution
- **Drift Analysis**: Current vs. target allocation comparison
- **Rebalancing History**: Log of all past rebalancing events
- **Backtest Results**: Historical performance of rebalancing strategy

**Rebalancing Strategies**:
- **Calendar-Based**: Fixed schedule rebalancing
- **Threshold-Based**: Rebalance when drift exceeds limit
- **Volatility-Based**: Rebalance during high volatility periods
- **Performance-Based**: Rebalance after significant moves

**Cost Considerations**:
- Trading costs: Default 0.1% per trade
- Minimum trade size: Avoid small, uneconomical trades
- Tax implications: Consider tax-loss harvesting opportunities

### 6. ⚙️ Settings Tab
**Purpose**: Configure application preferences and performance

**Key Settings**:
- **General Settings**:
  - Default data period for analysis
  - Risk-free rate for Sharpe ratio calculations
- **File Management**:
  - Auto-save portfolio configurations
  - Auto-export analysis results
  - File organization preferences
- **Performance Settings**:
  - CPU cores for parallel processing
  - Data caching options
  - Memory usage optimization

## 🎯 Advanced Features

### ETF Universe Building
The system includes a comprehensive ETF database with 60+ ETFs covering:
- **Broad Market**: SPY, VTI, ITOT
- **Technology**: QQQ, XLK, VGT
- **Financials**: XLF, VFH, KBE
- **Healthcare**: XLV, VHT, IXJ
- **Energy**: XLE, VDE, IXC
- **International**: EFA, VEA, VXUS
- **Bonds**: AGG, BND, TLT
- **Commodities**: GLD, SLV, USO

### Portfolio Optimization Methods
- **Modern Portfolio Theory**: Mean-variance optimization
- **Black-Litterman**: Bayesian approach with market views
- **Risk Parity**: Equal risk contribution
- **Maximum Diversification**: Diversification ratio maximization
- **Hierarchical Risk Parity**: ML-based portfolio construction

### Monte Carlo Simulation Engine
- **Parametric Methods**: Normal, t-distribution, skewed-t
- **Non-Parametric**: Bootstrap resampling
- **Factor Models**: Multi-factor risk model simulation
- **Scenario Analysis**: Stress testing capabilities

### Rebalancing Algorithms
- **Threshold Rebalancing**: Drift-based triggers
- **Volatility Timing**: Market condition-based
- **Tax-Aware**: Consider tax implications
- **Transaction Cost**: Optimize for trading costs

## 📁 File Management System

### Automatic Organization
The system automatically organizes generated files into:
- **`analyses/`**: Analysis reports and documentation
- **`data_exports/`**: CSV, Excel, and JSON data files
- **`visualizations/`**: Charts, graphs, and images
- **`portfolios/`**: Portfolio optimization results
- **`reports/`**: HTML reports and summaries
- **`temp/`**: Temporary files (auto-cleanup)
- **`archives/`**: Compressed session archives

### File Operations
- **Auto-Registration**: Track all generated files with metadata
- **Smart Categorization**: Organize files by type and content
- **Session Reports**: Comprehensive HTML summaries
- **Archive Creation**: ZIP files for long-term storage
- **Cleanup Tools**: Remove old temporary files

## 🔧 Configuration Management

### Configuration File (`portfolio_gui_config.json`)
Stores all your preferences:
```json
{
  "selected_etfs": ["SPY", "QQQ", "XLF", "XLK"],
  "min_weight": 2.0,
  "max_holdings": 20,
  "rebalance_frequency": "Monthly",
  "initial_investment": 100000,
  "data_period": "1y",
  "risk_free_rate": 5.0,
  "auto_save": true
}
```

### Backup and Restore
- Configurations are automatically backed up
- Manual export/import functionality
- Session state preservation
- Portfolio history maintenance

## 📊 Data Sources and Quality

### Market Data Provider
- **Primary**: Yahoo Finance (yfinance)
- **Backup**: Alternative data sources for redundancy
- **Update Frequency**: Real-time during market hours
- **Historical Data**: Up to 20+ years for most assets

### Data Quality Checks
- **Missing Data**: Automatic forward-fill and interpolation
- **Outlier Detection**: Statistical outlier identification
- **Corporate Actions**: Dividend and split adjustments
- **Currency**: All data in USD

## 🚨 Risk Management

### Portfolio Risk Measures
- **Value at Risk (VaR)**: 1%, 5%, 95%, 99% confidence levels
- **Conditional VaR**: Expected shortfall
- **Maximum Drawdown**: Peak-to-trough decline
- **Volatility**: Standard deviation of returns
- **Beta**: Market sensitivity
- **Tracking Error**: Deviation from benchmark

### Risk Monitoring
- **Daily Risk Reports**: Automated risk assessment
- **Stress Testing**: Scenario analysis capabilities
- **Correlation Monitoring**: Track changing relationships
- **Concentration Risk**: Sector and single-stock limits

## 🎓 Best Practices

### Getting Started
1. **Start Simple**: Begin with 3-4 ETFs (e.g., SPY, QQQ, XLF)
2. **Understand the Data**: Review ETF holdings and overlaps
3. **Test with Small Amounts**: Use realistic but small initial investments
4. **Compare to Benchmarks**: Always compare to simple alternatives

### Portfolio Construction
1. **Diversification**: Aim for 20-50 stocks from different sectors
2. **Weight Limits**: Avoid over-concentration (max 10% in any single stock)
3. **Rebalancing**: Start with quarterly rebalancing
4. **Cost Awareness**: Consider trading costs in your analysis

### Risk Management
1. **Regular Reviews**: Monthly portfolio health checks
2. **Stress Testing**: Run scenarios during market stress
3. **Documentation**: Keep records of all decisions
4. **Continuous Learning**: Stay updated on portfolio theory

### Performance Monitoring
1. **Benchmark Comparison**: Always compare to relevant benchmarks
2. **Risk-Adjusted Returns**: Focus on Sharpe ratio, not just returns
3. **Consistency**: Look for consistent performance patterns
4. **Transaction Costs**: Include all costs in performance calculations

## 🆘 Troubleshooting

### Common Issues
1. **"No data available"**: Check internet connection and ETF symbols
2. **Optimization fails**: Reduce universe size or check data quality
3. **Slow performance**: Reduce number of simulations or enable caching
4. **Memory errors**: Close other applications or reduce data period

### Performance Optimization
1. **Enable Caching**: Store frequently used data
2. **Parallel Processing**: Use multiple CPU cores
3. **Reduce Simulation Count**: Start with 100-500 simulations
4. **Shorter Periods**: Use 6mo-1y for initial analysis

### Data Issues
1. **Missing ETF Data**: Check symbol spelling and availability
2. **Inconsistent Results**: Verify data period consistency
3. **Extreme Values**: Review data for corporate actions
4. **Slow Data Loading**: Check internet speed and try different times

## 📚 Additional Resources

### Educational Materials
- **Modern Portfolio Theory**: Markowitz (1952)
- **ETF Research**: Morningstar, ETF.com
- **Risk Management**: Professional Risk Manager (PRM) materials
- **Python Finance**: "Python for Finance" by Yves Hilpisch

### External Tools
- **Portfolio Visualizer**: Compare with online tools
- **Morningstar**: ETF research and analysis  
- **Yahoo Finance**: Market data and news
- **SEC EDGAR**: Official fund documents

### Support and Community
- **GitHub Repository**: Source code and issues
- **Documentation**: Comprehensive technical docs
- **User Community**: Share strategies and insights
- **Professional Support**: Available for institutional users

---

*This manual covers the core functionality of the Portfolio Management System. For technical details, see the README.md file and source code documentation.*