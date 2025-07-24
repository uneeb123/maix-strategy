import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tests.helper.load_data import load_sample_candles

def swing_detection_strategy(highs: List[float], lows: List[float], strength: int = 2) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Swing High/Low detection - classic trading method
    strength: number of bars on each side to confirm swing
    """
    swing_highs = []
    swing_lows = []
    
    for i in range(strength, len(highs) - strength):
        # Swing High
        is_swing_high = True
        for j in range(i - strength, i + strength + 1):
            if j != i and highs[j] >= highs[i]:
                is_swing_high = False
                break
        
        if is_swing_high:
            swing_highs.append((i, highs[i]))
        
        # Swing Low
        is_swing_low = True
        for j in range(i - strength, i + strength + 1):
            if j != i and lows[j] <= lows[i]:
                is_swing_low = False
                break
        
        if is_swing_low:
            swing_lows.append((i, lows[i]))
    
    return swing_highs, swing_lows

def find_swings(candles: List, strength: int = 2, max_points: int = 15) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find swing points in candle data.
    
    Args:
        candles: List of Candle objects
        strength: Number of bars on each side to confirm swing (default: 2)
        max_points: Maximum number of points to return per type (default: 15)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    
    # Find all swing points
    swing_highs, swing_lows = swing_detection_strategy(highs, lows, strength)
    
    # Convert to timestamp-based points
    buy_points = []
    sell_points = []
    
    for index, price in swing_lows:
        if index < len(candles):
            buy_points.append((candles[index].timestamp, price, index))
    
    for index, price in swing_highs:
        if index < len(candles):
            sell_points.append((candles[index].timestamp, price, index))
    
    # Sort by timestamp
    buy_points.sort(key=lambda x: x[0])
    sell_points.sort(key=lambda x: x[0])
    
    # Limit to max_points
    buy_points = [(point[0], point[1]) for point in buy_points[:max_points]]
    sell_points = [(point[0], point[1]) for point in sell_points[:max_points]]
    
    return buy_points, sell_points