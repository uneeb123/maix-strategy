from typing import List, Tuple
from core.strategy_interface import Candle

def calculate_ema(candles: List[Candle], period: int = 20) -> List[Tuple[int, float]]:
    """
    Calculate Exponential Moving Average (EMA) for given candles.
    
    Args:
        candles: List of Candle objects
        period: EMA period (default: 20)
    
    Returns:
        List of tuples (timestamp, ema_value)
    """
    if len(candles) < period:
        return []
    
    ema_values = []
    multiplier = 2 / (period + 1)
    
    # Calculate SMA for the first period values
    sma = sum(c.close for c in candles[:period]) / period
    ema_values.append((candles[period-1].timestamp, sma))
    
    # Calculate EMA for remaining values
    for i in range(period, len(candles)):
        current_close = candles[i].close
        prev_ema = ema_values[-1][1]
        ema = (current_close * multiplier) + (prev_ema * (1 - multiplier))
        ema_values.append((candles[i].timestamp, ema))
    
    return ema_values 