"""
Trading Bot Configuration
Modify these values to customize the trading behavior
"""

import os
from typing import Optional

# Telegram and Token Configuration
TELEGRAM_CHAT_ID = 'dummy_174546'
TOKEN_ID = 15153  # Goliath token ID

# Trading Parameters
SLIPPAGE_BPS = 500  # 5% slippage
LOOP_DELAY_MS = 1000  # 1-second resolution
LOOKBACK = 35  # Need 30+ candles for Goliath strategy

# Risk Management
BALANCE_PERCENTAGE = 0.5  # 50% of portfolio per trade
FEE_BUFFER_SOL = 0.01  # Reserve 0.01 SOL for transaction fees
RENT_BUFFER_SOL = 0.002  # Reserve 0.002 SOL for rent costs

# Strategy Parameters
MIN_TRADE_SIZE_SOL = 0.001  # Minimum trade size in SOL
COOLDOWN_MINUTES = 5  # Cooldown period after exit before next trade
STOP_LOSS_PERCENTAGE = -10.0  # Stop loss at 10% loss
TAKE_PROFIT_PERCENTAGE = 20.0  # Take profit at 20% gain
MAX_HOLD_TIME_HOURS = 1  # Maximum time to hold a position

# Retry Configuration
MAX_RETRY_ATTEMPTS = 4
RETRY_DELAY_SECONDS = 0.5
SLIPPAGE_LEVELS = [500, 1000, 2000, 5000]  # 5%, 10%, 20%, 50%

# Logging Configuration
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = None  # None for console only, or filename for file logging

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
DIRECT_URL = os.getenv('DIRECT_URL')

# API Configuration
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
JUPITER_API_KEY = os.getenv('JUPITER_API_KEY')

# Validation
def validate_config():
    """Validate that all required configuration values are set"""
    required_vars = [
        'DATABASE_URL',
        'DIRECT_URL', 
        'HELIUS_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not globals().get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Validate numeric ranges
    if not (0 < BALANCE_PERCENTAGE <= 1):
        raise ValueError(f"BALANCE_PERCENTAGE must be between 0 and 1, got {BALANCE_PERCENTAGE}")
    
    if SLIPPAGE_BPS <= 0:
        raise ValueError(f"SLIPPAGE_BPS must be positive, got {SLIPPAGE_BPS}")
    
    if LOOP_DELAY_MS <= 0:
        raise ValueError(f"LOOP_DELAY_MS must be positive, got {LOOP_DELAY_MS}")
    
    if LOOKBACK <= 0:
        raise ValueError(f"LOOKBACK must be positive, got {LOOKBACK}")

# Print configuration summary
def print_config_summary():
    """Print a summary of the current configuration"""
    print("=== Trading Bot Configuration ===")
    print(f"Telegram Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"Token ID: {TOKEN_ID}")
    print(f"Slippage: {SLIPPAGE_BPS/100}%")
    print(f"Loop Delay: {LOOP_DELAY_MS}ms")
    print(f"Lookback Period: {LOOKBACK} candles")
    print(f"Balance Percentage: {BALANCE_PERCENTAGE*100}%")
    print(f"Fee Buffer: {FEE_BUFFER_SOL} SOL")
    print(f"Rent Buffer: {RENT_BUFFER_SOL} SOL")
    print(f"Stop Loss: {STOP_LOSS_PERCENTAGE}%")
    print(f"Take Profit: {TAKE_PROFIT_PERCENTAGE}%")
    print(f"Max Hold Time: {MAX_HOLD_TIME_HOURS} hours")
    print(f"Log Level: {LOG_LEVEL}")
    print("================================")

if __name__ == "__main__":
    # Test configuration
    try:
        validate_config()
        print_config_summary()
        print("✓ Configuration is valid")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        exit(1) 