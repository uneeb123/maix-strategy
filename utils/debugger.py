import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class Debugger:
    _instance: Optional['Debugger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Debugger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.logger = logging.getLogger('trading_bot')
        self.logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(console_handler)
        
        self._initialized = True
    
    @classmethod
    def getInstance(cls) -> 'Debugger':
        return cls()
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log info message with optional data"""
        if data:
            self.logger.info(f"{message} {data}")
        else:
            self.logger.info(message)
    
    def error(self, message: str, data: Optional[Any] = None):
        """Log error message with optional data"""
        if data:
            self.logger.error(f"{message} {data}")
        else:
            self.logger.error(message)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log warning message with optional data"""
        if data:
            self.logger.warning(f"{message} {data}")
        else:
            self.logger.warning(message)
    
    def debug(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log debug message with optional data"""
        if data:
            self.logger.debug(f"{message} {data}")
        else:
            self.logger.debug(message) 