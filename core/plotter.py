import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional
from core.strategy_interface import Candle
from core.indicators import calculate_pivot_points
from rich.console import Console

console = Console()

def plot_trading_signals(
    candles: List[Candle], 
    token_title: str,
    strategy_name: str,
    indicators: Optional[Dict[str, Dict[str, Any]]] = None
) -> str:
    """
    Plot trading signals with optional indicators.
    
    Args:
        candles: List of Candle objects
        token_title: Title for the token
        strategy_name: Name of the strategy
        indicators: Dictionary of indicators to plot with their parameters
                   Example: {"pivot_points": {"window": 5}}
    """
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
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{token_title}', 'Volume'),
            row_width=[0.2, 0.8]
        )
        
        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='OHLC',
                increasing_line_color='#26A69A',
                decreasing_line_color='#EF5350'
            ),
            row=1, col=1
        )
        
        # Add volume bars with better visibility
        colors = ['#26A69A' if close >= open else '#EF5350' 
                 for close, open in zip(df['Close'], df['Open'])]
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.8,
                width=0.8,
                marker_line_width=0
            ),
            row=2, col=1
        )
        
        # Add indicators
        if indicators:
            for indicator_name, params in indicators.items():
                if indicator_name == "pivot_points":
                    window = params.get("window", 5)
                    pivot_low, pivot_high = calculate_pivot_points(candles, window)
                    
                    # Add pivot low points (support)
                    if pivot_low:
                        pivot_low_df = pd.DataFrame(pivot_low, columns=['timestamp', 'price'])
                        fig.add_trace(
                            go.Scatter(
                                x=pivot_low_df['timestamp'],
                                y=pivot_low_df['price'],
                                mode='markers',
                                name=f'Pivot Low (w={window})',
                                marker=dict(
                                    symbol='triangle-up',
                                    size=10,
                                    color='blue',
                                    line=dict(width=1, color='darkblue')
                                )
                            ),
                            row=1, col=1
                        )
                    
                    # Add pivot high points (resistance)
                    if pivot_high:
                        pivot_high_df = pd.DataFrame(pivot_high, columns=['timestamp', 'price'])
                        fig.add_trace(
                            go.Scatter(
                                x=pivot_high_df['timestamp'],
                                y=pivot_high_df['price'],
                                mode='markers',
                                name=f'Pivot High (w={window})',
                                marker=dict(
                                    symbol='triangle-down',
                                    size=10,
                                    color='orange',
                                    line=dict(width=1, color='darkorange')
                                )
                            ),
                            row=1, col=1
                        )
        
        # Update layout
        fig.update_layout(
            title=f'{strategy_name}',
            xaxis_rangeslider_visible=False,
            height=800,
            showlegend=True,
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # Update axes with better styling
        fig.update_xaxes(title_text="Time", row=2, col=1, gridcolor='lightgray', showgrid=True)
        fig.update_yaxes(title_text="Price", row=1, col=1, gridcolor='lightgray', showgrid=True)
        fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor='lightgray', showgrid=True)
        
        # Show the plot in browser
        fig.show(browser=True)
        
        console.print(f"[green]Opened interactive chart for {strategy_name} strategy[/green]")
        
        return "Interactive chart opened in browser"
        
    except Exception as e:
        console.print(f"[red]Error creating plot: {e}[/red]")
        raise 