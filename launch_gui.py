"""
Portfolio Management GUI Launcher

Simple launcher script for the Portfolio Management GUI application.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import matplotlib
        import pandas
        import numpy
        import scipy
        import yfinance
        return True
    except ImportError as e:
        missing_package = str(e).split("'")[1] if "'" in str(e) else "unknown"
        messagebox.showerror(
            "Missing Dependencies", 
            f"Missing required package: {missing_package}\n\n"
            "Please install dependencies by running:\n"
            f"pip install {missing_package}"
        )
        return False


def launch_gui():
    """Launch the main GUI application."""
    try:
        # Import and run the GUI
        from portfolio_gui import PortfolioGUI
        app = PortfolioGUI()
        
        # Ensure the window comes to front and is visible
        app.root.lift()
        app.root.attributes('-topmost', True)
        app.root.after_idle(lambda: app.root.attributes('-topmost', False))
        app.root.focus_force()
        
        app.run()
    except Exception as e:
        messagebox.showerror("Launch Error", f"Failed to launch GUI:\n{e}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")


def create_splash_screen():
    """Create a splash screen while loading."""
    splash = tk.Tk()
    splash.title("Portfolio Management System")
    splash.geometry("500x300")
    splash.resizable(False, False)
    
    # Center the window
    splash.eval('tk::PlaceWindow . center')
    
    # Create content
    main_frame = tk.Frame(splash, bg='#f0f0f0')
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = tk.Label(main_frame, text="🏛️ Portfolio Management System", 
                          font=("Arial", 20, "bold"), bg='#f0f0f0', fg='#2c3e50')
    title_label.pack(pady=30)
    
    # Subtitle
    subtitle_label = tk.Label(main_frame, text="Ultra-Powerful Portfolio Management", 
                             font=("Arial", 12), bg='#f0f0f0', fg='#7f8c8d')
    subtitle_label.pack(pady=10)
    
    # Features list
    features_frame = tk.Frame(main_frame, bg='#f0f0f0')
    features_frame.pack(pady=20)
    
    features = [
        "📊 ETF-Based Universe Building",
        "💼 Multi-Strategy Portfolio Optimization",
        "🎲 Monte Carlo Simulation",
        "📈 Performance Tracking & Metrics",
        "⚖️ Automated Rebalancing",
        "📁 Advanced File Management"
    ]
    
    for feature in features:
        feature_label = tk.Label(features_frame, text=feature, 
                               font=("Arial", 10), bg='#f0f0f0', fg='#34495e')
        feature_label.pack(anchor=tk.W, pady=2)
    
    # Status label
    status_label = tk.Label(main_frame, text="Checking dependencies...", 
                           font=("Arial", 10, "italic"), bg='#f0f0f0', fg='#95a5a6')
    status_label.pack(pady=20)
    
    # Launch button (initially disabled)
    launch_button = tk.Button(main_frame, text="🚀 Launch Application", 
                             font=("Arial", 12, "bold"), state=tk.DISABLED,
                             bg='#3498db', fg='white', padx=20, pady=10)
    launch_button.pack(pady=10)
    
    def check_and_enable():
        """Check dependencies and enable launch button."""
        splash.update()
        
        if check_dependencies():
            status_label.config(text="✅ All dependencies found", fg='#27ae60')
            def launch_and_close():
                splash.withdraw()  # Hide splash first
                try:
                    launch_gui()
                finally:
                    splash.quit()  # Ensure splash mainloop ends
            launch_button.config(state=tk.NORMAL, command=launch_and_close)
        else:
            status_label.config(text="❌ Missing dependencies", fg='#e74c3c')
            launch_button.config(text="❌ Cannot Launch", bg='#e74c3c')
    
    # Check dependencies after a short delay
    splash.after(1000, check_and_enable)
    
    # Close button
    close_button = tk.Button(main_frame, text="❌ Close", 
                            command=splash.destroy, bg='#95a5a6', fg='white')
    close_button.pack(pady=5)
    
    splash.mainloop()


def create_desktop_shortcut():
    """Create a desktop shortcut (Windows only)."""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Portfolio Management.lnk")
        target = sys.executable
        wDir = os.path.dirname(os.path.abspath(__file__))
        icon = target
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
        shortcut.WorkingDirectory = wDir
        shortcut.IconLocation = icon
        shortcut.save()
        
        return True
    except ImportError:
        return False
    except Exception:
        return False


def show_quick_start_guide():
    """Show a quick start guide."""
    guide_window = tk.Tk()
    guide_window.title("📚 Quick Start Guide")
    guide_window.geometry("700x500")
    
    # Create scrollable text
    text_frame = tk.Frame(guide_window)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 11))
    scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    guide_text = """
