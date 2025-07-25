from typing import List, Tuple

from tests.helper.load_data import load_sample_candles

def fractal_strategy(highs: List[float], lows: List[float], window: int = 5) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    """
    Fractal analysis - Bill Williams' method for finding turning points
    """
    fractal_highs = []
    fractal_lows = []
    
    for i in range(window, len(highs) - window):
        # Fractal High (sell signal)
        is_fractal_high = True
        for j in range(i - window, i + window + 1):
            if j != i and highs[j] >= highs[i]:
                is_fractal_high = False
                break
        
        if is_fractal_high:
            fractal_highs.append((i, highs[i]))
        
        # Fractal Low (buy signal)
        is_fractal_low = True
        for j in range(i - window, i + window + 1):
            if j != i and lows[j] <= lows[i]:
                is_fractal_low = False
                break
        
        if is_fractal_low:
            fractal_lows.append((i, lows[i]))
    
    return fractal_highs, fractal_lows

def find_fractals(candles: List, window: int = 5) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find fractal points in candle data.
    
    Args:
        candles: List of Candle objects
        window: Window size for finding fractals (default: 5)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    
    # Find all fractal points
    fractal_highs, fractal_lows = fractal_strategy(highs, lows, window)
    
    # Convert to timestamp-based points
    buy_points = []
    sell_points = []
    
    for index, price in fractal_lows:
        if index < len(candles):
            buy_points.append((candles[index].timestamp, price, index))
    
    for index, price in fractal_highs:
        if index < len(candles):
            sell_points.append((candles[index].timestamp, price, index))
    
    # Sort by timestamp
    buy_points.sort(key=lambda x: x[0])
    sell_points.sort(key=lambda x: x[0])
    
    # Convert to final format
    buy_points = [(point[0], point[1]) for point in buy_points]
    sell_points = [(point[0], point[1]) for point in sell_points]
    
    return buy_points, sell_points