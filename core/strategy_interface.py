from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Position:
    id: int
    entry_price: float
    entry_time: datetime
    size: float


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    name: str
    token_id: int
    lookback_periods: int
    balance_percentage: float
    default_slippage_bps: int
    min_trade_size_sol: float
    fee_buffer_sol: float
    rent_buffer_sol: float
    loop_delay_ms: int


class TradingStrategy(ABC):
    """Abstract base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
    
    @abstractmethod
    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if a buy signal should be triggered.
        
        Args:
            data: Dictionary containing:
                - lookback: List of historical candles
                - curr: Current candle
                - last_exit_time: Last exit time for cooldown
        
        Returns:
            Dictionary with 'action' ('buy', 'hold') and 'info'
        """
        pass
    
    @abstractmethod
    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if a position should be sold.
        
        Args:
            data: Dictionary containing:
                - position: Position object
                - curr: Current candle
                - entry_price: Entry price
                - entry_time: Entry time
        
        Returns:
            Dictionary with 'shouldSell' (bool), 'reason' (str), and 'info' (str)
        """
        pass
    
    def get_config(self) -> StrategyConfig:
        """Get the strategy configuration"""
        return self.config
    
    def create_position(self, position_id: int, entry_price: float, entry_time: datetime, size: float) -> Position:
        """Create a position object."""
        return Position(
            id=position_id,
            entry_price=entry_price,
            entry_time=entry_time,
            size=size
        ) 