import os
import mplfinance as mpf
import matplotlib.pyplot as plt
import platform
import subprocess
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Tuple
from core.strategy_interface import Candle
from rich.console import Console

console = Console()

def plot_trading_signals(
    candles: List[Candle], 
    token_id: int,
    strategy_name: str,
    buy_points: List[Tuple[datetime, float]] = None,
    sell_points: List[Tuple[datetime, float]] = None
) -> str:
    if not candles:
        console.print("[red]No candle data to plot[/red]")
        return ""
    
    try:
        # Create DataFrame from candles
        df = pd.DataFrame([
            {
                'timestamp': c.timestamp,
                'Open': c.open,
                'High': c.high,
                'Low': c.low,
                'Close': c.close,
                'Volume': c.volume
            }
            for c in candles
        ])
        df.set_index('timestamp', inplace=True)
        
        # Create markers for buy/sell points
        buy_marker = np.full(len(df), np.nan)
        sell_marker = np.full(len(df), np.nan)
        
        # Map timestamps to DataFrame indices
        time_to_idx = {pd.Timestamp(t): i for i, t in enumerate(df.index)}
        
        # Mark buy points (local minima)
        if buy_points:
            for timestamp, price in buy_points:
                idx = time_to_idx.get(pd.Timestamp(timestamp))
                if idx is not None:
                    buy_marker[idx] = price
        
        # Mark sell points (local maxima)
        if sell_points:
            for timestamp, price in sell_points:
                idx = time_to_idx.get(pd.Timestamp(timestamp))
                if idx is not None:
                    sell_marker[idx] = price
        
        # Create additional plots
        apds = []
        if np.any(~np.isnan(buy_marker)):
            apds.append(mpf.make_addplot(
                buy_marker, 
                type='scatter', 
                markersize=150, 
                marker='^', 
                color='green', 
                panel=0,
                label='Buy Signals'
            ))
        
        if np.any(~np.isnan(sell_marker)):
            apds.append(mpf.make_addplot(
                sell_marker, 
                type='scatter', 
                markersize=150, 
                marker='v', 
                color='red', 
                panel=0,
                label='Sell Signals'
            ))
        
        # Create artifacts directory
        artifacts_dir = 'artifacts'
        os.makedirs(artifacts_dir, exist_ok=True)
        
        # Generate filename
        now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{token_id}_{strategy_name}_{now_str}.png"
            
        image_path = os.path.join(artifacts_dir, filename)
        
        # Create the plot
        fig, axes = mpf.plot(
            df,
            type='candle',
            volume=True,
            addplot=apds,
            returnfig=True,
            figscale=1.2,
            figratio=(16, 9),
            style='yahoo',
            panel_ratios=(3, 1),
            warn_too_much_data=4000
        )
        
        # Add legend
        if apds:
            axes[0].legend()
        
        # Save and close
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            plt.tight_layout()
        
        plt.savefig(image_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        console.print(f"[green]Saved extrema detection plot to {image_path}[/green]")
        
        # Try to open the image
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", image_path], check=False)
            elif platform.system() == "Windows":
                os.startfile(image_path)
            else:
                subprocess.run(["xdg-open", image_path], check=False)
        except Exception as e:
            console.print(f"[yellow]Could not open image automatically: {e}[/yellow]")
        
        return image_path
        
    except Exception as e:
        console.print(f"[red]Error creating plot: {e}[/red]")
        raise 