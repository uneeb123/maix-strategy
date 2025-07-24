import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tests.helper.load_data import load_sample_candles

def zigzag_strategy(prices: List[float], deviation: float = 0.05) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    ZigZag algorithm - finds significant turning points
    deviation: minimum price change percentage to consider a turn
    """
    peaks = []
    valleys = []
    last_peak = None
    last_valley = None
    
    for i, price in enumerate(prices):
        if last_peak is None:
            last_peak = (i, price)
        elif last_valley is None:
            if price < last_peak[1]:
                last_valley = (i, price)
            elif price > last_peak[1]:
                last_peak = (i, price)
        else:
            # We have both peak and valley
            if price > last_valley[1] * (1 + deviation):
                # New peak (sell signal)
                valleys.append(last_valley)
                last_peak = (i, price)
                last_valley = None
            elif price < last_peak[1] * (1 - deviation):
                # New valley (buy signal)
                peaks.append(last_peak)
                last_valley = (i, price)
                last_peak = None
    
    # Add final points if they exist
    if last_peak:
        peaks.append(last_peak)
    if last_valley:
        valleys.append(last_valley)
    
    return peaks, valleys

def find_zigzag(candles: List, deviation: float = 0.05, max_points: int = 15) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find zigzag points in candle data.
    
    Args:
        candles: List of Candle objects
        deviation: Minimum price change percentage to consider a turn (default: 0.05 = 5%)
        max_points: Maximum number of points to return per type (default: 15)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    prices = [c.close for c in candles]
    
    # Find all zigzag points
    peaks, valleys = zigzag_strategy(prices, deviation)
    
    # Convert to timestamp-based points
    buy_points = []
    sell_points = []
    
    for index, price in valleys:
        if index < len(candles):
            buy_points.append((candles[index].timestamp, price, index))
    
    for index, price in peaks:
        if index < len(candles):
            sell_points.append((candles[index].timestamp, price, index))
    
    # Sort by timestamp
    buy_points.sort(key=lambda x: x[0])
    sell_points.sort(key=lambda x: x[0])
    
    # Limit to max_points
    buy_points = [(point[0], point[1]) for point in buy_points[:max_points]]
    sell_points = [(point[0], point[1]) for point in sell_points[:max_points]]
    
    return buy_points, sell_points