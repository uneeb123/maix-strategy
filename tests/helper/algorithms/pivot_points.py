import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from tests.helper.load_data import load_sample_candles

def pivot_points_strategy(highs: List[float], lows: List[float], closes: List[float], 
                         window: int = 5) -> List[Tuple[str, int, float]]:
    """
    Pivot Points - widely used by traders for support/resistance
    """
    pivots = []
    
    for i in range(window, len(closes) - window):
        # Pivot High (resistance)
        is_pivot_high = True
        for j in range(i - window, i + window + 1):
            if j != i and highs[j] >= highs[i]:
                is_pivot_high = False
                break
        
        if is_pivot_high:
            pivots.append(('resistance', i, highs[i]))
        
        # Pivot Low (support)
        is_pivot_low = True
        for j in range(i - window, i + window + 1):
            if j != i and lows[j] <= lows[i]:
                is_pivot_low = False
                break
        
        if is_pivot_low:
            pivots.append(('support', i, lows[i]))
    
    return pivots

def find_pivot_points(candles: List, window: int = 5, max_points: int = 15) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find pivot points in candle data.
    
    Args:
        candles: List of Candle objects
        window: Window size for finding pivots (default: 5)
        max_points: Maximum number of points to return per type (default: 15)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    
    # Find all pivot points
    pivots = pivot_points_strategy(highs, lows, closes, window)
    
    # Separate into support (buy) and resistance (sell) points
    support_points = []
    resistance_points = []
    
    for pivot_type, index, price in pivots:
        if pivot_type == 'support':
            support_points.append((candles[index].timestamp, price, index))
        else:  # resistance
            resistance_points.append((candles[index].timestamp, price, index))
    
    # Sort by timestamp
    support_points.sort(key=lambda x: x[0])
    resistance_points.sort(key=lambda x: x[0])
    
    # Limit to max_points
    buy_points = [(point[0], point[1]) for point in support_points[:max_points]]
    sell_points = [(point[0], point[1]) for point in resistance_points[:max_points]]
    
    return buy_points, sell_points