🚀 PORTFOLIO MANAGEMENT SYSTEM - QUICK START GUIDE

Welcome to your ultra-powerful portfolio management system! Here's how to get started:

📊 STEP 1: ETF SELECTION
• Go to the "ETF Selection" tab
• Enter your desired ETFs (e.g., SPY, QQQ, XLF, XLK)
• Adjust minimum weight threshold (default: 2%)
• Set maximum holdings per ETF (default: 20)
• Click "Build Universe" to create your stock universe

💼 STEP 2: PORTFOLIO ANALYSIS
• Use "Analysis" menu → "Run Full Analysis"
• The system will fetch market data and optimize portfolios
• View results in the "Portfolio Overview" tab
• Examine different strategies (Equal Weight, Max Sharpe, Min Volatility)

🎲 STEP 3: MONTE CARLO SIMULATION
• Go to "Simulation" tab
• Set number of simulations (default: 1000)
• Adjust time horizon in days (default: 252 = 1 year)
• Set initial investment amount
• Click "Run Monte Carlo Simulation"

📈 STEP 4: PERFORMANCE TRACKING
• Visit "Metrics" tab for detailed performance analysis
• Compare different portfolio strategies
• View performance over time charts
• Analyze risk metrics and drawdowns

⚖️ STEP 5: REBALANCING SETUP
• Configure rebalancing in "Rebalancing" tab
• Choose frequency (Weekly, Monthly, Quarterly, etc.)
• Set drift threshold percentage
• Enable automatic rebalancing if desired
• Backtest your rebalancing strategy

💡 PRO TIPS:
• Save your ETF selections in Settings
• Use the File Manager to organize your analysis files
• Export data for further analysis in Excel
• Create archives of completed analysis sessions
• Enable auto-save for configuration persistence

🔧 SETTINGS & CUSTOMIZATION:
• Adjust risk-free rate for Sharpe ratio calculations
• Configure CPU cores for faster processing
• Enable data caching for improved performance
• Set up automatic file management

🆘 NEED HELP?
• Use Help menu for detailed documentation
• Check the README file for technical details
• File issues or questions through the support system

🎯 POWER USER FEATURES:
• Custom rebalancing strategies
• Advanced Monte Carlo parameters
• Detailed ETF overlap analysis
• Comprehensive performance attribution
• Automated report generation

Ready to optimize your portfolio? Click Launch Application!
    """
    
    text_widget.insert(tk.END, guide_text)
    text_widget.config(state=tk.DISABLED)
    
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Close button
    close_button = tk.Button(guide_window, text="✅ Got It!", 
                            command=guide_window.destroy, 
                            font=("Arial", 12, "bold"), bg='#27ae60', fg='white')
    close_button.pack(pady=10)
    
    guide_window.mainloop()


def main():
    """Main launcher function."""
    if len(sys.argv) > 1 and sys.argv[1] == '--guide':
        show_quick_start_guide()
    elif len(sys.argv) > 1 and sys.argv[1] == '--direct':
        # Direct launch without splash screen
        if check_dependencies():
            launch_gui()
    else:
        # Show splash screen and launch
        create_splash_screen()


if __name__ == "__main__":
    main()