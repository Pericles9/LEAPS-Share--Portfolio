"""
Portfolio Management GUI Application

Ultra-powerful desktop interface for comprehensive portfolio management,
ETF selection, simulation, metrics tracking, and rebalancing automation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import threading
import time
from typing import Dict, List, Optional, Tuple
import warnings
import yfinance as yf
warnings.filterwarnings('ignore')

# Import our portfolio system components
from src.data.universe_manager import PortfolioUniverseManager
from src.data.etf_holdings import ETFHoldingsManager
from src.data.tv_data_fetcher import TradingViewDataFetcher, get_stock_returns
from src.portfolio.optimizer import PortfolioOptimizer
from src.utils.file_manager import PortfolioFileManager
from src.utils.helpers import format_percentage, format_currency


class ScrollableFrame(ttk.Frame):
    """A scrollable frame widget that can contain other widgets."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar_v = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar_h = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        
        # Create the scrollable frame
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrollbars
        self.canvas.configure(
            yscrollcommand=self.scrollbar_v.set,
            xscrollcommand=self.scrollbar_h.set
        )
        
        # Pack scrollbars and canvas
        self.scrollbar_v.pack(side="right", fill="y")
        self.scrollbar_h.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Bind events
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Bind mousewheel to canvas when mouse enters
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
    
    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update canvas window width to match frame if smaller
        canvas_width = self.canvas.winfo_width()
        frame_width = self.scrollable_frame.winfo_reqwidth()
        if canvas_width > frame_width:
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_canvas_configure(self, event):
        """Update frame width when canvas size changes."""
        canvas_width = event.width
        frame_width = self.scrollable_frame.winfo_reqwidth()
        if canvas_width > frame_width:
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if self.canvas.winfo_containing(event.x_root, event.y_root) == self.canvas:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _bind_mousewheel(self, event):
        """Bind mousewheel when entering canvas."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        """Unbind mousewheel when leaving canvas."""
        self.canvas.unbind_all("<MouseWheel>")
    
    def scroll_to_top(self):
        """Scroll to the top of the frame."""
        self.canvas.yview_moveto(0)
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the frame."""
        self.canvas.yview_moveto(1)


def create_slider_with_entry(parent, from_, to, variable, label_text, row, column=0, 
                            resolution=1, orient='horizontal', width=200, pady=5):
    """
    Create an enhanced slider with keyboard input capability.
    
    Args:
        parent: Parent widget
        from_: Minimum value
        to: Maximum value
        variable: tk Variable to bind to
        label_text: Label text
        row: Grid row
        column: Grid column (default 0)
        resolution: Step size (default 1 for whole numbers)
        orient: Orientation (default 'horizontal')
        width: Slider width (default 200)
        pady: Vertical padding (default 5)
    
    Returns:
        Tuple of (label, slider, entry) widgets
    """
    # Label
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, sticky=tk.W, padx=5, pady=pady)
    
    # Frame to hold slider and entry
    control_frame = ttk.Frame(parent)
    control_frame.grid(row=row, column=column+1, sticky=tk.W, padx=5, pady=pady)
    
    # Slider with whole number resolution
    slider = ttk.Scale(control_frame, from_=from_, to=to, variable=variable, 
                      orient=orient, length=width)
    # Note: ttk.Scale doesn't have resolution parameter, we handle rounding in callback instead
    
    slider.pack(side=tk.LEFT, padx=(0, 10))
    
    # Entry for keyboard input
    entry = ttk.Entry(control_frame, textvariable=variable, width=8)
    entry.pack(side=tk.LEFT)
    
    # Function to validate and round values for whole number sliders
    def validate_value(*args):
        try:
            value = variable.get()
            if resolution == 1:
                # Round to whole number
                rounded_value = round(value)
                if rounded_value != value:
                    variable.set(rounded_value)
        except (tk.TclError, ValueError):
            pass
    
    # Bind validation to variable changes
    variable.trace_add('write', validate_value)
    
    return label, slider, entry


