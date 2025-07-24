import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tests.helper.load_data import load_sample_candles

def zigzag_strategy(prices: List[float], timestamps: List[int], threshold_pct: float = 0.015) -> List[Tuple[int, float]]:
    """
    ZigZag algorithm for finding pivot points in price data
    
    Args:
        prices: List of closing prices
        timestamps: List of timestamps corresponding to prices
        threshold_pct: Percentage threshold for pivot detection (default: 1.5%)
    
    Returns:
        List of pivot points as (timestamp, price) tuples
    """
    pivots = []
    
    if len(prices) < 2:
        return pivots
    
    last_pivot_idx = 0
    last_pivot_price = prices[0]
    direction = None
    
    for i in range(1, len(prices)):
        change_pct = (prices[i] - last_pivot_price) / last_pivot_price
        
        if direction is None:
            if abs(change_pct) >= threshold_pct:
                direction = 'up' if change_pct > 0 else 'down'
                last_pivot_idx = i
                last_pivot_price = prices[i]
                pivots.append((timestamps[i], prices[i]))
        
        elif direction == 'up':
            if prices[i] > last_pivot_price:
                last_pivot_idx = i
                last_pivot_price = prices[i]
                pivots[-1] = (timestamps[i], prices[i])
            elif (prices[i] - last_pivot_price) / last_pivot_price <= -threshold_pct:
                direction = 'down'
                last_pivot_idx = i
                last_pivot_price = prices[i]
                pivots.append((timestamps[i], prices[i]))
        
        elif direction == 'down':
            if prices[i] < last_pivot_price:
                last_pivot_idx = i
                last_pivot_price = prices[i]
                pivots[-1] = (timestamps[i], prices[i])
            elif (prices[i] - last_pivot_price) / last_pivot_price >= threshold_pct:
                direction = 'up'
                last_pivot_idx = i
                last_pivot_price = prices[i]
                pivots.append((timestamps[i], prices[i]))
    
    return pivots

def find_zigzag_signals(candles: List, threshold_pct: float = 0.015, max_points: int = 15) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find ZigZag pivot points and generate buy/sell signals
    
    Args:
        candles: List of Candle objects
        threshold_pct: Percentage threshold for pivot detection (default: 1.5%)
        max_points: Maximum number of points to return per type (default: 15)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    prices = [c.close for c in candles]
    timestamps = [c.timestamp for c in candles]
    
    # Find pivot points
    pivot_points = zigzag_strategy(prices, timestamps, threshold_pct)
    
    if len(pivot_points) < 2:
        return [], []
    
    # Generate trading signals
    buy_points = []
    sell_points = []
    position = None
    
    for i in range(1, len(pivot_points)):
        prev_time, prev_price = pivot_points[i - 1]
        curr_time, curr_price = pivot_points[i]
        
        if curr_price > prev_price and position is not None:
            # Sell signal
            sell_points.append((curr_time, curr_price))
            position = None
        elif curr_price < prev_price:
            # Buy signal
            buy_points.append((prev_time, prev_price))
            position = (prev_time, prev_price)
    
    # Sort by timestamp
    buy_points.sort(key=lambda x: x[0])
    sell_points.sort(key=lambda x: x[0])
    
    # Limit to max_points
    buy_points = buy_points[:max_points]
    sell_points = sell_points[:max_points]
    
    return buy_points, sell_points 