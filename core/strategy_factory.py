from typing import Dict, Type
from core.strategy_interface import TradingStrategy
from strategies.goliath_strategy import GoliathStrategy
from strategies.momentum_strategy import MomentumStrategy


class StrategyFactory:
    """Factory for creating trading strategies"""
    
    _strategies: Dict[str, Type[TradingStrategy]] = {
        'goliath': GoliathStrategy,
        'momentum': MomentumStrategy,
    }
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[TradingStrategy]):
        """Register a new strategy"""
        cls._strategies[name] = strategy_class
    
    @classmethod
    def create_strategy(cls, name: str) -> TradingStrategy:
        """Create a strategy instance by name"""
        if name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available strategies: {list(cls._strategies.keys())}")
        
        return cls._strategies[name]()
    
    @classmethod
    def list_strategies(cls) -> list[str]:
        """List all available strategies"""
        return list(cls._strategies.keys())
    
    @classmethod
    def get_strategy_config(cls, name: str):
        """Get strategy configuration without creating instance"""
        strategy = cls.create_strategy(name)
        return strategy.get_config() 