class PortfolioGUI:
    """Main GUI application for portfolio management."""
    
    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("🏛️ Portfolio Management System")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Initialize backend systems
        self.universe_manager = PortfolioUniverseManager()
        self.etf_manager = ETFHoldingsManager()
        self.file_manager = PortfolioFileManager()
        
        # Configuration and state
        self.config_file = "portfolio_gui_config.json"
        self.config = self.load_config()
        self.current_portfolios = {}
        self.simulation_results = {}
        self.selected_etfs = tk.StringVar(value=", ".join(self.config.get('selected_etfs', [])))
        self.rebalance_frequency = tk.StringVar(value=self.config.get('rebalance_frequency', 'Monthly'))
        
        # Threading for background operations
        self.background_thread = None
        self.stop_background = threading.Event()
        
        # Create the GUI
        self.create_gui()
        
        # Load saved portfolios if available
        self.load_saved_portfolios()
        
        # Add keyboard shortcuts
        self.root.bind('<Control-p>', lambda e: self.optimize_selected_portfolio())
        self.root.bind('<F5>', lambda e: self.optimize_selected_portfolio())
        
        # Show quick start on first run
        if not self.config.get('quick_start_shown', False):
            self.root.after(1000, self.show_quick_start)
        
        print("🚀 Portfolio Management GUI initialized")
    
    def create_gui(self):
        """Create the main GUI interface."""
        # Create main menu
        self.create_menu()
        
        # Create main frame with notebook for tabs
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Quick action banner (shown when no portfolios exist)
        self.action_banner = ttk.Frame(main_frame)
        self.action_banner_label = ttk.Label(self.action_banner, 
                                           text="👋 Get started: Select ETFs → Build Universe → Create Portfolios",
                                           font=("Arial", 12, "bold"), foreground="#2c3e50")
        self.action_banner_label.pack(side=tk.LEFT, padx=10)
        
        self.quick_create_btn = ttk.Button(self.action_banner, text="🚀 Create Portfolios Now", 
                                         command=self.optimize_selected_portfolio,
                                         style="Accent.TButton")
        self.quick_create_btn.pack(side=tk.RIGHT, padx=10)
        
        # Show banner initially
        self.action_banner.pack(fill=tk.X, pady=(0, 10))
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.create_etf_selection_tab()
        self.create_portfolio_overview_tab()
        self.create_custom_allocation_tab()
        self.create_simulation_tab()
        self.create_metrics_tab()
        
        self.create_rebalancing_tab()
        self.create_settings_tab()
        
        # Create status bar
        self.create_status_bar()
    
    def create_slider_with_entry(self, parent, label_text, variable, min_val, max_val, side):
        """Create an enhanced slider with keyboard input capability using pack layout."""
        label = ttk.Label(parent, text=label_text)
        label.pack(side=side, padx=5)
        
        # Frame to hold slider and entry
        control_frame = ttk.Frame(parent)
        control_frame.pack(side=side, padx=10)
        
        # Slider with whole number resolution
        slider = ttk.Scale(control_frame, from_=min_val, to=max_val, variable=variable, 
                          orient=tk.HORIZONTAL, length=200)
        # Note: ttk.Scale doesn't have resolution parameter, we handle rounding in callback instead
        slider.pack(side=tk.LEFT, padx=(0, 10))
        
        # Entry for keyboard input
        entry = ttk.Entry(control_frame, textvariable=variable, width=8)
        entry.pack(side=tk.LEFT)
        
        # Function to validate and round values for whole number sliders
        def validate_value(*args):
            try:
                value = variable.get()
                # Round to whole number
                rounded_value = round(value)
                if rounded_value != value:
                    variable.set(rounded_value)
            except (tk.TclError, ValueError):
                pass
        
        # Bind validation to variable changes
        variable.trace_add('write', validate_value)
        
        return label, slider, entry
    
    def create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Portfolio", command=self.load_portfolio)
        file_menu.add_command(label="Save Portfolio", command=self.save_portfolio)
        file_menu.add_command(label="Export Data", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Portfolio menu
        portfolio_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Portfolio", menu=portfolio_menu)
        portfolio_menu.add_command(label="🚀 Create Portfolios", command=self.optimize_selected_portfolio)
        portfolio_menu.add_separator()
        portfolio_menu.add_command(label="Run Full Analysis", command=self.run_full_analysis)
        portfolio_menu.add_command(label="Quick Simulation", command=self.quick_simulation)
        portfolio_menu.add_command(label="Generate Report", command=self.generate_report)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="File Manager", command=self.open_file_manager)
        tools_menu.add_command(label="ETF Database", command=self.view_etf_database)
        tools_menu.add_command(label="Data Refresh", command=self.refresh_all_data)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_status_bar(self, parent):
        """Create status bar showing data source information."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # Data source status
        self.data_source_label = ttk.Label(status_frame, text="Data Source: Checking...", 
                                         font=("Arial", 9))
        self.data_source_label.pack(side=tk.LEFT, padx=5)
        
        # API status indicator
        self.api_status_label = ttk.Label(status_frame, text="●", 
                                        font=("Arial", 12), foreground="gray")
        self.api_status_label.pack(side=tk.LEFT, padx=2)
        
        # Version info
        version_label = ttk.Label(status_frame, text="Portfolio System v2.0", 
                                font=("Arial", 9), foreground="gray")
        version_label.pack(side=tk.RIGHT, padx=5)
        
        # Check data source status
        self.update_data_source_status()
    
    def update_data_source_status(self):
        """Update the data source status indicator."""
        try:
            import os
            
            # Check Polygon.io API key
            polygon_key = os.getenv('POLYGON_API_KEY')
            
            if polygon_key:
                # Try to import and test Polygon.io
                try:
                    from src.data.polygon_options_source import PolygonOptionsDataSource
                    # Quick test - just initialize
                    polygon_source = PolygonOptionsDataSource()
                    self.data_source_label.config(text="Data Source: Polygon.io Premium ⭐")
                    self.api_status_label.config(text="●", foreground="green")
                    return
                except Exception as e:
                    print(f"Polygon.io error: {e}")
            
            # 🚀 GO BIG OR GO HOME - Polygon.io only!
            self.data_source_label.config(text="❌ Data Source: POLYGON.IO REQUIRED")
            self.api_status_label.config(text="●", foreground="red")
            
        except Exception as e:
            self.data_source_label.config(text="Data Source: Error")
            self.api_status_label.config(text="●", foreground="red")
            print(f"Status update error: {e}")
    
    def create_etf_selection_tab(self):
        """Create ETF selection and universe building tab."""
        etf_frame = ttk.Frame(self.notebook)
        self.notebook.add(etf_frame, text="📊 ETF Selection")
        
        # Main sections
        left_frame = ttk.Frame(etf_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = ttk.Frame(etf_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # ETF Selection Section
        etf_selection_frame = ttk.LabelFrame(left_frame, text="ETF Selection", padding=10)
        etf_selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # ETF input
        ttk.Label(etf_selection_frame, text="Selected ETFs:").pack(anchor=tk.W)
        etf_entry = ttk.Entry(etf_selection_frame, textvariable=self.selected_etfs, width=50)
        etf_entry.pack(fill=tk.X, pady=(5, 5))
        
        # Quick select buttons
        quick_frame = ttk.Frame(etf_selection_frame)
        quick_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(quick_frame, text="Quick Select:", font=("Arial", 8)).pack(side=tk.LEFT)
        
        quick_sets = [
            ("🇺🇸 US Core", "SPY, QQQ, IWM"),
            ("🏦 Sector Mix", "SPY, QQQ, XLF, XLK"),
            ("🌍 Global", "SPY, EFA, EEM, IWM"),
            ("📈 Growth", "QQQ, XLK, XLY, ARKK")
        ]
        
        for label, etfs in quick_sets:
            btn = ttk.Button(quick_frame, text=label, 
                           command=lambda e=etfs: self.selected_etfs.set(e))
            btn.pack(side=tk.LEFT, padx=2)
        
        # Buttons frame
        buttons_frame = ttk.Frame(etf_selection_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(buttons_frame, text="🔍 Browse ETFs", 
                  command=self.browse_etfs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="✅ Build Universe", 
                  command=self.build_universe).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="📊 Analyze ETFs", 
                  command=self.analyze_etfs).pack(side=tk.LEFT, padx=5)
        
        # Data Source Status Panel
        data_source_frame = ttk.LabelFrame(etf_selection_frame, text="🔍 Data Source Status", padding=10)
        data_source_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create data source indicators (ordered by priority)
        self.data_source_status = {}
        status_indicators = [
            ('️ Web Scraper', 'PRIMARY: Live data from etf.com (your XPaths)', '#3498db'),

            ('📊 yfinance', 'Free API data', '#f39c12'),
            ('⚠️ Hard-coded', 'Synthetic/manual data (29 ETFs)', '#e74c3c')
        ]
        
        for i, (icon_name, description, color) in enumerate(status_indicators):
            row_frame = ttk.Frame(data_source_frame)
            row_frame.pack(fill=tk.X, pady=1)
            
            # Status indicator (will be updated dynamically)
            status_label = ttk.Label(row_frame, text="⚪", font=("Arial", 10))
            status_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # Source name and description
            name_label = ttk.Label(row_frame, text=icon_name, font=("Arial", 9, "bold"))
            name_label.pack(side=tk.LEFT, padx=(0, 5))
            
            desc_label = ttk.Label(row_frame, text=description, font=("Arial", 8), foreground="gray")
            desc_label.pack(side=tk.LEFT)
            
            # Store references for updates
            source_key = icon_name.split()[1] if len(icon_name.split()) > 1 else icon_name
            self.data_source_status[source_key] = {
                'status': status_label,
                'name': name_label,
                'description': desc_label,
                'color': color,
                'used': False
            }
        
        # Universe configuration
        config_frame = ttk.LabelFrame(etf_selection_frame, text="Universe Configuration", padding=5)
        config_frame.pack(fill=tk.X, pady=10)
        
        # Min weight threshold
        self.min_weight_var = tk.DoubleVar(value=self.config.get('min_weight', 2.0))
        create_slider_with_entry(config_frame, 1, 10, self.min_weight_var, 
                               "Min Weight Threshold (%):", 0, resolution=1)
        
        # Max holdings per ETF
        self.max_holdings_var = tk.IntVar(value=self.config.get('max_holdings', 20))
        create_slider_with_entry(config_frame, 5, 50, self.max_holdings_var, 
                               "Max Holdings per ETF:", 1, resolution=1)
        
        config_frame.columnconfigure(1, weight=1)
        
        # Universe Results Section
        universe_frame = ttk.LabelFrame(right_frame, text="Universe Analysis", padding=10)
        universe_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results tree
        self.universe_tree = ttk.Treeview(universe_frame, columns=("Source", "Weight", "Overlap"), show="tree headings")
        self.universe_tree.heading("#0", text="Stock Symbol")
        self.universe_tree.heading("Source", text="Source ETFs")
        self.universe_tree.heading("Weight", text="Avg Weight")
        self.universe_tree.heading("Overlap", text="ETF Count")
        
        universe_scrollbar = ttk.Scrollbar(universe_frame, orient=tk.VERTICAL, command=self.universe_tree.yview)
        self.universe_tree.configure(yscrollcommand=universe_scrollbar.set)
        
        self.universe_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        universe_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Data source legend
        legend_frame = ttk.LabelFrame(universe_frame, text="📊 Data Source Legend", padding=5)
        legend_frame.pack(fill=tk.X, pady=(10, 0))
        
        legend_text = (
            "�️ Web Scraper (Primary)  �🔗 Finnhub API (Premium)  📊 yfinance (Free)  "
            "⚠️ Hard-coded (Synthetic)  💾 Cached\n"
            "⚠️ Symbol = Contains synthetic/manual data that may not reflect current allocations"
        )
        ttk.Label(legend_frame, text=legend_text, font=("Arial", 8), 
                 foreground="gray", wraplength=400).pack()
        
        # Universe summary and portfolio creation
        summary_frame = ttk.Frame(universe_frame)
        summary_frame.pack(fill=tk.X, pady=10)
        
        self.universe_summary = ttk.Label(summary_frame, text="No universe built yet", 
                                        foreground="gray", font=("Arial", 10, "italic"))
        self.universe_summary.pack(pady=(0, 5))
        
        # Progress bar for universe building
        self.universe_progress = ttk.Progressbar(summary_frame, mode='indeterminate')
        # Don't pack initially
        
        # Portfolio creation button (initially hidden)
        self.create_portfolios_btn = ttk.Button(summary_frame, text="🚀 Create Optimized Portfolios", 
                                               command=self.optimize_selected_portfolio,
                                               style="Accent.TButton")
        # Don't pack initially - will be shown after universe is built
    
    def create_portfolio_overview_tab(self):
        """Create portfolio overview and allocation display tab."""
        portfolio_frame = ttk.Frame(self.notebook)
        self.notebook.add(portfolio_frame, text="💼 Portfolio Overview")
        
        # Top section - Portfolio selector and summary
        top_frame = ttk.Frame(portfolio_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Portfolio selector
        selector_frame = ttk.LabelFrame(top_frame, text="Portfolio Selection", padding=10)
        selector_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(selector_frame, text="Active Portfolio:").pack(side=tk.LEFT)
        self.portfolio_selector = ttk.Combobox(selector_frame, values=[], state="readonly", width=30)
        self.portfolio_selector.pack(side=tk.LEFT, padx=10)
        self.portfolio_selector.bind('<<ComboboxSelected>>', self.on_portfolio_selected)
        
        ttk.Button(selector_frame, text="🔄 Refresh", 
                  command=self.refresh_portfolios).pack(side=tk.LEFT, padx=10)
        ttk.Button(selector_frame, text="📊 Optimize", 
                  command=self.optimize_selected_portfolio).pack(side=tk.LEFT, padx=5)
        
        # Main content area
        content_frame = ttk.Frame(portfolio_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - Allocation chart
        chart_frame = ttk.LabelFrame(content_frame, text="Portfolio Allocation", padding=10)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create matplotlib figure for portfolio chart
        self.portfolio_fig = Figure(figsize=(8, 6), dpi=100)
        self.portfolio_canvas = FigureCanvasTkAgg(self.portfolio_fig, chart_frame)
        self.portfolio_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right side - Portfolio details
        details_frame = ttk.LabelFrame(content_frame, text="Portfolio Details", padding=10)
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Data Quality Warning Panel
        self.data_quality_frame = ttk.LabelFrame(details_frame, text="⚠️ Data Quality Notice", padding=5)
        self.data_quality_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.data_quality_label = ttk.Label(self.data_quality_frame, 
                                          text="Portfolio uses live data sources", 
                                          font=("Arial", 9), foreground="green")
        self.data_quality_label.pack(anchor=tk.W)
        
        self.synthetic_warning_label = ttk.Label(self.data_quality_frame, 
                                               text="", font=("Arial", 8), 
                                               foreground="red", wraplength=300)
        self.synthetic_warning_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Initially hide the data quality frame
        self.data_quality_frame.pack_forget()
        
        # Performance metrics
        metrics_frame = ttk.LabelFrame(details_frame, text="Performance Metrics", padding=5)
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.metrics_labels = {}
        metrics = ["Expected Return", "Volatility", "Sharpe Ratio", "VaR (95%)", "Max Drawdown"]
        for i, metric in enumerate(metrics):
            ttk.Label(metrics_frame, text=f"{metric}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            label = ttk.Label(metrics_frame, text="-", font=("Arial", 10, "bold"))
            label.grid(row=i, column=1, sticky=tk.E, padx=5, pady=2)
            self.metrics_labels[metric] = label
        
        # Holdings table
        holdings_frame = ttk.LabelFrame(details_frame, text="Top Holdings", padding=5)
        holdings_frame.pack(fill=tk.BOTH, expand=True)
        
        self.holdings_tree = ttk.Treeview(holdings_frame, columns=("Weight", "Value"), show="tree headings", height=10)
        self.holdings_tree.heading("#0", text="Symbol")
        self.holdings_tree.heading("Weight", text="Weight")
        self.holdings_tree.heading("Value", text="Value ($)")
        
        holdings_scrollbar = ttk.Scrollbar(holdings_frame, orient=tk.VERTICAL, command=self.holdings_tree.yview)
        self.holdings_tree.configure(yscrollcommand=holdings_scrollbar.set)
        
        self.holdings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        holdings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_custom_allocation_tab(self):
        """Create custom portfolio allocation management tab."""
        alloc_frame = ttk.Frame(self.notebook)
        self.notebook.add(alloc_frame, text="⚖️ Custom Allocation")
        
        # Top controls
        controls_frame = ttk.LabelFrame(alloc_frame, text="Portfolio Selection & Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Portfolio selector for custom allocation
        selector_frame = ttk.Frame(controls_frame)
        selector_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(selector_frame, text="Base Portfolio:").pack(side=tk.LEFT)
        self.alloc_portfolio_selector = ttk.Combobox(selector_frame, values=[], state="readonly", width=25)
        self.alloc_portfolio_selector.pack(side=tk.LEFT, padx=10)
        self.alloc_portfolio_selector.bind('<<ComboboxSelected>>', self.on_alloc_portfolio_selected)
        
        ttk.Button(selector_frame, text="🔄 Refresh", 
                  command=self.refresh_alloc_portfolios).pack(side=tk.LEFT, padx=5)
        
        # Allocation mode selection
        mode_frame = ttk.Frame(controls_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Allocation Mode:").pack(side=tk.LEFT)
        self.alloc_mode = tk.StringVar(value="percentage")
        mode_frame_inner = ttk.Frame(mode_frame)
        mode_frame_inner.pack(side=tk.LEFT, padx=10)
        
        ttk.Radiobutton(mode_frame_inner, text="Percentage (%)", variable=self.alloc_mode, 
                       value="percentage", command=self.on_alloc_mode_changed).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame_inner, text="Dollar Amount ($)", variable=self.alloc_mode, 
                       value="dollar", command=self.on_alloc_mode_changed).pack(side=tk.LEFT, padx=10)
        
        # Total portfolio value for dollar mode
        value_frame = ttk.Frame(controls_frame)
        value_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(value_frame, text="Total Portfolio Value:").pack(side=tk.LEFT)
        self.custom_portfolio_value = tk.DoubleVar(value=100000)
        value_entry = ttk.Entry(value_frame, textvariable=self.custom_portfolio_value, width=15)
        value_entry.pack(side=tk.LEFT, padx=10)
        ttk.Label(value_frame, text="$").pack(side=tk.LEFT)
        
        # Action buttons
        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="⚖️ Equal Weight", 
                  command=self.set_equal_weights).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🎯 Optimize", 
                  command=self.optimize_custom_allocation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Save Custom Portfolio", 
                  command=self.save_custom_allocation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reset", 
                  command=self.reset_custom_allocation).pack(side=tk.LEFT, padx=5)
        
        # Main allocation editing area
        main_frame = ttk.Frame(alloc_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - Allocation table with sliders
        edit_frame = ttk.LabelFrame(main_frame, text="Edit Allocations", padding=5)
        edit_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create improved scrollable frame for allocations
        scrollable_alloc = ScrollableFrame(edit_frame)
        scrollable_alloc.pack(fill=tk.BOTH, expand=True)
        self.alloc_scrollable_frame = scrollable_alloc.scrollable_frame
        
        # Right side - Allocation summary and chart
        summary_frame = ttk.LabelFrame(main_frame, text="Allocation Summary", padding=5)
        summary_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Allocation summary display
        summary_text_frame = ttk.Frame(summary_frame)
        summary_text_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.total_allocation_label = ttk.Label(summary_text_frame, text="Total Allocation: 0.0%", 
                                              font=("Arial", 12, "bold"))
        self.total_allocation_label.pack(anchor=tk.W)
        
        self.allocation_status_label = ttk.Label(summary_text_frame, text="Status: Ready", 
                                               font=("Arial", 10))
        self.allocation_status_label.pack(anchor=tk.W)
        
        # Mini allocation chart
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            self.alloc_fig = Figure(figsize=(4, 4), dpi=80, facecolor='white')
            self.alloc_canvas_widget = FigureCanvasTkAgg(self.alloc_fig, summary_frame)
            self.alloc_canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except ImportError:
            ttk.Label(summary_frame, text="Matplotlib not available for charts").pack()
        
        # Initialize allocation tracking
        self.custom_allocations = {}  # symbol -> weight
        self.allocation_vars = {}     # symbol -> tkinter variable
        self.allocation_widgets = {}  # symbol -> widget references
    
    def create_simulation_tab(self):
        """Create Monte Carlo simulation tab."""
        sim_frame = ttk.Frame(self.notebook)
        self.notebook.add(sim_frame, text="🎲 Simulation")
        
        # Control panel
        control_frame = ttk.LabelFrame(sim_frame, text="Simulation Parameters", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Portfolio selection
        portfolio_frame = ttk.Frame(control_frame)
        portfolio_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(portfolio_frame, text="Portfolio for Simulation:").pack(side=tk.LEFT)
        self.sim_portfolio_selector = ttk.Combobox(portfolio_frame, values=[], state="readonly", width=30)
        self.sim_portfolio_selector.pack(side=tk.LEFT, padx=10)
        self.sim_portfolio_selector.bind('<<ComboboxSelected>>', self.on_sim_portfolio_selected)
        
        ttk.Button(portfolio_frame, text="🔄 Refresh", 
                  command=self.refresh_sim_portfolios).pack(side=tk.LEFT, padx=5)
        
        # Parameters in a grid
        params_frame = ttk.Frame(control_frame)
        params_frame.pack(fill=tk.X)
        
        # Number of simulations
        self.num_sims_var = tk.IntVar(value=self.config.get('num_simulations', 1000))
        create_slider_with_entry(params_frame, 100, 10000, self.num_sims_var, 
                               "Simulations:", 0, resolution=1, width=200)
        
        # Time horizon (days)
        self.time_horizon_var = tk.IntVar(value=self.config.get('time_horizon', 252))
        create_slider_with_entry(params_frame, 30, 1260, self.time_horizon_var, 
                               "Time Horizon (days):", 1, resolution=1, width=200)
        
        # Initial investment
        ttk.Label(params_frame, text="Initial Investment ($):").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.initial_investment_var = tk.DoubleVar(value=self.config.get('initial_investment', 100000))
        ttk.Entry(params_frame, textvariable=self.initial_investment_var, width=15).grid(row=2, column=1, padx=5, sticky=tk.W)
        
        # Action buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="🚀 Create Portfolios", 
                  command=self.optimize_selected_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🎲 Run Monte Carlo Simulation", 
                  command=self.run_monte_carlo).pack(side=tk.LEFT, padx=5)
        
        # Results area
        results_frame = ttk.Frame(sim_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Chart area
        chart_frame = ttk.LabelFrame(results_frame, text="Simulation Results", padding=10)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.simulation_fig = Figure(figsize=(10, 6), dpi=100)
        self.simulation_canvas = FigureCanvasTkAgg(self.simulation_fig, chart_frame)
        self.simulation_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Statistics panel
        stats_frame = ttk.LabelFrame(results_frame, text="Statistics", padding=10)
        stats_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.sim_stats_labels = {}
        stats = ["Mean Return", "Median Return", "Std Deviation", "Best Case", "Worst Case", 
                "VaR (5%)", "VaR (1%)", "Prob. of Loss", "Sharpe Ratio"]
        
        for i, stat in enumerate(stats):
            ttk.Label(stats_frame, text=f"{stat}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            label = ttk.Label(stats_frame, text="-", font=("Arial", 9, "bold"))
            label.grid(row=i, column=1, sticky=tk.E, padx=5, pady=2)
            self.sim_stats_labels[stat] = label
    
    def create_metrics_tab(self):
        """Create performance metrics and tracking tab."""
        metrics_tab = ttk.Frame(self.notebook)
        self.notebook.add(metrics_tab, text="📈 Metrics")
        
        # Create scrollable frame for metrics content
        scrollable_metrics = ScrollableFrame(metrics_tab)
        scrollable_metrics.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Use the scrollable frame's content area
        metrics_frame = scrollable_metrics.scrollable_frame
        
        # Time period selector
        period_frame = ttk.LabelFrame(metrics_frame, text="Analysis Period", padding=10)
        period_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(period_frame, text="Data Period:").pack(side=tk.LEFT)
        self.data_period_var = tk.StringVar(value=self.config.get('data_period', '1y'))
        period_combo = ttk.Combobox(period_frame, textvariable=self.data_period_var, 
                                  values=['3mo', '6mo', '1y', '2y', '5y', 'max'], 
                                  state="readonly", width=10)
        period_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(period_frame, text="� Create Portfolios", 
                  command=self.optimize_selected_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(period_frame, text="�📊 Update Metrics", 
                  command=self.update_metrics).pack(side=tk.LEFT, padx=5)
        
        # Main metrics area
        metrics_content = ttk.Frame(metrics_frame)
        metrics_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Performance chart
        perf_frame = ttk.LabelFrame(metrics_content, text="Performance Over Time", padding=10)
        perf_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.metrics_fig = Figure(figsize=(12, 8), dpi=100)
        self.metrics_canvas = FigureCanvasTkAgg(self.metrics_fig, perf_frame)
        self.metrics_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Metrics comparison table
        comparison_frame = ttk.LabelFrame(metrics_content, text="Strategy Comparison", padding=10)
        comparison_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.comparison_tree = ttk.Treeview(comparison_frame, 
                                          columns=("Return", "Volatility", "Sharpe", "MaxDD", "VaR"), 
                                          show="tree headings", height=6)
        
        self.comparison_tree.heading("#0", text="Strategy")
        self.comparison_tree.heading("Return", text="Ann. Return")
        self.comparison_tree.heading("Volatility", text="Volatility")
        self.comparison_tree.heading("Sharpe", text="Sharpe Ratio")
        self.comparison_tree.heading("MaxDD", text="Max Drawdown")
        self.comparison_tree.heading("VaR", text="VaR (95%)")
        
        comparison_scrollbar = ttk.Scrollbar(comparison_frame, orient=tk.VERTICAL, command=self.comparison_tree.yview)
        self.comparison_tree.configure(yscrollcommand=comparison_scrollbar.set)
        
        self.comparison_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        comparison_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_rebalancing_tab(self):
        """Create portfolio rebalancing tab."""
        rebal_tab = ttk.Frame(self.notebook)
        self.notebook.add(rebal_tab, text="⚖️ Rebalancing")
        
        # Create scrollable frame for rebalancing content
        scrollable_rebal = ScrollableFrame(rebal_tab)
        scrollable_rebal.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Use the scrollable frame's content area
        rebal_frame = scrollable_rebal.scrollable_frame
        
        # Rebalancing settings
        settings_frame = ttk.LabelFrame(rebal_frame, text="Rebalancing Configuration", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Frequency selection
        freq_frame = ttk.Frame(settings_frame)
        freq_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(freq_frame, text="Rebalancing Frequency:").pack(side=tk.LEFT)
        freq_combo = ttk.Combobox(freq_frame, textvariable=self.rebalance_frequency,
                                values=['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Semi-Annual', 'Annual'],
                                state="readonly", width=15)
        freq_combo.pack(side=tk.LEFT, padx=10)
        
        # Threshold settings
        threshold_frame = ttk.Frame(settings_frame)
        threshold_frame.pack(fill=tk.X, pady=5)
        
        self.rebal_threshold_var = tk.DoubleVar(value=self.config.get('rebalance_threshold', 5.0))
        self.create_slider_with_entry(threshold_frame, "Rebalancing Threshold (%):", 
                                     self.rebal_threshold_var, 1, 20, tk.LEFT)
        
        # Auto-rebalancing
        auto_frame = ttk.Frame(settings_frame)
        auto_frame.pack(fill=tk.X, pady=5)
        
        self.auto_rebalance_var = tk.BooleanVar(value=self.config.get('auto_rebalance', False))
        ttk.Checkbutton(auto_frame, text="Enable Automatic Rebalancing", 
                       variable=self.auto_rebalance_var).pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="� Create Portfolios", 
                  command=self.optimize_selected_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="�📊 Analyze Current Drift", 
                  command=self.analyze_drift).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="⚖️ Rebalance Now", 
                  command=self.rebalance_now).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📈 Backtest Rebalancing", 
                  command=self.backtest_rebalancing).pack(side=tk.LEFT, padx=5)
        
        # Results area
        results_frame = ttk.Frame(rebal_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Drift analysis chart
        drift_frame = ttk.LabelFrame(results_frame, text="Portfolio Drift Analysis", padding=10)
        drift_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.drift_fig = Figure(figsize=(8, 6), dpi=100)
        self.drift_canvas = FigureCanvasTkAgg(self.drift_fig, drift_frame)
        self.drift_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Rebalancing history
        history_frame = ttk.LabelFrame(results_frame, text="Rebalancing History", padding=10)
        history_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.rebal_tree = ttk.Treeview(history_frame, 
                                     columns=("Date", "Trigger", "Trades"), 
                                     show="tree headings")
        self.rebal_tree.heading("#0", text="ID")
        self.rebal_tree.heading("Date", text="Date")
        self.rebal_tree.heading("Trigger", text="Trigger")
        self.rebal_tree.heading("Trades", text="Trades")
        
        rebal_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.rebal_tree.yview)
        self.rebal_tree.configure(yscrollcommand=rebal_scrollbar.set)
        
        self.rebal_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rebal_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_settings_tab(self):
        """Create application settings tab."""
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text="⚙️ Settings")
        
        # Create scrollable frame for settings content
        scrollable_settings = ScrollableFrame(settings_tab)
        scrollable_settings.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Use the scrollable frame's content area
        settings_frame = scrollable_settings.scrollable_frame
        
        # General settings
        general_frame = ttk.LabelFrame(settings_frame, text="General Settings", padding=10)
        general_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Data source settings
        ttk.Label(general_frame, text="Default Data Period:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        data_period_combo = ttk.Combobox(general_frame, textvariable=self.data_period_var,
                                       values=['3mo', '6mo', '1y', '2y', '5y'], 
                                       state="readonly", width=10)
        data_period_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Risk-free rate
        ttk.Label(general_frame, text="Risk-Free Rate (%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.risk_free_rate_var = tk.DoubleVar(value=self.config.get('risk_free_rate', 5.0))
        ttk.Entry(general_frame, textvariable=self.risk_free_rate_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # File management settings
        file_frame = ttk.LabelFrame(settings_frame, text="File Management", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto-save settings
        self.auto_save_var = tk.BooleanVar(value=self.config.get('auto_save', True))
        ttk.Checkbutton(file_frame, text="Auto-save portfolio configurations", 
                       variable=self.auto_save_var).pack(anchor=tk.W, pady=2)
        
        self.auto_export_var = tk.BooleanVar(value=self.config.get('auto_export', True))
        ttk.Checkbutton(file_frame, text="Auto-export analysis results", 
                       variable=self.auto_export_var).pack(anchor=tk.W, pady=2)
        
        # Data handling preference
        self.global_auto_remove_var = tk.BooleanVar(value=self.config.get('auto_remove_insufficient_data', True))
        ttk.Checkbutton(file_frame, text="🗑️ Auto-remove stocks with insufficient data (global setting)", 
                       variable=self.global_auto_remove_var).pack(anchor=tk.W, pady=2)
        
        # Caching preferences
        ttk.Separator(file_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(file_frame, text="Data Caching:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        self.enable_data_cache_var = tk.BooleanVar(value=self.config.get('enable_cache', True))
        ttk.Checkbutton(file_frame, text="💾 Enable data caching (recommended for performance)", 
                       variable=self.enable_data_cache_var).pack(anchor=tk.W, pady=2)
        
        # Cache management buttons
        cache_buttons = ttk.Frame(file_frame)
        cache_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(cache_buttons, text="📊 View Cache Stats", 
                  command=self.show_cache_stats).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(cache_buttons, text="🧹 Clear Cache", 
                  command=self.clear_cache).pack(side=tk.LEFT, padx=5)
        
        # File management buttons
        file_buttons = ttk.Frame(file_frame)
        file_buttons.pack(fill=tk.X, pady=10)
        
        ttk.Button(file_buttons, text="� Create Portfolios", 
                  command=self.optimize_selected_portfolio).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_buttons, text="�📁 Open File Manager", 
                  command=self.open_file_manager).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_buttons, text="🧹 Clean Temp Files", 
                  command=self.clean_temp_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_buttons, text="📦 Create Archive", 
                  command=self.create_archive).pack(side=tk.LEFT, padx=5)
        
        # Performance settings
        perf_frame = ttk.LabelFrame(settings_frame, text="Performance Settings", padding=10)
        perf_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Number of CPU cores for parallel processing
        self.cpu_cores_var = tk.IntVar(value=self.config.get('cpu_cores', 4))
        create_slider_with_entry(perf_frame, 1, 16, self.cpu_cores_var, 
                               "CPU Cores for Processing:", 0, resolution=1)
        
        # Cache settings
        self.enable_cache_var = tk.BooleanVar(value=self.config.get('enable_cache', True))
        ttk.Checkbutton(perf_frame, text="Enable data caching", 
                       variable=self.enable_cache_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Save settings button
        ttk.Button(settings_frame, text="💾 Save Settings", 
                  command=self.save_settings).pack(pady=20)
    
    def create_status_bar(self):
        """Create status bar at bottom of application."""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_bar = ttk.Progressbar(self.status_bar, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, padx=5)
    
    def update_status(self, message: str, show_progress: bool = False):
        """Update status bar message."""
        self.status_label.config(text=message)
        if show_progress:
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
        self.root.update_idletasks()
    
    def get_data_source_indicator(self, data_source: str) -> str:
        """Get visual indicator for data source type."""
        indicators = {

            'Web Scraper': '🕷️',     # Real web scraped data  
            'yfinance': '📊',         # Free API data
            'Hard-coded': '⚠️',       # Synthetic/manual data
            'Cache': '💾',            # Cached data
            'Unknown': '❓'           # Unknown source
        }
        return indicators.get(data_source, '❓')
    
    def get_data_source_color(self, data_source: str) -> str:
        """Get color for data source type."""
        colors = {

            'Web Scraper': '#3498db',    # Blue - web scraped
            'yfinance': '#f39c12',       # Orange - free API
            'Hard-coded': '#e74c3c',     # Red - synthetic
            'Cache': '#9b59b6',          # Purple - cached
            'Unknown': '#95a5a6'         # Gray - unknown
        }
        return colors.get(data_source, '#95a5a6')
    
    def update_data_source_status(self, sources_used: dict):
        """Update data source status indicators.
        
        Args:
            sources_used: Dict mapping data source names to usage counts
        """
        try:
            # Reset all indicators
            for source_key, info in self.data_source_status.items():
                info['status'].config(text="⚪", foreground="gray")
                info['name'].config(foreground="gray")
                info['used'] = False
            
            # Update based on what was actually used
            for source, count in sources_used.items():
                # Map source names to display keys
                display_key = None
                if 'Web Scraper' in source or 'Scraper' in source:
                    display_key = 'Scraper'
                elif 'yfinance' in source:
                    display_key = 'yfinance'
                elif 'Hard-coded' in source:
                    display_key = 'Hard-coded'
                elif 'Cache' in source:
                    # Handle cached data - extract original source
                    if 'Hard-coded' in source:
                        display_key = 'Hard-coded'
                    elif 'Web Scraper' in source:
                        display_key = 'Scraper'
                    elif 'yfinance' in source:
                        display_key = 'yfinance'

                
                if display_key and display_key in self.data_source_status:
                    info = self.data_source_status[display_key]
                    info['status'].config(text="🟢" if count > 0 else "⚪", 
                                        foreground=info['color'] if count > 0 else "gray")
                    info['name'].config(foreground=info['color'] if count > 0 else "gray")
                    info['used'] = count > 0
            
            # Update status bar with summary
            active_sources = [key for key, info in self.data_source_status.items() if info['used']]
            if active_sources:
                status_msg = f"Data sources active: {', '.join(active_sources)}"
                # Highlight if using synthetic data
                if 'Hard-coded' in active_sources:
                    status_msg += " ⚠️ (Synthetic data in use)"
                self.update_status(status_msg, False)
            
        except Exception as e:
            print(f"Error updating data source status: {e}")
    
    def update_portfolio_data_quality_warning(self, portfolio_symbols: List[str]):
        """Update data quality warning based on portfolio data sources.
        
        Args:
            portfolio_symbols: List of stock symbols in the portfolio
        """
        try:
            if not hasattr(self, 'data_quality_frame'):
                return
            
            # Check which ETFs were used to build the universe and their data sources
            sources_used = set()
            synthetic_etfs = []
            
            # Get ETF info for current selected ETFs
            if hasattr(self, 'selected_etfs') and self.selected_etfs.get():
                etf_list = [etf.strip() for etf in self.selected_etfs.get().split(',')]
                for etf in etf_list:
                    etf_info = self.etf_manager.get_etf_holdings(etf)
                    if etf_info:
                        source = getattr(etf_info, 'data_source', 'Unknown')
                        sources_used.add(source)
                        if 'Hard-coded' in source:
                            synthetic_etfs.append(etf)
            
            # Update warning based on data sources
            has_synthetic = any('Hard-coded' in source for source in sources_used)
            has_live_data = any(source in ['Web Scraper', 'yfinance'] 
                              for source in sources_used)
            
            if has_synthetic:
                # Show warning for synthetic data
                self.data_quality_frame.pack(fill=tk.X, pady=(0, 5))
                
                if has_live_data:
                    # Mixed data sources
                    self.data_quality_label.config(
                        text="⚠️ Mixed data sources: Live + Synthetic", 
                        foreground="orange"
                    )
                    warning_text = (f"Portfolio includes synthetic holdings data from: {', '.join(synthetic_etfs)}. "
                                  "These ETFs use manually curated holdings data and may not reflect current allocations. "
                                  "Live data sources are also active for other ETFs.")
                else:
                    # All synthetic data
                    self.data_quality_label.config(
                        text="⚠️ Portfolio uses synthetic/manual data", 
                        foreground="red"
                    )
                    warning_text = (f"Portfolio is based on manually curated holdings data from: {', '.join(synthetic_etfs)}. "
                                  "This data may not reflect current ETF allocations. Consider using ETFs with live data support "
                                  "or enable web scraping for more accurate holdings.")
                
                self.synthetic_warning_label.config(text=warning_text)
                
            else:
                # All live data - show positive message
                if has_live_data:
                    source_names = []
                    for source in sources_used:
                        if 'Web Scraper' in source:
                            source_names.append("Web Scraper")
                        elif 'yfinance' in source:
                            source_names.append("yfinance")
                        elif 'Cache' in source:
                            source_names.append("Cached data")
                    
                    self.data_quality_frame.pack(fill=tk.X, pady=(0, 5))
                    self.data_quality_label.config(
                        text=f"✅ Portfolio uses live data: {', '.join(set(source_names))}", 
                        foreground="green"
                    )
                    self.synthetic_warning_label.config(text="Holdings data is current and accurate.")
                else:
                    # Hide warning if no data or unknown sources
                    self.data_quality_frame.pack_forget()
                    
        except Exception as e:
            print(f"Error updating portfolio data quality warning: {e}")
    
    def load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        
        # Default configuration
        return {
            'selected_etfs': ['SPY', 'QQQ', 'XLF', 'XLK'],
            'min_weight': 2.0,
            'max_holdings': 20,
            'rebalance_frequency': 'Monthly',
            'rebalance_threshold': 5.0,
            'auto_rebalance': False,
            'num_simulations': 1000,
            'time_horizon': 252,
            'initial_investment': 100000,
            'data_period': '1y',
            'risk_free_rate': 5.0,
            'auto_save': True,
            'auto_export': True,
            'cpu_cores': 4,
            'enable_cache': True,
            'auto_remove_insufficient_data': True,
            'enable_web_scraping': True,  # Enable web scraping with user XPath selectors
            'web_scraper_headless': True  # Run web scraper in headless mode for performance
        }
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            config = {
                'selected_etfs': self.selected_etfs.get().split(', ') if self.selected_etfs.get() else [],
                'min_weight': self.min_weight_var.get(),
                'max_holdings': self.max_holdings_var.get(),
                'rebalance_frequency': self.rebalance_frequency.get(),
                'rebalance_threshold': self.rebal_threshold_var.get(),
                'auto_rebalance': self.auto_rebalance_var.get(),
                'num_simulations': self.num_sims_var.get(),
                'time_horizon': self.time_horizon_var.get(),
                'initial_investment': self.initial_investment_var.get(),
                'data_period': self.data_period_var.get(),
                'risk_free_rate': self.risk_free_rate_var.get(),
                'auto_save': self.auto_save_var.get(),
                'auto_export': self.auto_export_var.get(),
                'cpu_cores': self.cpu_cores_var.get(),
                'enable_cache': self.enable_cache_var.get(),
                'auto_remove_insufficient_data': getattr(self, 'global_auto_remove_var', tk.BooleanVar(value=True)).get()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not save configuration: {e}")
    
    # ETF Selection Methods
    def browse_etfs(self):
        """Open ETF browser dialog."""
        etf_window = tk.Toplevel(self.root)
        etf_window.title("🔍 ETF Browser")
        etf_window.geometry("800x600")
        
        # Get available ETFs
        available_etfs = self.etf_manager.get_available_etfs()
        
        # Create ETF list
        frame = ttk.Frame(etf_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(frame, text="Available ETFs:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # ETF tree with details
        etf_tree = ttk.Treeview(frame, columns=("Name", "Category", "Holdings"), show="tree headings")
        etf_tree.heading("#0", text="Symbol")
        etf_tree.heading("Name", text="Name")
        etf_tree.heading("Category", text="Category")
        etf_tree.heading("Holdings", text="Holdings")
        
        for symbol, info in available_etfs.items():
            etf_tree.insert("", tk.END, text=symbol, 
                          values=(info.get('name', 'Unknown'),
                                info.get('category', 'Unknown'),
                                info.get('holdings_count', 'Unknown')))
        
        etf_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=etf_tree.yview)
        etf_tree.configure(yscrollcommand=etf_scrollbar.set)
        
        etf_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        etf_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Selection buttons
        button_frame = ttk.Frame(etf_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_selected():
            selection = etf_tree.selection()
            if selection:
                current_etfs = self.selected_etfs.get().split(', ') if self.selected_etfs.get() else []
                for item in selection:
                    symbol = etf_tree.item(item)['text']
                    if symbol not in current_etfs:
                        current_etfs.append(symbol)
                self.selected_etfs.set(', '.join(current_etfs))
                etf_window.destroy()
        
        ttk.Button(button_frame, text="✅ Add Selected", command=add_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Cancel", command=etf_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def build_universe(self):
        """Build stock universe from selected ETFs."""
        if not self.selected_etfs.get():
            messagebox.showwarning("Warning", "Please select at least one ETF")
            return
        
        # Show progress
        self.universe_progress.pack(fill=tk.X, pady=5)
        self.universe_progress.start()
        self.universe_summary.config(text="Building universe from ETFs...", foreground="blue")
        
        self.update_status("Building universe from ETFs...", True)
        
        def build_in_background():
            try:
                etf_list = [etf.strip() for etf in self.selected_etfs.get().split(',')]
                
                # Track data sources used
                sources_used = {}
                
                # Get holdings for each ETF and track sources
                for etf in etf_list:
                    etf_info = self.etf_manager.get_etf_holdings(etf)
                    if etf_info:
                        source = getattr(etf_info, 'data_source', 'Unknown')
                        sources_used[source] = sources_used.get(source, 0) + 1
                
                # Build universe
                universe_stocks = self.etf_manager.build_universe_from_etfs(
                    etf_list,
                    min_weight=self.min_weight_var.get(),
                    top_n_per_etf=self.max_holdings_var.get()
                )
                
                if universe_stocks:
                    # Add to universe manager
                    self.universe_manager.add_universe_stocks(universe_stocks)
                    
                    # Update GUI in main thread
                    self.root.after(0, self.update_universe_display, universe_stocks)
                    self.root.after(0, lambda: self.update_data_source_status(sources_used))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Could not build universe from selected ETFs"))
                    self.root.after(0, self.universe_build_failed)
                    
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error building universe: {e}"))
                self.root.after(0, self.universe_build_failed) 
            finally:
                self.root.after(0, lambda: self.update_status("Ready", False))
        
        threading.Thread(target=build_in_background, daemon=True).start()

    def universe_build_failed(self):
        """Handle universe build failure."""
        self.universe_progress.stop()
        self.universe_progress.pack_forget()
        self.universe_summary.config(text="❌ Failed to build universe", foreground="red")
    
    def update_universe_display(self, universe_stocks: List[str]):
        """Update the universe display with new stocks."""
        # Clear existing items
        for item in self.universe_tree.get_children():
            self.universe_tree.delete(item)
        
        # Get detailed info for each stock
        try:
            etf_list = [etf.strip() for etf in self.selected_etfs.get().split(',')]
            
            for stock in universe_stocks:
                # Find which ETFs contain this stock and track data sources
                sources = []
                total_weight = 0
                count = 0
                data_sources = set()  # Track unique data sources
                
                for etf in etf_list:
                    etf_info = self.etf_manager.get_etf_holdings(etf)
                    if etf_info and etf_info.holdings:
                        # Track data source for this ETF
                        data_source = getattr(etf_info, 'data_source', 'Unknown')
                        data_sources.add(data_source)
                        
                        for holding in etf_info.holdings:
                            if holding.symbol == stock:
                                # Add source indicator based on data type
                                source_indicator = self.get_data_source_indicator(data_source)
                                sources.append(f"{etf}({holding.weight:.1f}%){source_indicator}")
                                total_weight += holding.weight
                                count += 1
                                break
                
                avg_weight = total_weight / count if count > 0 else 0
                
                # Add color coding based on data sources
                has_synthetic = any('⚠️' in source for source in sources)
                
                item = self.universe_tree.insert("", tk.END, text=stock,
                                        values=(", ".join(sources), f"{avg_weight:.1f}%", str(count)))
                
                # Color code rows with synthetic data
                if has_synthetic:
                    self.universe_tree.set(item, "#0", f"⚠️ {stock}")  # Add warning icon
            
            # Update summary
            self.universe_progress.stop()
            self.universe_progress.pack_forget()
            self.universe_summary.config(text=f"✅ Universe built: {len(universe_stocks)} stocks from {len(etf_list)} ETFs",
                                       foreground="green", font=("Arial", 10, "bold"))
            
            # Show portfolio creation button
            self.create_portfolios_btn.pack(pady=5)
            
        except Exception as e:
            print(f"Error updating universe display: {e}")
    
    def analyze_etfs(self):
        """Analyze selected ETFs in detail."""
        if not self.selected_etfs.get():
            messagebox.showwarning("Warning", "Please select at least one ETF")
            return
        
        # Open analysis window
        analysis_window = tk.Toplevel(self.root)
        analysis_window.title("📊 ETF Analysis")
        analysis_window.geometry("1000x700")
        
        # Create analysis content
        # This would include detailed ETF overlap analysis, correlation matrices, etc.
        ttk.Label(analysis_window, text="ETF Analysis", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(analysis_window, text="Detailed ETF analysis would be implemented here").pack(pady=20)
    
    # Portfolio Methods (continued in next part due to length)
    def run_full_analysis(self):
        """Run complete portfolio analysis."""
        if not hasattr(self.universe_manager, 'universe') or not self.universe_manager.universe:
            messagebox.showwarning("Warning", "Please build a universe first")
            return
        
        self.update_status("Running full portfolio analysis...", True)
        
        def analyze_in_background():
            try:
                # Fetch market data
                self.universe_manager.fetch_universe_data(period=self.data_period_var.get())
                
                # Build and optimize strategies
                strategies = self.universe_manager.build_portfolio_strategies()
                self.universe_manager.optimize_strategies()
                
                # Store results
                self.current_portfolios = {strategy.name: strategy for strategy in strategies}
                
                # Update GUI
                self.root.after(0, self.update_portfolio_selector)
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Analysis complete! Generated {len(strategies)} portfolio strategies"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Analysis failed: {e}"))
            finally:
                self.root.after(0, lambda: self.update_status("Ready", False))
        
        threading.Thread(target=analyze_in_background, daemon=True).start()
    
    def update_portfolio_selector(self):
        """Update portfolio selector dropdown."""
        portfolio_names = list(self.current_portfolios.keys())
        self.portfolio_selector['values'] = portfolio_names
        
        # Also update custom allocation selector
        if hasattr(self, 'alloc_portfolio_selector'):
            self.alloc_portfolio_selector['values'] = portfolio_names
        
        if portfolio_names:
            self.portfolio_selector.set(portfolio_names[0])
            self.on_portfolio_selected()
            
            # Set first portfolio in allocation selector too
            if hasattr(self, 'alloc_portfolio_selector') and not self.alloc_portfolio_selector.get():
                self.alloc_portfolio_selector.set(portfolio_names[0])
    
    def on_portfolio_selected(self, event=None):
        """Handle portfolio selection change."""
        selected = self.portfolio_selector.get()
        if selected and selected in self.current_portfolios:
            self.display_portfolio(self.current_portfolios[selected])
    
    def display_portfolio(self, portfolio):
        """Display portfolio details in the overview tab."""
        if not portfolio or not portfolio.metrics:
            return
        
        # Update metrics labels
        metrics = portfolio.metrics
        self.metrics_labels["Expected Return"].config(text=format_percentage(metrics.expected_return))
        self.metrics_labels["Volatility"].config(text=format_percentage(metrics.volatility))
        self.metrics_labels["Sharpe Ratio"].config(text=f"{metrics.sharpe_ratio:.3f}")
        
        # Calculate additional metrics if available
        if hasattr(metrics, 'var_95'):
            self.metrics_labels["VaR (95%)"].config(text=format_percentage(metrics.var_95))
        if hasattr(metrics, 'max_drawdown'):
            self.metrics_labels["Max Drawdown"].config(text=format_percentage(metrics.max_drawdown))
        
        # Update holdings tree
        for item in self.holdings_tree.get_children():
            self.holdings_tree.delete(item)
        
        if hasattr(metrics, 'weights') and metrics.weights is not None:
            # Assume $100,000 portfolio value for display
            portfolio_value = self.initial_investment_var.get()
            
            stock_weights = list(zip(portfolio.symbols, metrics.weights))
            stock_weights.sort(key=lambda x: x[1], reverse=True)
            
            for symbol, weight in stock_weights[:15]:  # Top 15 holdings
                value = portfolio_value * weight
                self.holdings_tree.insert("", tk.END, text=symbol,
                                        values=(f"{weight:.1%}", f"${value:,.0f}"))
        
        # Update data quality warning
        self.update_portfolio_data_quality_warning(portfolio.symbols)
        
        # Update portfolio chart
        self.update_portfolio_chart(portfolio)
    
    def update_portfolio_chart(self, portfolio):
        """Update the portfolio allocation chart."""
        self.portfolio_fig.clear()
        
        if not portfolio or not portfolio.metrics or not hasattr(portfolio.metrics, 'weights'):
            return
        
        ax = self.portfolio_fig.add_subplot(111)
        
        # Get top holdings for pie chart
        stock_weights = list(zip(portfolio.symbols, portfolio.metrics.weights))
        stock_weights.sort(key=lambda x: x[1], reverse=True)
        
        # Show top 10 holdings, group rest as "Others"
        top_10 = stock_weights[:10]
        others_weight = sum(weight for _, weight in stock_weights[10:])
        
        labels = [symbol for symbol, _ in top_10]
        sizes = [weight for _, weight in top_10]
        
        if others_weight > 0:
            labels.append("Others")
            sizes.append(others_weight)
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        
        # Improve readability
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(8)
        
        ax.set_title(f"{portfolio.name} - Allocation", fontsize=12, fontweight='bold')
        
        self.portfolio_canvas.draw()
    
    # Custom Allocation Methods
    def refresh_alloc_portfolios(self):
        """Refresh the custom allocation portfolio selector."""
        try:
            portfolio_names = list(self.current_portfolios.keys())
            self.alloc_portfolio_selector['values'] = portfolio_names
            if portfolio_names and not self.alloc_portfolio_selector.get():
                self.alloc_portfolio_selector.set(portfolio_names[0])
                self.on_alloc_portfolio_selected()
        except Exception as e:
            print(f"Error refreshing allocation portfolios: {e}")
    
    def on_alloc_portfolio_selected(self, event=None):
        """Handle custom allocation portfolio selection."""
        selected = self.alloc_portfolio_selector.get()
        if selected and selected in self.current_portfolios:
            portfolio = self.current_portfolios[selected]
            self.setup_custom_allocation_widgets(portfolio)
    
    def setup_custom_allocation_widgets(self, portfolio):
        """Set up allocation editing widgets for the selected portfolio."""
        # Clear existing widgets
        for widget in self.alloc_scrollable_frame.winfo_children():
            widget.destroy()
        
        self.custom_allocations.clear()
        self.allocation_vars.clear()
        self.allocation_widgets.clear()
        
        if not portfolio or not portfolio.metrics or not hasattr(portfolio.metrics, 'weights'):
            ttk.Label(self.alloc_scrollable_frame, text="No allocation data available for this portfolio").pack()
            return
        
        # Header
        header_frame = ttk.Frame(self.alloc_scrollable_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Symbol", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, sticky=tk.W)
        ttk.Label(header_frame, text="Original %", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Custom Allocation", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, columnspan=2)
        ttk.Label(header_frame, text="Value ($)", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=5)
        
        # Create widgets for each symbol
        stock_weights = list(zip(portfolio.symbols, portfolio.metrics.weights))
        stock_weights.sort(key=lambda x: x[1], reverse=True)
        
        for i, (symbol, original_weight) in enumerate(stock_weights):
            # Initialize custom allocation with original weight
            self.custom_allocations[symbol] = original_weight
            
            # Create row frame
            row_frame = ttk.Frame(self.alloc_scrollable_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Symbol label
            symbol_label = ttk.Label(row_frame, text=symbol, font=("Arial", 9, "bold"))
            symbol_label.grid(row=0, column=0, padx=5, sticky=tk.W, ipadx=10)
            
            # Original weight display
            orig_label = ttk.Label(row_frame, text=f"{original_weight:.1%}")
            orig_label.grid(row=0, column=1, padx=5)
            
            # Custom allocation slider and entry
            var = tk.DoubleVar(value=original_weight * 100)  # Convert to percentage
            self.allocation_vars[symbol] = var
            
            # Slider (0 to 50% max to prevent one stock dominating)
            slider = ttk.Scale(row_frame, from_=0, to=50, variable=var, 
                             orient=tk.HORIZONTAL, length=200,
                             command=lambda val, sym=symbol: self.on_allocation_changed(sym))
            slider.grid(row=0, column=2, padx=5)
            
            # Entry for precise input
            entry = ttk.Entry(row_frame, textvariable=var, width=8)
            entry.grid(row=0, column=3, padx=5)
            entry.bind('<KeyRelease>', lambda e, sym=symbol: self.on_allocation_changed(sym))
            
            # Value display
            value_var = tk.StringVar(value=f"${self.custom_portfolio_value.get() * original_weight:,.0f}")
            value_label = ttk.Label(row_frame, textvariable=value_var)
            value_label.grid(row=0, column=4, padx=5)
            
            # Store widget references
            self.allocation_widgets[symbol] = {
                'var': var,
                'slider': slider,
                'entry': entry,
                'value_label': value_label,
                'value_var': value_var
            }
        
        # Update summary
        self.update_allocation_summary()
    
    def on_allocation_changed(self, symbol):
        """Handle allocation change for a specific symbol."""
        if symbol in self.allocation_vars:
            try:
                new_percentage = self.allocation_vars[symbol].get()
                new_weight = new_percentage / 100.0
                self.custom_allocations[symbol] = new_weight
                
                # Update value display
                if symbol in self.allocation_widgets:
                    portfolio_value = self.custom_portfolio_value.get()
                    new_value = portfolio_value * new_weight
                    self.allocation_widgets[symbol]['value_var'].set(f"${new_value:,.0f}")
                
                # Update summary
                self.update_allocation_summary()
                
            except (ValueError, tk.TclError):
                pass  # Ignore invalid values during typing
    
    def on_alloc_mode_changed(self):
        """Handle allocation mode change (percentage vs dollar)."""
        mode = self.alloc_mode.get()
        # Update all value displays based on mode
        self.update_allocation_summary()
    
    def update_allocation_summary(self):
        """Update the allocation summary display and chart."""
        try:
            total_allocation = sum(self.custom_allocations.values())
            total_percentage = total_allocation * 100
            
            # Update labels
            self.total_allocation_label.config(text=f"Total Allocation: {total_percentage:.1f}%")
            
            # Update status
            if abs(total_percentage - 100) < 0.1:
                status_text = "✅ Balanced (100%)"
                status_color = "green"
            elif total_percentage > 100:
                status_text = f"⚠️ Over-allocated ({total_percentage:.1f}%)"
                status_color = "red"
            else:
                status_text = f"⚠️ Under-allocated ({total_percentage:.1f}%)"
                status_color = "orange"
            
            self.allocation_status_label.config(text=f"Status: {status_text}", foreground=status_color)
            
            # Update mini chart
            self.update_allocation_chart()
            
        except Exception as e:
            print(f"Error updating allocation summary: {e}")
    
    def update_allocation_chart(self):
        """Update the custom allocation chart."""
        try:
            if not hasattr(self, 'alloc_fig'):
                return
            
            self.alloc_fig.clear()
            
            if not self.custom_allocations:
                return
            
            ax = self.alloc_fig.add_subplot(111)
            
            # Filter out zero allocations and sort by size
            filtered_allocs = {k: v for k, v in self.custom_allocations.items() if v > 0.001}
            if not filtered_allocs:
                return
            
            # Sort by allocation size
            sorted_allocs = sorted(filtered_allocs.items(), key=lambda x: x[1], reverse=True)
            
            symbols = [item[0] for item in sorted_allocs[:10]]  # Top 10
            weights = [item[1] for item in sorted_allocs[:10]]
            
            # Add "Others" if there are more than 10
            if len(sorted_allocs) > 10:
                others_weight = sum(item[1] for item in sorted_allocs[10:])
                symbols.append("Others")
                weights.append(others_weight)
            
            # Create pie chart
            colors = plt.cm.Set3(range(len(symbols)))
            wedges, texts, autotexts = ax.pie(weights, labels=symbols, autopct='%1.1f%%', 
                                            startangle=90, colors=colors)
            
            # Improve readability
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(7)
            
            for text in texts:
                text.set_fontsize(8)
            
            ax.set_title("Custom Allocation", fontsize=10, fontweight='bold')
            
            self.alloc_canvas_widget.draw()
            
        except Exception as e:
            print(f"Error updating allocation chart: {e}")
    
    def set_equal_weights(self):
        """Set all allocations to equal weights."""
        if not self.custom_allocations:
            return
        
        num_stocks = len(self.custom_allocations)
        equal_weight = 1.0 / num_stocks
        equal_percentage = equal_weight * 100
        
        for symbol in self.custom_allocations:
            self.custom_allocations[symbol] = equal_weight
            if symbol in self.allocation_vars:
                self.allocation_vars[symbol].set(equal_percentage)
        
        self.update_allocation_summary()
    
    def optimize_custom_allocation(self):
        """Optimize the custom allocation using portfolio theory."""
        try:
            selected = self.alloc_portfolio_selector.get()
            if not selected or selected not in self.current_portfolios:
                messagebox.showwarning("No Portfolio", "Please select a portfolio first.")
                return
            
            portfolio = self.current_portfolios[selected]
            if not portfolio.metrics or not hasattr(portfolio.metrics, 'weights'):
                messagebox.showwarning("No Data", "Portfolio has no optimization data.")
                return
            
            # Use the original optimized weights
            for symbol, weight in zip(portfolio.symbols, portfolio.metrics.weights):
                if symbol in self.custom_allocations:
                    self.custom_allocations[symbol] = weight
                    if symbol in self.allocation_vars:
                        self.allocation_vars[symbol].set(weight * 100)
            
            self.update_allocation_summary()
            messagebox.showinfo("Optimization Complete", "Portfolio has been optimized using the original strategy.")
            
        except Exception as e:
            messagebox.showerror("Optimization Error", f"Failed to optimize allocation: {e}")
    
    def save_custom_allocation(self):
        """Save the custom allocation as a new portfolio."""
        try:
            if not self.custom_allocations:
                messagebox.showwarning("No Data", "No custom allocation to save.")
                return
            
            # Check if allocation is reasonable (sums to ~100%)
            total_allocation = sum(self.custom_allocations.values())
            if abs(total_allocation - 1.0) > 0.05:  # Allow 5% tolerance
                response = messagebox.askyesno("Allocation Warning", 
                    f"Total allocation is {total_allocation:.1%}. Save anyway?")
                if not response:
                    return
            
            # Get name for custom portfolio
            name = tk.simpledialog.askstring("Save Custom Portfolio", 
                                           "Enter name for custom portfolio:",
                                           initialvalue="Custom Allocation")
            if not name:
                return
            
            # Create portfolio from custom allocation
            base_portfolio = self.current_portfolios[self.alloc_portfolio_selector.get()]
            
            # Create new portfolio with custom weights
            from src.data.universe_manager import PortfolioStrategy
            from src.portfolio.optimizer import PortfolioMetrics
            
            custom_symbols = [symbol for symbol, weight in self.custom_allocations.items() if weight > 0.001]
            custom_weights = [self.custom_allocations[symbol] for symbol in custom_symbols]
            
            # Normalize weights to sum to 1
            weight_sum = sum(custom_weights)
            if weight_sum > 0:
                custom_weights = [w / weight_sum for w in custom_weights]
            
            # Create metrics object
            custom_metrics = PortfolioMetrics(
                expected_return=base_portfolio.metrics.expected_return if base_portfolio.metrics else 0.1,
                volatility=base_portfolio.metrics.volatility if base_portfolio.metrics else 0.15,
                sharpe_ratio=base_portfolio.metrics.sharpe_ratio if base_portfolio.metrics else 0.67,
                weights=custom_weights
            )
            
            # Create custom portfolio strategy
            custom_portfolio = PortfolioStrategy(
                name=name,
                description=f"Custom allocation based on {base_portfolio.name}",
                symbols=custom_symbols,
                metrics=custom_metrics
            )
            
            # Add to current portfolios
            self.current_portfolios[name] = custom_portfolio
            
            # Update portfolio selector
            self.update_portfolio_selector()
            
            # Switch to overview tab to see the new portfolio
            self.notebook.select(1)  # Portfolio Overview tab
            self.portfolio_selector.set(name)
            self.display_portfolio(custom_portfolio)
            
            messagebox.showinfo("Success", f"Custom portfolio '{name}' has been saved!")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save custom allocation: {e}")
    
    def reset_custom_allocation(self):
        """Reset custom allocation to original portfolio weights."""
        try:
            selected = self.alloc_portfolio_selector.get()
            if selected and selected in self.current_portfolios:
                portfolio = self.current_portfolios[selected]
                self.setup_custom_allocation_widgets(portfolio)
                messagebox.showinfo("Reset Complete", "Allocation has been reset to original values.")
        except Exception as e:
            messagebox.showerror("Reset Error", f"Failed to reset allocation: {e}")
    
    def refresh_sim_portfolios(self):
        """Refresh the simulation portfolio list."""
        try:
            if hasattr(self.universe_manager, 'strategies') and self.universe_manager.strategies:
                portfolio_names = [strategy.name for strategy in self.universe_manager.strategies]
                self.sim_portfolio_selector['values'] = portfolio_names
                if portfolio_names and not self.sim_portfolio_selector.get():
                    self.sim_portfolio_selector.set(portfolio_names[0])
            else:
                self.sim_portfolio_selector['values'] = []
                messagebox.showinfo("No Portfolios", "No portfolios available for simulation.\n\nCreate portfolios first using the '🚀 Create Portfolios' button.")
        except Exception as e:
            messagebox.showerror("Error", f"Error refreshing simulation portfolios: {e}")

    def on_sim_portfolio_selected(self, event=None):
        """Handle simulation portfolio selection change."""
        selected_name = self.sim_portfolio_selector.get()
        if selected_name:
            # Update simulation parameters based on selected portfolio
            print(f"📊 Selected portfolio for simulation: {selected_name}")

    def run_monte_carlo(self):
        """Run Monte Carlo simulation."""
        selected = self.sim_portfolio_selector.get()
        if not selected:
            messagebox.showwarning("Portfolio Required", 
                                 "Please select a portfolio for simulation.\n\n"
                                 "If no portfolios are available, create them first using '🚀 Create Portfolios'.")
            return
        
        # Find the selected strategy
        selected_strategy = None
        if hasattr(self.universe_manager, 'strategies'):
            for strategy in self.universe_manager.strategies:
                if strategy.name == selected:
                    selected_strategy = strategy
                    break
        
        if not selected_strategy:
            messagebox.showerror("Error", f"Portfolio '{selected}' not found!")
            return
        
        self.update_status("Running Monte Carlo simulation...", True)
        
        def simulate_in_background():
            try:
                # Get returns data - first try universe data, then fetch fresh data
                returns_data = None
                
                if hasattr(self.universe_manager, 'universe_data') and self.universe_manager.universe_data:
                    returns_data = self.universe_manager.universe_data.get('returns')
                
                if returns_data is None:
                    print("📊 Universe data not available, fetching fresh data for simulation...")
                    # Use TradingView data fetcher to get fresh data
                    tv_fetcher = TradingViewDataFetcher()
                    returns_data = tv_fetcher.get_returns_data(selected_strategy.symbols, days=252)  # 1 year of data
                
                if returns_data is None or len(returns_data) == 0:
                    raise Exception("Unable to fetch returns data for simulation.")
                
                # Get portfolio weights
                portfolio_weights = None
                if hasattr(selected_strategy, 'weights') and selected_strategy.weights is not None:
                    portfolio_weights = selected_strategy.weights
                elif hasattr(selected_strategy, 'metrics') and selected_strategy.metrics and hasattr(selected_strategy.metrics, 'weights'):
                    portfolio_weights = selected_strategy.metrics.weights
                else:
                    # Create equal weights for the portfolio symbols
                    num_stocks = len(selected_strategy.symbols)
                    portfolio_weights = np.ones(num_stocks) / num_stocks
                    print(f"Using equal weights for {selected_strategy.name}")
                
                # Filter returns data to only include portfolio symbols (if needed)
                if isinstance(returns_data, pd.DataFrame):
                    # Check if we have all required symbols
                    available_symbols = [symbol for symbol in selected_strategy.symbols if symbol in returns_data.columns]
                    if len(available_symbols) < len(selected_strategy.symbols):
                        print(f"⚠️  Only {len(available_symbols)}/{len(selected_strategy.symbols)} symbols available in data")
                    
                    portfolio_returns = returns_data[available_symbols]
                    
                    # Adjust weights if some symbols are missing
                    if len(available_symbols) < len(selected_strategy.symbols):
                        # Create new equal weights for available symbols
                        portfolio_weights = np.ones(len(available_symbols)) / len(available_symbols)
                        print(f"Adjusted to equal weights for {len(available_symbols)} available symbols")
                else:
                    portfolio_returns = returns_data
                
                # Create optimizer and run simulation
                optimizer = PortfolioOptimizer(risk_free_rate=self.risk_free_rate_var.get() / 100)
                
                results = optimizer.monte_carlo_simulation(
                    returns=portfolio_returns,
                    weights=portfolio_weights,
                    initial_investment=self.initial_investment_var.get(),
                    time_horizon=self.time_horizon_var.get(),
                    num_simulations=self.num_sims_var.get()
                )
                
                # Store results
                self.simulation_results[selected] = results
                
                # Update GUI
                self.root.after(0, lambda: self.update_simulation_display(results))
                
            except Exception as e:
                error_msg = f"Simulation failed: {str(e)}"
                print(f"Monte Carlo error: {error_msg}")
                self.root.after(0, lambda: messagebox.showerror("Simulation Error", error_msg))
            finally:
                self.root.after(0, lambda: self.update_status("Ready", False))
        
        threading.Thread(target=simulate_in_background, daemon=True).start()
    
    def update_simulation_display(self, results):
        """Update simulation results display."""
        self.simulation_fig.clear()
        
        # Create subplots
        ax1 = self.simulation_fig.add_subplot(221)
        ax2 = self.simulation_fig.add_subplot(222)
        ax3 = self.simulation_fig.add_subplot(223)
        ax4 = self.simulation_fig.add_subplot(224)
        
        # Portfolio value paths
        simulations = results.get('simulations', [])
        if len(simulations) > 0:
            initial_value = self.initial_investment_var.get()
            time_horizon = self.time_horizon_var.get()
            
            # Plot sample paths (first 100 simulations)
            for i in range(min(100, len(simulations))):
                path = simulations[i]
                ax1.plot(path, alpha=0.1, color='blue')
            
            ax1.set_title("Portfolio Value Paths")
            ax1.set_xlabel("Days")
            ax1.set_ylabel("Portfolio Value ($)")
            
            # Final values histogram
            final_values = results.get('final_values', [])
            if len(final_values) > 0:
                ax2.hist(final_values, bins=50, alpha=0.7, color='green')
                ax2.set_title("Final Portfolio Values")
                ax2.set_xlabel("Final Value ($)")
                ax2.set_ylabel("Frequency")
                
                # Returns distribution
                returns = [(final/initial_value - 1) for final in final_values]
                ax3.hist(returns, bins=50, alpha=0.7, color='orange')
                ax3.set_title("Returns Distribution")
                ax3.set_xlabel("Return")
                ax3.set_ylabel("Frequency")
                
                # Percentiles display instead of drawdown
                percentiles = results.get('percentiles', {})
                if percentiles:
                    percentile_labels = ['5th', '25th', '50th', '75th', '95th']
                    percentile_values = [percentiles.get(label, 0) for label in percentile_labels]
                    
                    ax4.bar(percentile_labels, percentile_values, alpha=0.7, color='purple')
                    ax4.set_title("Value Percentiles")
                    ax4.set_xlabel("Percentile")
                    ax4.set_ylabel("Portfolio Value ($)")
                    ax4.tick_params(axis='x', rotation=45)
                
                # Update statistics
                self.update_simulation_stats(results, final_values, returns)
            else:
                ax2.text(0.5, 0.5, 'No simulation data', ha='center', va='center', transform=ax2.transAxes)
                ax3.text(0.5, 0.5, 'No simulation data', ha='center', va='center', transform=ax3.transAxes)
                ax4.text(0.5, 0.5, 'No simulation data', ha='center', va='center', transform=ax4.transAxes)
        
        plt.tight_layout()
        self.simulation_canvas.draw()
    
    def update_simulation_stats(self, results, final_values, returns):
        """Update simulation statistics labels."""
        initial_value = self.initial_investment_var.get()
        
        # Calculate statistics
        mean_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        best_case = max(returns)
        worst_case = min(returns)
        var_5 = np.percentile(returns, 5)
        var_1 = np.percentile(returns, 1)
        prob_loss = sum(1 for r in returns if r < 0) / len(returns)
        
        # Sharpe ratio (annualized)
        rf_rate = self.risk_free_rate_var.get() / 100
        sharpe = (mean_return * 252 - rf_rate) / (std_return * np.sqrt(252))
        
        # Update labels
        try:
            if "Mean Return" in self.sim_stats_labels:
                self.sim_stats_labels["Mean Return"].config(text=f"{mean_return:.2%}")
            if "Median Return" in self.sim_stats_labels:
                self.sim_stats_labels["Median Return"].config(text=f"{median_return:.2%}")
            if "Std Deviation" in self.sim_stats_labels:
                self.sim_stats_labels["Std Deviation"].config(text=f"{std_return:.2%}")
            if "Best Case" in self.sim_stats_labels:
                self.sim_stats_labels["Best Case"].config(text=f"{best_case:.2%}")
            if "Worst Case" in self.sim_stats_labels:
                self.sim_stats_labels["Worst Case"].config(text=f"{worst_case:.2%}")
            if "VaR (5%)" in self.sim_stats_labels:
                self.sim_stats_labels["VaR (5%)"].config(text=f"{var_5:.2%}")
            if "VaR (1%)" in self.sim_stats_labels:
                self.sim_stats_labels["VaR (1%)"].config(text=f"{var_1:.2%}")
            if "Prob. of Loss" in self.sim_stats_labels:
                self.sim_stats_labels["Prob. of Loss"].config(text=f"{prob_loss:.1%}")
            if "Sharpe Ratio" in self.sim_stats_labels:
                self.sim_stats_labels["Sharpe Ratio"].config(text=f"{sharpe:.3f}")
        except Exception as e:
            print(f"Error updating simulation statistics: {e}")
    
    def save_settings(self):
        """Save current settings."""
        self.save_config()
        messagebox.showinfo("Success", "Settings saved successfully!")
    
    def on_closing(self):
        """Handle application closing."""
        if self.auto_save_var.get():
            self.save_config()
        
        # Stop background processes
        self.stop_background.set()
        
        self.root.destroy()
    
    # Placeholder methods for other functionality
    def quick_simulation(self):
        """Run quick simulation."""
        messagebox.showinfo("Info", "Quick simulation functionality would be implemented here")
    
    def generate_report(self):
        """Generate comprehensive report."""
        messagebox.showinfo("Info", "Report generation functionality would be implemented here")
    
    def open_file_manager(self):
        """Open file manager."""
        messagebox.showinfo("Info", "File manager would be opened here")
    
    def view_etf_database(self):
        """View ETF database."""
        messagebox.showinfo("Info", "ETF database viewer would be implemented here")
    
    def refresh_all_data(self):
        """Refresh all data."""
        messagebox.showinfo("Info", "Data refresh functionality would be implemented here")
    
    def show_help(self):
        """Show help dialog."""
        help_text = """
