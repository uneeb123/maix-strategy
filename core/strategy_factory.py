import json
import importlib
from pathlib import Path
from typing import Dict, Type
from core.strategy_interface import TradingStrategy

class StrategyFactory:
    """Factory for creating trading strategies"""
    _strategies: Dict[str, Type[TradingStrategy]] = {}
    _config_path = Path(__file__).parent.parent / 'strategies' / 'config.json'
    _initialized = False
    _display_info = {}

    @classmethod
    def _initialize(cls):
        if cls._initialized:
            return
        with open(cls._config_path, 'r') as f:
            config = json.load(f)
        for entry in config:
            name = entry['name']
            description = entry.get('description', '')
            module_name = f"strategies.{name.lower()}"
            class_name = f"{name}Strategy"
            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)
            cls._strategies[name.lower()] = strategy_class
            cls._display_info[name.lower()] = {'name': name, 'description': description}
        cls._initialized = True

    @classmethod
    def register_strategy(cls, name: str, strategy_class: Type[TradingStrategy]):
        cls._initialize()
        cls._strategies[name.lower()] = strategy_class

    @classmethod
    def create_strategy(cls, name: str) -> TradingStrategy:
        cls._initialize()
        key = name.lower()
        if key not in cls._strategies:
            raise ValueError(f"Unknown strategy: {name}. Available strategies: {list(cls._strategies.keys())}")
        return cls._strategies[key]()

    @classmethod
    def list_strategies(cls) -> list[dict]:
        cls._initialize()
        return [cls._display_info[k] for k in cls._strategies.keys()]

    @classmethod
    def get_strategy_config(cls, name: str):
        strategy = cls.create_strategy(name)
        return strategy.get_config() 