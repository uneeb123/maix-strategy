from datetime import datetime
from typing import List, Tuple
from core.strategy_interface import Candle

def calculate_pivot_points(candles: List[Candle], window: int = 5) -> Tuple[List[Tuple[datetime, float]], List[Tuple[datetime, float]]]:
    """
    Calculate pivot points from candle data.
    
    Args:
        candles: List of Candle objects
        window: Window size for finding pivots (default: 5)
    
    Returns:
        Tuple of (pivot_low, pivot_high) where each point is (timestamp, price)
    """
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    
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
    
    # Separate into support (pivot_low) and resistance (pivot_high) points
    support_points = []
    resistance_points = []
    
    for pivot_type, index, price in pivots:
        if pivot_type == 'support':
            support_points.append((candles[index].timestamp, price))
        else:  # resistance
            resistance_points.append((candles[index].timestamp, price))
    
    # Sort by timestamp
    support_points.sort(key=lambda x: x[0])
    resistance_points.sort(key=lambda x: x[0])
    
    return support_points, resistance_points 