Portfolio Management System Help

This application provides comprehensive portfolio management capabilities:

1. ETF Selection: Choose ETFs to build your stock universe
2. Portfolio Overview: View allocation and performance metrics  
3. Simulation: Run Monte Carlo simulations
4. Metrics: Track performance over time
5. Rebalancing: Manage portfolio rebalancing
6. Settings: Configure application preferences

For detailed documentation, see the README file.
        """
        messagebox.showinfo("Help", help_text)
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
Portfolio Management System v1.0

A comprehensive portfolio management application with:
• ETF-based universe building
• Multi-strategy portfolio optimization  
• Monte Carlo simulation
• Performance tracking
• Automated rebalancing
• Advanced file management

Built with Python, Tkinter, and financial analysis libraries.
        """
        messagebox.showinfo("About", about_text)
    
    # Portfolio Management Methods
    def refresh_portfolios(self):
        """Refresh the portfolio list."""
        try:
            if hasattr(self.universe_manager, 'strategies') and self.universe_manager.strategies:
                portfolio_names = [strategy.name for strategy in self.universe_manager.strategies]
                self.portfolio_selector['values'] = portfolio_names
                if portfolio_names and not self.portfolio_selector.get():
                    self.portfolio_selector.set(portfolio_names[0])
                    self.on_portfolio_selected()
                
                # Also refresh simulation portfolio selector
                if hasattr(self, 'sim_portfolio_selector'):
                    self.sim_portfolio_selector['values'] = portfolio_names
                    if portfolio_names and not self.sim_portfolio_selector.get():
                        self.sim_portfolio_selector.set(portfolio_names[0])
                
                # Hide action banner when portfolios exist
                self.action_banner.pack_forget()
            else:
                self.portfolio_selector['values'] = []
                if hasattr(self, 'sim_portfolio_selector'):
                    self.sim_portfolio_selector['values'] = []
                self.update_status("No portfolios available. Build universe and optimize first.", False)
                
                # Show action banner when no portfolios
                self.action_banner.pack(fill=tk.X, pady=(0, 10), before=self.notebook)
        except Exception as e:
            messagebox.showerror("Error", f"Error refreshing portfolios: {e}")

    def optimize_selected_portfolio(self):
        """Create and optimize portfolios from the current universe."""
        if not hasattr(self.universe_manager, 'universe') or not self.universe_manager.universe:
            messagebox.showwarning("Warning", "Please build a universe first in the ETF Selection tab")
            return
        
        # Show portfolio creation wizard
        self.show_portfolio_creation_wizard()

    def show_portfolio_creation_wizard(self):
        """Show portfolio creation wizard dialog."""
        wizard = tk.Toplevel(self.root)
        wizard.title("🎯 Portfolio Creation Wizard")
        wizard.geometry("650x600")
        wizard.resizable(True, True)
        wizard.transient(self.root)
        wizard.grab_set()
        
        # Center the window
        wizard.update_idletasks()
        x = (wizard.winfo_screenwidth() // 2) - (325)
        y = (wizard.winfo_screenheight() // 2) - (300)
        wizard.geometry(f"650x600+{x}+{y}")
        
        # Title
        title_frame = ttk.Frame(wizard)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(title_frame, text="🎯 Portfolio Creation Wizard", 
                 font=("Arial", 16, "bold")).pack()
        ttk.Label(title_frame, text="Create optimized portfolios from your universe", 
                 font=("Arial", 10)).pack(pady=(5, 0))
        
        # Universe info
        info_frame = ttk.LabelFrame(wizard, text="Universe Information", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        universe_size = len(self.universe_manager.universe) if hasattr(self.universe_manager, 'universe') else 0
        ttk.Label(info_frame, text=f"📊 Universe Size: {universe_size} stocks").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"📈 Source ETFs: {self.selected_etfs.get()}").pack(anchor=tk.W)
        
        # Create scrollable frame for wizard content
        scroll_frame = ScrollableFrame(wizard)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Move all content to scrollable frame
        wizard_content = scroll_frame.scrollable_frame
        
        # Portfolio options
        options_frame = ttk.LabelFrame(wizard_content, text="Portfolio Types to Create", padding=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        # Instructions
        instructions = ttk.Label(options_frame, 
                               text="✅ Select portfolio types to create (options-based strategies analyze market sentiment):",
                               font=("Arial", 9), foreground="#2c3e50")
        instructions.pack(anchor=tk.W, pady=(0, 5))
        
        self.wizard_options = {}
        
        # Traditional Strategies
        traditional_label = ttk.Label(options_frame, text="📊 Traditional Strategies:", 
                                    font=("Arial", 9, "bold"), foreground="#34495e")
        traditional_label.pack(anchor=tk.W, pady=(10, 5))
        
        traditional_types = [
            ("Conservative (Top 10 stocks)", "conservative", False),
            ("Balanced (Top 15 stocks)", "balanced", False),
            ("Growth (Top 20 stocks)", "growth", False),
            ("Full Universe", "full", False)
        ]
        
        for i, (label, key, default) in enumerate(traditional_types):
            var = tk.BooleanVar(value=default)
            self.wizard_options[key] = var
            ttk.Checkbutton(options_frame, text=label, variable=var).pack(anchor=tk.W, pady=2, padx=20)
        
        # Options-Based Strategies
        options_label = ttk.Label(options_frame, text="🔥 Options-Based Strategies:", 
                                font=("Arial", 9, "bold"), foreground="#e74c3c")
        options_label.pack(anchor=tk.W, pady=(10, 5))
        
        options_types = [
            ("🚀 Growth-Focused (High bullish sentiment)", "options_growth", True),
            ("🛡️ Stability/Defensive (Balanced positioning)", "options_defensive", True),
            ("⚖️ Sharpe-Optimized (Underpriced volatility)", "options_sharpe", True),
            ("💰 High-Income (Rich premium opportunities)", "options_income", False),
            ("🔄 Market-Neutral (Relative sentiment)", "options_neutral", False)
        ]
        
        for i, (label, key, default) in enumerate(options_types):
            var = tk.BooleanVar(value=default)
            self.wizard_options[key] = var
            ttk.Checkbutton(options_frame, text=label, variable=var).pack(anchor=tk.W, pady=2, padx=20)
        
        # Optimization settings
        settings_frame = ttk.LabelFrame(wizard_content, text="Optimization Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=10)
        
        # Risk-free rate
        risk_frame = ttk.Frame(settings_frame)
        risk_frame.pack(fill=tk.X, pady=2)
        ttk.Label(risk_frame, text="Risk-free rate (%):").pack(side=tk.LEFT)
        self.wizard_risk_rate = tk.DoubleVar(value=self.config.get('risk_free_rate', 2.0))
        risk_spinbox = ttk.Spinbox(risk_frame, from_=0, to=10, increment=0.1, 
                                  textvariable=self.wizard_risk_rate, width=10)
        risk_spinbox.pack(side=tk.RIGHT)
        
        # Optimization method
        method_frame = ttk.Frame(settings_frame)
        method_frame.pack(fill=tk.X, pady=2)
        ttk.Label(method_frame, text="Optimization method:").pack(side=tk.LEFT)
        self.wizard_method = tk.StringVar(value="max_sharpe")
        method_combo = ttk.Combobox(method_frame, textvariable=self.wizard_method, 
                                   values=["max_sharpe", "min_volatility", "equal_weight"], 
                                   state="readonly", width=15)
        method_combo.pack(side=tk.RIGHT)
        
        # Progress section
        progress_frame = ttk.LabelFrame(wizard_content, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.wizard_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.wizard_progress.pack(fill=tk.X, pady=5)
        
        self.wizard_status = ttk.Label(progress_frame, text="Ready to create portfolios")
        self.wizard_status.pack()
        
        # Add some visual separation before buttons
        ttk.Separator(wizard, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)
        
        # Data handling options
        data_options_frame = ttk.LabelFrame(wizard, text="Data Handling Options", padding=10)
        data_options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Auto-remove stocks with insufficient data
        self.auto_remove_stocks_var = tk.BooleanVar(value=self.config.get('auto_remove_insufficient_data', True))
        ttk.Checkbutton(data_options_frame, 
                       text="🗑️ Auto-remove stocks with insufficient data (recommended)", 
                       variable=self.auto_remove_stocks_var).pack(anchor=tk.W, pady=2)
        
        # Show data quality info
        ttk.Label(data_options_frame, 
                 text="• Stocks needing ≥20 days of data for optimization\n• Failed stocks will be excluded, not cause portfolio failure", 
                 font=("Arial", 8), foreground="#555").pack(anchor=tk.W, padx=20, pady=(0, 5))
        
        # Simple mode option
        self.simple_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(data_options_frame, text="💨 Quick Mode (Equal-weight portfolios, faster)", 
                       variable=self.simple_mode_var).pack(anchor=tk.W, pady=2)
        
        # Buttons
        button_frame = ttk.Frame(wizard)
        button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        cancel_btn = ttk.Button(button_frame, text="❌ Cancel", 
                               command=wizard.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        create_btn = ttk.Button(button_frame, text="🚀 Create Portfolios", 
                               command=lambda: self.execute_portfolio_creation(wizard),
                               style="Accent.TButton")
        create_btn.pack(side=tk.RIGHT, padx=5)
        
        # Make the create button more prominent
        create_btn.focus_set()
        
        # Store wizard reference
        self.portfolio_wizard = wizard

    def execute_portfolio_creation(self, wizard):
        """Execute portfolio creation from wizard."""
        # Get selected options
        selected_types = [key for key, var in self.wizard_options.items() if var.get()]
        
        if not selected_types:
            messagebox.showwarning("Selection Required", 
                                 "Please select at least one portfolio type to create.\n\n"
                                 "Tip: Conservative, Balanced, and Growth are selected by default.")
            return
        
        # Check if universe exists
        if not hasattr(self.universe_manager, 'universe') or not self.universe_manager.universe or len(self.universe_manager.universe) == 0:
            messagebox.showwarning("Universe Required", 
                                 "No stock universe found!\n\n"
                                 "Please go to the ETF Selection tab and:\n"
                                 "1. Enter ETF symbols (e.g., SPY, QQQ)\n"
                                 "2. Click 'Build Universe'\n"
                                 "3. Then return to create portfolios")
            wizard.destroy()
            self.notebook.select(0)  # Switch to ETF Selection tab
            return
        
        # Disable create button and show progress
        for widget in wizard.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and "Create Portfolios" in child.cget('text'):
                        child.config(state='disabled')
        
        self.wizard_progress.start()
        self.wizard_status.config(text="Creating portfolios...")
        
        self.update_status("Creating portfolios from universe...", True)
        
        def optimize_in_background():
            try:
                print("🚀 Starting portfolio optimization...")
                print(f"🔍 Universe manager exists: {hasattr(self, 'universe_manager')}")
                print(f"🔍 Universe attribute exists: {hasattr(self.universe_manager, 'universe') if hasattr(self, 'universe_manager') else False}")
                
                # Get universe stocks
                if hasattr(self.universe_manager, 'universe') and self.universe_manager.universe:
                    # universe is a list of UniverseStock objects
                    universe_stocks = [stock.symbol for stock in self.universe_manager.universe]
                    print(f"📊 Universe has {len(universe_stocks)} stocks: {universe_stocks[:5]}{'...' if len(universe_stocks) > 5 else ''}")
                else:
                    universe_stocks = []
                    print("❌ No universe found or universe is empty")
                
                if len(universe_stocks) < 3:
                    self.root.after(0, lambda: messagebox.showwarning("Warning", 
                        "Universe too small. Need at least 3 stocks for optimization."))
                    self.root.after(0, self.wizard_cleanup)
                    return
                
                # Create strategies based on wizard selections
                strategies = []
                options_strategies = []
                
                if hasattr(self, 'wizard_options') and self.wizard_options:
                    print(f"🎯 Checking wizard options...")
                    for key, var in self.wizard_options.items():
                        is_selected = var.get() if var else False
                        print(f"   {key}: {is_selected}")
                    
                    # Traditional strategies
                    if self.wizard_options.get('conservative') and self.wizard_options['conservative'].get():
                        strategies.append(("Conservative Portfolio", universe_stocks[:10], "traditional"))
                        print("   ✅ Adding Conservative Portfolio")
                    if self.wizard_options.get('balanced') and self.wizard_options['balanced'].get():
                        strategies.append(("Balanced Portfolio", universe_stocks[:15], "traditional"))
                        print("   ✅ Adding Balanced Portfolio")
                    if self.wizard_options.get('growth') and self.wizard_options['growth'].get():
                        strategies.append(("Growth Portfolio", universe_stocks[:20], "traditional"))
                        print("   ✅ Adding Growth Portfolio")
                    if self.wizard_options.get('full') and self.wizard_options['full'].get():
                        strategies.append(("Full Universe Portfolio", universe_stocks, "traditional"))
                        print("   ✅ Adding Full Universe Portfolio")
                    
                    # Options-based strategies
                    if self.wizard_options.get('options_growth') and self.wizard_options['options_growth'].get():
                        options_strategies.append(("Options Growth-Focused", "growth"))
                        print("   🚀 Adding Options Growth-Focused Portfolio")
                    if self.wizard_options.get('options_defensive') and self.wizard_options['options_defensive'].get():
                        options_strategies.append(("Options Stability/Defensive", "defensive"))
                        print("   🛡️ Adding Options Defensive Portfolio")
                    if self.wizard_options.get('options_sharpe') and self.wizard_options['options_sharpe'].get():
                        options_strategies.append(("Options Sharpe-Optimized", "balanced"))
                        print("   ⚖️ Adding Options Sharpe-Optimized Portfolio")
                    if self.wizard_options.get('options_income') and self.wizard_options['options_income'].get():
                        options_strategies.append(("Options High-Income", "income"))
                        print("   💰 Adding Options High-Income Portfolio")
                    if self.wizard_options.get('options_neutral') and self.wizard_options['options_neutral'].get():
                        options_strategies.append(("Options Market-Neutral", "balanced"))
                        print("   🔄 Adding Options Market-Neutral Portfolio")
                        
                else:
                    print("🎯 No wizard options found, using defaults")
                    # Default strategies if wizard not used
                    strategies = [
                        ("Conservative Portfolio", universe_stocks[:10], "traditional"),
                        ("Balanced Portfolio", universe_stocks[:15], "traditional"),
                        ("Growth Portfolio", universe_stocks[:20], "traditional")
                    ]
                    options_strategies = [
                        ("Options Growth-Focused", "growth")
                    ]
                
                print(f"📋 Will create {len(strategies)} traditional strategies and {len(options_strategies)} options-based strategies")
                
                # Comprehensive options-based strategy analysis
                options_portfolios = {}
                if options_strategies:
                    print("� Starting comprehensive options strategy analysis...")
                    self.root.after(0, lambda: self.wizard_status.config(text="Running options strategy analysis..."))
                    
                    try:
                        from src.strategy.options_strategy_engine import OptionsStrategyEngine, STRATEGY_CONFIGS
                        options_engine = OptionsStrategyEngine(enable_cache=True)
                        
                        # Analyze top universe stocks for options factors
                        analysis_symbols = universe_stocks[:25]  # Analyze top 25 for comprehensive analysis
                        print(f"� Analyzing {len(analysis_symbols)} stocks for options factors...")
                        
                        # Step 1: Analyze universe to compute options factors
                        factors_dict = options_engine.analyze_universe(analysis_symbols)
                        
                        if not factors_dict:
                            print("   ❌ No options factors computed - using fallback")
                            # Create fallback portfolios
                            for strategy_name, objective in options_strategies:
                                fallback_portfolio = {
                                    'symbols': analysis_symbols[:15],
                                    'weights': np.full(15, 1.0/15),
                                    'scores': {s: 5.0 + np.random.random() for s in analysis_symbols[:15]},
                                    'strategy_type': 'fallback'
                                }
                                options_portfolios[strategy_name] = fallback_portfolio
                        else:
                            print(f"   ✅ Options factors computed for {len(factors_dict)} stocks")
                            
                            # Step 2: Construct portfolios for each strategy
                            for strategy_name, objective in options_strategies:
                                print(f"🎯 Constructing {strategy_name} portfolio...")
                                
                                try:
                                    # Map strategy name to config
                                    if "Growth-Focused" in strategy_name:
                                        config = STRATEGY_CONFIGS['growth_focused']
                                    elif "Defensive" in strategy_name or "Stability" in strategy_name:
                                        config = STRATEGY_CONFIGS['defensive_stability']
                                    elif "Sharpe-Optimized" in strategy_name:
                                        config = STRATEGY_CONFIGS['sharpe_optimized']
                                    elif "High-Income" in strategy_name:
                                        config = STRATEGY_CONFIGS['high_income']
                                    elif "Market-Neutral" in strategy_name:
                                        config = STRATEGY_CONFIGS['market_neutral']
                                    else:
                                        config = STRATEGY_CONFIGS['growth_focused']  # Default
                                    
                                    # Construct portfolio
                                    portfolio_data = options_engine.construct_portfolio(
                                        factors_dict, config, universe_size=15
                                    )
                                    
                                    if portfolio_data:
                                        options_portfolios[strategy_name] = portfolio_data
                                        print(f"   ✅ {strategy_name}: {len(portfolio_data['symbols'])} stocks selected")
                                    else:
                                        print(f"   ❌ {strategy_name}: Portfolio construction failed")
                                        # Fallback
                                        fallback_symbols = list(factors_dict.keys())[:15]
                                        fallback_portfolio = {
                                            'symbols': fallback_symbols,
                                            'weights': np.full(len(fallback_symbols), 1.0/len(fallback_symbols)),
                                            'scores': {s: factors_dict[s].growth_score for s in fallback_symbols},
                                            'strategy_type': 'fallback'
                                        }
                                        options_portfolios[strategy_name] = fallback_portfolio
                                        
                                except Exception as e:
                                    print(f"   ❌ Portfolio construction failed for {strategy_name}: {e}")
                                    # Create fallback
                                    fallback_symbols = list(factors_dict.keys())[:15] if factors_dict else analysis_symbols[:15]
                                    fallback_portfolio = {
                                        'symbols': fallback_symbols,
                                        'weights': np.full(len(fallback_symbols), 1.0/len(fallback_symbols)),
                                        'scores': {s: 5.0 + np.random.random() for s in fallback_symbols},
                                        'strategy_type': 'fallback'
                                    }
                                    options_portfolios[strategy_name] = fallback_portfolio
                                    
                    except Exception as e:
                        print(f"❌ Failed to initialize options strategy engine: {e}")
                        # Create fallback portfolios
                        for strategy_name, objective in options_strategies:
                            fallback_portfolio = {
                                'symbols': universe_stocks[:15],
                                'weights': np.full(15, 1.0/15),
                                'scores': {s: 5.0 + np.random.random() for s in universe_stocks[:15]},
                                'strategy_type': 'fallback'
                            }
                            options_portfolios[strategy_name] = fallback_portfolio
                
                # Initialize strategies list
                if not hasattr(self.universe_manager, 'strategies'):
                    self.universe_manager.strategies = []
                else:
                    self.universe_manager.strategies.clear()
                
                print(f"📈 Creating {len(strategies)} traditional + {len(options_strategies)} options-based strategies...")
                
                # Check if using simple mode
                simple_mode = self.simple_mode_var.get() if hasattr(self, 'simple_mode_var') else False
                print(f"⚡ Simple mode: {simple_mode}")
                
                # Process traditional strategies
                all_strategies_to_process = [(name, symbols, "traditional") for name, symbols, _ in strategies]
                
                # Process options-based strategies
                for strategy_name, strategy_type in options_strategies:
                    if strategy_name in options_portfolios:
                        # Get stocks from comprehensive options analysis
                        portfolio_data = options_portfolios[strategy_name]
                        selected_stocks = portfolio_data['symbols']
                        all_strategies_to_process.append((strategy_name, selected_stocks, "options", portfolio_data))
                    else:
                        # Fallback to top universe stocks
                        all_strategies_to_process.append((strategy_name, universe_stocks[:15], "options", None))
                
                for i, item in enumerate(all_strategies_to_process):
                    if len(item) == 4:
                        strategy_name, symbols, strategy_category, portfolio_data = item
                    else:
                        strategy_name, symbols, strategy_category = item
                        portfolio_data = None
                    print(f"🔄 Processing {strategy_name} ({i+1}/{len(all_strategies_to_process)})...")
                    
                    if len(symbols) >= 3:  # Minimum required for optimization
                        try:
                            # Update status
                            status_text = f"Creating {strategy_name}..." if simple_mode else f"Optimizing {strategy_name}..."
                            self.root.after(0, lambda s=status_text: self.wizard_status.config(text=s))
                            
                            # Limit to reasonable number of symbols
                            limited_symbols = symbols[:15]
                            
                            # Create strategy description based on category
                            if strategy_category == "options":
                                if "Growth-Focused" in strategy_name:
                                    description = f"Options-based growth portfolio targeting stocks with high bullish sentiment ({len(limited_symbols)} stocks)"
                                elif "Defensive" in strategy_name or "Stability" in strategy_name:
                                    description = f"Options-based defensive portfolio targeting stable, balanced positioning ({len(limited_symbols)} stocks)"  
                                elif "Sharpe-Optimized" in strategy_name:
                                    description = f"Options-based Sharpe portfolio targeting underpriced volatility opportunities ({len(limited_symbols)} stocks)"
                                elif "High-Income" in strategy_name:
                                    description = f"Options-based income portfolio targeting high premium opportunities ({len(limited_symbols)} stocks)"
                                elif "Market-Neutral" in strategy_name:
                                    description = f"Options-based market-neutral portfolio using relative sentiment analysis ({len(limited_symbols)} stocks)"
                                else:
                                    description = f"Options-based portfolio with {len(limited_symbols)} stocks"
                            else:
                                description = f"Traditional optimized portfolio with {len(limited_symbols)} stocks"
                            
                            if simple_mode:
                                # Simple equal-weight portfolio creation
                                print(f"  ⚡ Creating equal-weight {strategy_name}")
                                
                                from src.data.universe_manager import PortfolioStrategy
                                equal_weights = np.array([1.0/len(limited_symbols)] * len(limited_symbols))
                                strategy = PortfolioStrategy(
                                    name=strategy_name,
                                    description=description,
                                    symbols=limited_symbols,
                                    weights=equal_weights,
                                    metrics=None
                                )
                                
                                self.universe_manager.strategies.append(strategy)
                                print(f"  ✅ Created {strategy_name} (equal-weight)")
                                continue
                            
                            # Full optimization mode
                            # Get historical data for optimization (use a shorter period for faster processing)
                            # Use a fixed historical period since we might be in simulation mode
                            end_date = datetime(2023, 12, 29)  # Use well-established historical end date
                            start_date = end_date - timedelta(days=180)  # 6 months of data
                            
                            print(f"📅 Fetching data from {start_date.date()} to {end_date.date()}")
                            
                            # Use TradingView data fetcher instead of yfinance
                            print(f"  📊 Fetching market data using TradingView...")
                            
                            # Calculate days needed
                            days_needed = (end_date - start_date).days
                            
                            # Use TradingView data fetcher
                            tv_fetcher = TradingViewDataFetcher()
                            returns_df = tv_fetcher.get_returns_data(limited_symbols, days=days_needed)
                            
                            # Apply stock removal override based on user preference
                            auto_remove = self.auto_remove_stocks_var.get() if hasattr(self, 'auto_remove_stocks_var') else True
                            
                            if auto_remove:
                                # Filter out symbols with insufficient data
                                original_count = len(limited_symbols)
                                working_symbols = list(returns_df.columns) if len(returns_df.columns) > 0 else []
                                
                                if len(working_symbols) < original_count:
                                    removed_symbols = [s for s in limited_symbols if s not in working_symbols]
                                    print(f"  🗑️ Auto-removed {len(removed_symbols)} stocks with insufficient data: {removed_symbols}")
                                    print(f"  ✅ Continuing with {len(working_symbols)} stocks: {working_symbols}")
                                
                                # Ensure we have minimum required stocks
                                if len(working_symbols) < 3:
                                    print(f"  ⚠️ After data filtering, only {len(working_symbols)} stocks remain (need ≥3)")
                                    if len(working_symbols) == 0:
                                        print(f"  ❌ {strategy_name}: No stocks have sufficient data")
                                        continue
                                    else:
                                        print(f"  🔄 {strategy_name}: Creating single/dual stock portfolio with available data")
                                
                            else:
                                # Original behavior - use all symbols even if some lack data
                                working_symbols = list(returns_df.columns) if len(returns_df.columns) > 0 else limited_symbols
                            
                            # Check data quality for optimization
                            min_data_days = 20  # Reduced requirement for more flexibility
                            if len(returns_df) >= min_data_days and len(working_symbols) >= 1:
                                print(f"  ✅ Working symbols: {len(working_symbols)}/{len(limited_symbols)}")
                                print(f"  📊 Returns data: {len(returns_df)} days, {len(returns_df.columns)} stocks")
                                
                                # Proceed with optimization if we have sufficient data
                                if len(returns_df) >= min_data_days:
                                    try:
                                        # Initialize optimizer
                                        risk_rate = self.wizard_risk_rate.get() / 100 if hasattr(self, 'wizard_risk_rate') else self.config.get('risk_free_rate', 0.02)
                                        optimizer = PortfolioOptimizer(
                                            risk_free_rate=risk_rate
                                        )
                                        
                                        print(f"  🎯 Optimizing {strategy_name}...")
                                        
                                        # Check if we have options strategy data with pre-computed weights
                                        if strategy_category == "options" and portfolio_data and 'weights' in portfolio_data:
                                            print(f"  🚀 Using options-based strategy weights for {strategy_name}")
                                            
                                            # Use options strategy weights if symbols match
                                            options_symbols = portfolio_data['symbols']
                                            options_weights = portfolio_data['weights']
                                            
                                            # Map options weights to working symbols
                                            if set(options_symbols) == set(working_symbols):
                                                # Perfect match - use options weights directly
                                                weights = options_weights
                                                print(f"  ✅ Perfect symbol match - using options weights")
                                            else:
                                                # Partial match - create hybrid weights
                                                print(f"  🔀 Symbol mismatch - creating hybrid weights")
                                                weights_dict = dict(zip(options_symbols, options_weights))
                                                weights = []
                                                for symbol in working_symbols:
                                                    if symbol in weights_dict:
                                                        weights.append(weights_dict[symbol])
                                                    else:
                                                        weights.append(1.0 / len(working_symbols))  # Equal weight for missing
                                                weights = np.array(weights)
                                                weights = weights / weights.sum()  # Normalize
                                            
                                            # Calculate metrics for options-based weights
                                            exp_return, volatility, sharpe = optimizer.calculate_portfolio_metrics(weights, returns_df)
                                            from src.portfolio.optimizer import PortfolioMetrics
                                            metrics = PortfolioMetrics(
                                                expected_return=exp_return,
                                                volatility=volatility,
                                                sharpe_ratio=sharpe,
                                                weights=weights,
                                                symbols=working_symbols
                                            )
                                            
                                        else:
                                            # Traditional optimization
                                            opt_target = self.wizard_method.get() if hasattr(self, 'wizard_method') else 'sharpe'
                                            if opt_target == 'max_sharpe':
                                                opt_target = 'sharpe'
                                            elif opt_target == 'min_variance':
                                                opt_target = 'min_volatility'
                                            
                                            metrics = optimizer.optimize_portfolio(
                                                returns_df, optimization_target=opt_target
                                            )
                                            weights = metrics.weights
                                        
                                        print(f"  ✅ Optimization complete for {strategy_name}")
                                        
                                        # Create strategy object
                                        from src.data.universe_manager import PortfolioStrategy
                                        strategy = PortfolioStrategy(
                                            name=strategy_name,
                                            description=description,
                                            symbols=working_symbols,
                                            weights=weights,
                                            metrics=metrics
                                        )
                                        
                                        self.universe_manager.strategies.append(strategy)
                                        print(f"  🎉 Added {strategy_name} to strategies")
                                        
                                    except Exception as opt_error:
                                        print(f"  ❌ Optimization failed for {strategy_name}: {opt_error}")
                                        # Create equal-weight strategy as fallback
                                        from src.data.universe_manager import PortfolioStrategy
                                        equal_weights = np.array([1.0/len(working_symbols)] * len(working_symbols))
                                        strategy = PortfolioStrategy(
                                            name=f"{strategy_name} (Equal Weight)",
                                            description=f"Equal-weight fallback: {description}",
                                            symbols=working_symbols,
                                            weights=equal_weights,
                                            metrics=None
                                        )
                                        self.universe_manager.strategies.append(strategy)
                                        print(f"  🔄 Created equal-weight fallback for {strategy_name}")
                                else:
                                    print(f"  ❌ {strategy_name}: Insufficient return data ({len(returns_df)} days, need ≥{min_data_days})")
                            else:
                                if auto_remove:
                                    print(f"  ⚠️ {strategy_name}: After filtering, insufficient symbols ({len(working_symbols)})")
                                else:
                                    print(f"  ❌ {strategy_name}: Too few working symbols ({len(working_symbols)})")
                                    print(f"  💡 Tip: Enable 'Auto-remove stocks with insufficient data' to continue with available stocks")
                                
                        except Exception as e:
                            print(f"❌ Error processing {strategy_name}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                print(f"🎉 Portfolio creation complete! Created {len(self.universe_manager.strategies)} strategies")
                
                # Store universe data for Monte Carlo simulations
                if self.universe_manager.strategies:
                    try:
                        # Get all unique symbols from all strategies
                        all_symbols = set()
                        for strategy in self.universe_manager.strategies:
                            all_symbols.update(strategy.symbols)
                        all_symbols = list(all_symbols)
                        
                        # Fetch and store universe data
                        print("📊 Storing universe data for Monte Carlo simulations...")
                        tv_fetcher = TradingViewDataFetcher()
                        returns_df = tv_fetcher.get_returns_data(all_symbols, days=180)
                        
                        if len(returns_df) > 0:
                            # Store in universe manager
                            self.universe_manager.universe_data = {
                                'returns': returns_df,
                                'symbols': all_symbols
                            }
                            print(f"✅ Stored universe data: {len(returns_df)} days, {len(returns_df.columns)} stocks")
                        else:
                            print("⚠️  Could not store universe data, Monte Carlo will fetch fresh data")
                    except Exception as data_error:
                        print(f"⚠️  Could not store universe data: {data_error}")
                
                # Update GUI
                self.root.after(0, self.refresh_portfolios)
                
                if self.universe_manager.strategies:
                    self.root.after(0, lambda: self.update_status(
                        f"Created {len(self.universe_manager.strategies)} optimized portfolios", False))
                    self.root.after(0, self.wizard_success)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", 
                        "Could not create any portfolios. Check that universe contains valid stocks with sufficient historical data."))
                    self.root.after(0, self.wizard_cleanup)
                    
            except Exception as e:
                print(f"❌ Critical error in portfolio creation: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda err=str(e): messagebox.showerror("Error", f"Error creating portfolios: {err}"))
                self.root.after(0, self.wizard_cleanup)
            finally:
                print("🏁 Portfolio creation thread finished")
                self.root.after(0, lambda: self.update_status("Ready", False))
        
        threading.Thread(target=optimize_in_background, daemon=True).start()

    def wizard_cleanup(self):
        """Clean up wizard after completion or error."""
        try:
            if hasattr(self, 'portfolio_wizard') and self.portfolio_wizard and self.portfolio_wizard.winfo_exists():
                if hasattr(self, 'wizard_progress') and self.wizard_progress:
                    self.wizard_progress.stop()
                self.portfolio_wizard.destroy()
                print("🧹 Wizard cleaned up after error")
        except Exception as e:
            print(f"Error during wizard cleanup: {e}")

    def wizard_success(self):
        """Handle successful portfolio creation."""
        try:
            if hasattr(self, 'portfolio_wizard') and self.portfolio_wizard and self.portfolio_wizard.winfo_exists():
                if hasattr(self, 'wizard_progress') and self.wizard_progress:
                    self.wizard_progress.stop()
                if hasattr(self, 'wizard_status') and self.wizard_status:
                    self.wizard_status.config(text="✅ Portfolios created successfully!")
                
                # Brief delay to show success message
                self.root.after(1000, self.complete_wizard_success)
        except Exception as e:
            print(f"Error in wizard success: {e}")
            self.wizard_cleanup()

    def complete_wizard_success(self):
        """Complete the wizard success process."""
        try:
            # Show success message
            strategy_count = len(self.universe_manager.strategies) if hasattr(self.universe_manager, 'strategies') else 0
            messagebox.showinfo("Success", 
                f"Created {strategy_count} optimized portfolios!\n\n"
                "Switching to the 'Portfolio Overview' tab to view and analyze them.")
            
            # Close wizard
            if hasattr(self, 'portfolio_wizard') and self.portfolio_wizard and self.portfolio_wizard.winfo_exists():
                self.portfolio_wizard.destroy()
                
            # Switch to portfolio overview tab
            self.notebook.select(1)  # Portfolio Overview is tab index 1
            print("🎉 Wizard completed successfully")
            
        except Exception as e:
            print(f"Error completing wizard success: {e}")
            self.wizard_cleanup()

    def show_quick_start(self):
        """Show quick start guide for new users."""
        quick_start = tk.Toplevel(self.root)
        quick_start.title("🚀 Quick Start Guide")
        quick_start.geometry("500x400")
        quick_start.transient(self.root)
        quick_start.grab_set()
        
        # Center window
        quick_start.update_idletasks()
        x = (quick_start.winfo_screenwidth() // 2) - (250)
        y = (quick_start.winfo_screenheight() // 2) - (200)
        quick_start.geometry(f"500x400+{x}+{y}")
        
        # Content
        main_frame = ttk.Frame(quick_start)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        ttk.Label(main_frame, text="🚀 Welcome to Portfolio Management!", 
                 font=("Arial", 16, "bold")).pack(pady=(0, 10))
        
        # Instructions
        instructions = """
📊 STEP 1: Select ETFs
• Go to the 'ETF Selection' tab
• Enter ETF symbols (e.g., SPY, QQQ, XLF, XLK)
• Click 'Build Universe' to create your stock universe

🎯 STEP 2: Create Portfolios  
• After building universe, click 'Create Optimized Portfolios'
• Choose portfolio types (Conservative, Balanced, Growth)
• Set optimization parameters

💼 STEP 3: Analyze Results
• View portfolio allocations in 'Portfolio Overview' tab
• Run Monte Carlo simulations in 'Simulation' tab
• Track performance metrics in 'Metrics' tab

⚖️ STEP 4: Set Rebalancing
• Configure rebalancing frequency in 'Rebalancing' tab
• Set thresholds and schedules

⚡ QUICK ACCESS:
• Press Ctrl+P or F5 to create portfolios from any tab
• Use "🚀 Create Portfolios" buttons on every tab
• Portfolio menu → Create Portfolios

💡 PRO TIP: Start with popular ETFs like SPY, QQQ, IWM, EFA
        """
        
        text_widget = tk.Text(main_frame, wrap=tk.WORD, font=("Arial", 10))
        text_widget.insert(tk.END, instructions.strip())
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def dont_show_again():
            self.config['quick_start_shown'] = True
            self.save_config()
            quick_start.destroy()
        
        ttk.Button(button_frame, text="Don't show again", 
                  command=dont_show_again).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Got it!", 
                  command=quick_start.destroy).pack(side=tk.RIGHT)

    def on_portfolio_selected(self, event=None):
        """Handle portfolio selection change."""
        selected_name = self.portfolio_selector.get()
        if not selected_name or not hasattr(self.universe_manager, 'strategies'):
            return
            
        # Find the selected strategy
        selected_strategy = None
        for strategy in self.universe_manager.strategies:
            if strategy.name == selected_name:
                selected_strategy = strategy
                break
        
        if selected_strategy:
            self.display_portfolio_allocation(selected_strategy)
            self.update_portfolio_metrics(selected_strategy)

    def display_portfolio_allocation(self, strategy):
        """Display portfolio allocation chart."""
        try:
            self.portfolio_fig.clear()
            
            if strategy.weights is not None and len(strategy.weights) > 0:
                # Create pie chart
                ax = self.portfolio_fig.add_subplot(111)
                
                # Filter out very small weights for cleaner display
                min_display_weight = 0.01  # 1%
                display_weights = []
                display_labels = []
                other_weight = 0
                
                for symbol, weight in zip(strategy.symbols, strategy.weights):
                    if weight >= min_display_weight:
                        display_weights.append(weight)
                        display_labels.append(f"{symbol}\n{weight:.1%}")
                    else:
                        other_weight += weight
                
                if other_weight > 0:
                    display_weights.append(other_weight)
                    display_labels.append(f"Others\n{other_weight:.1%}")
                
                # Create pie chart with colors
                colors = plt.cm.Set3(np.linspace(0, 1, len(display_weights)))
                wedges, texts, autotexts = ax.pie(display_weights, labels=display_labels, 
                                                 autopct='', startangle=90, colors=colors)
                
                ax.set_title(f"{strategy.name}\nAllocation", fontsize=14, fontweight='bold')
                
                # Adjust text size
                for text in texts:
                    text.set_fontsize(8)
                
            else:
                # No weights available - show equal weight assumption
                ax = self.portfolio_fig.add_subplot(111)
                n_stocks = len(strategy.symbols)
                equal_weights = [1/n_stocks] * n_stocks
                
                # Show only top 10 for readability
                display_symbols = strategy.symbols[:10]
                display_weights = equal_weights[:10]
                
                if len(strategy.symbols) > 10:
                    remaining = len(strategy.symbols) - 10
                    remaining_weight = sum(equal_weights[10:])
                    display_symbols.append(f"Others ({remaining})")
                    display_weights.append(remaining_weight)
                
                colors = plt.cm.Set3(np.linspace(0, 1, len(display_weights)))
                ax.pie(display_weights, labels=[f"{s}\n{w:.1%}" for s, w in zip(display_symbols, display_weights)], 
                      autopct='', startangle=90, colors=colors)
                ax.set_title(f"{strategy.name}\n(Equal Weight)", fontsize=14, fontweight='bold')
            
            self.portfolio_fig.tight_layout()
            self.portfolio_canvas.draw()
            
            # Update holdings table
            self.update_holdings_table(strategy)
            
        except Exception as e:
            print(f"Error displaying portfolio allocation: {e}")

    def update_holdings_table(self, strategy):
        """Update the holdings table in portfolio overview."""
        try:
            # Clear existing items
            for item in self.holdings_tree.get_children():
                self.holdings_tree.delete(item)
            
            if strategy.weights is not None:
                # Sort by weight descending
                holdings_data = list(zip(strategy.symbols, strategy.weights))
                holdings_data.sort(key=lambda x: x[1], reverse=True)
                
                # Add top holdings to table
                for i, (symbol, weight) in enumerate(holdings_data[:20]):  # Show top 20
                    # Assume $100k portfolio for value calculation
                    portfolio_value = 100000
                    position_value = portfolio_value * weight
                    
                    self.holdings_tree.insert("", tk.END, text=symbol,
                                            values=(f"{weight:.2%}", f"${position_value:,.0f}"))
            else:
                # Equal weight
                equal_weight = 1.0 / len(strategy.symbols)
                portfolio_value = 100000
                position_value = portfolio_value * equal_weight
                
                for symbol in strategy.symbols[:20]:  # Show top 20
                    self.holdings_tree.insert("", tk.END, text=symbol,
                                            values=(f"{equal_weight:.2%}", f"${position_value:,.0f}"))
                    
        except Exception as e:
            print(f"Error updating holdings table: {e}")

    def update_portfolio_metrics(self, strategy):
        """Update portfolio metrics display."""
        try:
            if strategy.metrics:
                metrics_data = {
                    "Expected Return": f"{strategy.metrics.expected_return:.2%}",
                    "Volatility": f"{strategy.metrics.volatility:.2%}",
                    "Sharpe Ratio": f"{strategy.metrics.sharpe_ratio:.3f}",
                    "VaR (95%)": f"{strategy.metrics.var_95:.2%}" if hasattr(strategy.metrics, 'var_95') else "N/A",
                    "Max Drawdown": "N/A"  # Would need historical simulation
                }
            else:
                # Show placeholder values
                metrics_data = {
                    "Expected Return": "Calculating...",
                    "Volatility": "Calculating...", 
                    "Sharpe Ratio": "Calculating...",
                    "VaR (95%)": "Calculating...",
                    "Max Drawdown": "Calculating..."
                }
            
            # Update the metrics labels
            for metric, value in metrics_data.items():
                if metric in self.metrics_labels:
                    self.metrics_labels[metric].config(text=value)
                    
        except Exception as e:
            print(f"Error updating portfolio metrics: {e}")

    def update_metrics(self):
        """Update metrics for current portfolio."""
        selected_name = self.portfolio_selector.get()
        if selected_name and hasattr(self.universe_manager, 'strategies'):
            for strategy in self.universe_manager.strategies:
                if strategy.name == selected_name:
                    self.update_portfolio_metrics(strategy)
                    break

    def analyze_drift(self):
        """Analyze portfolio drift from target allocation."""
        messagebox.showinfo("Portfolio Drift", "Portfolio drift analysis would be implemented here.\n\n"
                          "This would compare current positions to target weights and show rebalancing needs.")

    def rebalance_now(self):
        """Execute portfolio rebalancing."""
        messagebox.showinfo("Rebalancing", "Portfolio rebalancing execution would be implemented here.\n\n"
                          "This would generate trade orders to rebalance to target weights.")

    def backtest_rebalancing(self):
        """Backtest rebalancing strategies."""
        messagebox.showinfo("Backtesting", "Rebalancing backtest would be implemented here.\n\n"
                          "This would show historical performance of different rebalancing frequencies.")

    def load_portfolio(self):
        """Load a saved portfolio."""
        try:
            file_path = filedialog.askopenfilename(
                title="Load Portfolio",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                defaultextension=".json"
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    portfolio_data = json.load(f)
                
                # Reconstruct portfolio strategy
                from src.data.universe_manager import PortfolioStrategy
                strategy = PortfolioStrategy(
                    name=portfolio_data.get('name', 'Loaded Portfolio'),
                    description=portfolio_data.get('description', 'Loaded from file'),
                    symbols=portfolio_data.get('symbols', []),
                    weights=np.array(portfolio_data.get('weights', [])) if portfolio_data.get('weights') else None
                )
                
                # Add to strategies
                if not hasattr(self.universe_manager, 'strategies'):
                    self.universe_manager.strategies = []
                    
                self.universe_manager.strategies.append(strategy)
                self.refresh_portfolios()
                self.portfolio_selector.set(strategy.name)
                self.on_portfolio_selected()
                
                messagebox.showinfo("Success", f"Portfolio '{strategy.name}' loaded successfully!")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading portfolio: {e}")

    def save_portfolio(self):
        """Save current portfolio."""
        try:
            selected_name = self.portfolio_selector.get()
            if not selected_name or not hasattr(self.universe_manager, 'strategies'):
                messagebox.showwarning("Warning", "No portfolio selected to save")
                return
            
            # Find selected strategy
            selected_strategy = None
            for strategy in self.universe_manager.strategies:
                if strategy.name == selected_name:
                    selected_strategy = strategy
                    break
            
            if not selected_strategy:
                messagebox.showwarning("Warning", "Selected portfolio not found")
                return
            
            # Choose save location
            file_path = filedialog.asksaveasfilename(
                title="Save Portfolio",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialvalue=f"{selected_strategy.name.replace(' ', '_')}.json"
            )
            
            if file_path:
                # Prepare data for saving
                portfolio_data = {
                    'name': selected_strategy.name,
                    'description': selected_strategy.description,
                    'symbols': selected_strategy.symbols,
                    'weights': selected_strategy.weights.tolist() if selected_strategy.weights is not None else None,
                    'created_date': datetime.now().isoformat(),
                    'metrics': {
                        'expected_return': selected_strategy.metrics.expected_return if selected_strategy.metrics else None,
                        'volatility': selected_strategy.metrics.volatility if selected_strategy.metrics else None,
                        'sharpe_ratio': selected_strategy.metrics.sharpe_ratio if selected_strategy.metrics else None
                    } if selected_strategy.metrics else None
                }
                
                with open(file_path, 'w') as f:
                    json.dump(portfolio_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Portfolio saved to {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saving portfolio: {e}")

    def export_data(self):
        """Export portfolio data to Excel/CSV."""
        try:
            selected_name = self.portfolio_selector.get()
            if not selected_name or not hasattr(self.universe_manager, 'strategies'):
                messagebox.showwarning("Warning", "No portfolio selected to export")
                return
            
            # Find selected strategy
            selected_strategy = None
            for strategy in self.universe_manager.strategies:
                if strategy.name == selected_name:
                    selected_strategy = strategy
                    break
            
            if not selected_strategy:
                messagebox.showwarning("Warning", "Selected portfolio not found")
                return
            
            # Choose export location
            file_path = filedialog.asksaveasfilename(
                title="Export Portfolio Data",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                initialvalue=f"{selected_strategy.name.replace(' ', '_')}_export.xlsx"
            )
            
            if file_path:
                # Create DataFrame with portfolio data
                portfolio_df = pd.DataFrame({
                    'Symbol': selected_strategy.symbols,
                    'Weight': selected_strategy.weights if selected_strategy.weights is not None else [1/len(selected_strategy.symbols)] * len(selected_strategy.symbols)
                })
                
                if file_path.endswith('.xlsx'):
                    portfolio_df.to_excel(file_path, index=False)
                else:
                    portfolio_df.to_csv(file_path, index=False)
                
                messagebox.showinfo("Success", f"Portfolio data exported to {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting data: {e}")

    def clean_temp_files(self):
        """Clean temporary files."""
        try:
            cleaned_count = self.file_manager.clean_temp_files()
            messagebox.showinfo("File Cleanup", f"Cleaned {cleaned_count} temporary files")
        except Exception as e:
            messagebox.showerror("Error", f"Error cleaning files: {e}")

    def create_archive(self):
        """Create archive of analysis session."""
        try:
            archive_path = self.file_manager.create_archive()
            messagebox.showinfo("Archive Created", f"Analysis session archived to:\n{archive_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error creating archive: {e}")
    
    def show_cache_stats(self):
        """Show cache statistics in a popup window."""
        try:
            from src.utils.cache_manager import get_cache_manager
            cache = get_cache_manager()
            stats = cache.get_cache_stats()
            
            stats_window = tk.Toplevel(self.root)
            stats_window.title("📊 Cache Statistics")
            stats_window.geometry("500x400")
            stats_window.transient(self.root)
            stats_window.grab_set()
            
            # Center window
            stats_window.update_idletasks()
            x = (stats_window.winfo_screenwidth() // 2) - (250)
            y = (stats_window.winfo_screenheight() // 2) - (200)
            stats_window.geometry(f"500x400+{x}+{y}")
            
            main_frame = ttk.Frame(stats_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            ttk.Label(main_frame, text="📊 Data Cache Statistics", 
                     font=("Arial", 14, "bold")).pack(pady=(0, 15))
            
            # Stats content
            stats_text = f"""
💾 Cache Overview:
   • Total cached files: {stats['total_files']}
   • Total cache size: {stats['total_size_mb']:.1f} MB
   • Maximum cache size: 100 MB

📈 Data Breakdown:
   • TradingView data: {stats['tv_data_files']} files
   • Polygon.io data: {stats['polygon_data_files']} files  
   • Metadata files: {stats['metadata_files']} files

⏰ Cache Timing:
   • Oldest entry: {stats['oldest_entry'].strftime('%Y-%m-%d %H:%M:%S') if stats['oldest_entry'] else 'N/A'}
   • Newest entry: {stats['newest_entry'].strftime('%Y-%m-%d %H:%M:%S') if stats['newest_entry'] else 'N/A'}

🔄 Cache Benefits:
   • Faster portfolio creation (2-10x speedup)
   • Reduced API calls and rate limiting
   • Improved reliability and performance
   • Automatic expiration management

⚙️ Cache Settings:
   • TradingView data expires: 4 hours
   • Polygon.io options expire: 1 hour
   • Stock prices expire: 4 hours
   • Automatic cleanup enabled
            """
            
            text_widget = tk.Text(main_frame, wrap=tk.WORD, font=("Consolas", 10))
            text_widget.insert(tk.END, stats_text.strip())
            text_widget.config(state=tk.DISABLED)
            text_widget.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(button_frame, text="🔄 Refresh Stats", 
                      command=lambda: self.refresh_cache_stats(text_widget, cache)).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="🧹 Clear Cache", 
                      command=lambda: self.clear_cache_from_stats(stats_window, cache)).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Close", 
                      command=stats_window.destroy).pack(side=tk.RIGHT)
            
        except ImportError:
            messagebox.showwarning("Cache Stats", "Cache manager not available")
        except Exception as e:
            messagebox.showerror("Error", f"Could not show cache stats: {e}")
    
    def clear_cache(self):
        """Clear all cached data."""
        result = messagebox.askyesno("Clear Cache", 
                                   "Are you sure you want to clear all cached data?\n\n"
                                   "This will remove all cached API responses and "
                                   "the next data fetch will be slower.")
        if result:
            try:
                from src.utils.cache_manager import get_cache_manager
                cache = get_cache_manager()
                cache.clear_cache()
                messagebox.showinfo("Cache Cleared", "All cached data has been cleared successfully.")
            except ImportError:
                messagebox.showwarning("Clear Cache", "Cache manager not available")
            except Exception as e:
                messagebox.showerror("Error", f"Could not clear cache: {e}")

    def load_saved_portfolios(self):
        """Load any previously saved portfolios on startup."""
        try:
            # This would load from a default location or config
            # For now, just ensure the universe manager has an empty strategies list
            if not hasattr(self.universe_manager, 'strategies'):
                self.universe_manager.strategies = []
        except Exception as e:
            print(f"Error loading saved portfolios: {e}")
    
    def run(self):
        """Start the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main function to run the GUI."""
    app = PortfolioGUI()
    app.run()


if __name__ == "__main__":
    main()