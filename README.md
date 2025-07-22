# Maix Strategy

A Python implementation of a Solana-based trading bot that executes automated trading strategies using Jupiter and Helius APIs. Features a modular strategy architecture that allows easy implementation of new trading strategies.

## Features

- Automated trading on Solana blockchain
- Integration with Jupiter DEX for token swaps
- Real-time market data from Helius
- PostgreSQL database integration with Prisma ORM
- Easy to add new trading strategies

## Prerequisites

- Python 3.8+ (<3.12)
- PostgreSQL database
- Solana wallet with SOL balance
- Helius API key
- Jupiter API access
- Virtual environment (recommended for dependency isolation)

## Installation

1. Clone the repository:

```bash
git clone git@github.com:uneeb123/maix-strategy.git
cd maix-strategy
```

2. Set up a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

# To use a specific python version
python@3.10 -m venv myenv

# Activate virtual environment
source venv/bin/activate

# Verify activation (should show path to venv)
which python  # macOS/Linux
which pip     # Verify pip is also from venv
```

3. Install dependencies:

```bash
# Standard installation
pip install -r requirements.txt

# If you encounter "externally-managed-environment" error, use:
pip3 install -r requirements.txt
```

3. Set up environment variables:

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your actual values
```

4. Set up the database:

```bash
# Generate Prisma client
prisma generate
```

5. Deactivate virtual environment when done:

```bash
deactivate
```

## Usage

**Important**: Make sure your virtual environment is activated before running the bot.

### Running the Trading Bot

The bot features an interactive CLI that guides you through the setup process:

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # macOS/Linux

# Run the interactive trading bot
python3 trade_executor.py
```

### Interactive CLI Features

The CLI will:

1. **Ask for Token ID**: Enter the token ID you want to trade
2. **Strategy Selection**: Choose from available strategies with cursor navigation
   - Use ↑/↓ arrow keys to navigate
   - Press ENTER to select
   - Press Ctrl+C to exit
3. **Configuration Review**: Shows your selected configuration
4. **Confirmation**: Confirm before starting the trading bot

### Fallback Mode

If cursor navigation is not available in your terminal, the CLI will automatically fall back to a simple numbered selection interface.

### What the Bot Does

1. Connects to the database and loads wallet information
2. Fetches token metadata and OHLCV data
3. Executes the selected trading strategy in a continuous loop
4. Places buy/sell orders based on strategy signals
5. Manages positions with strategy-specific stop-loss and take-profit levels

## Trading Strategies

The bot uses a modular strategy architecture that allows easy implementation of new trading strategies. Each strategy is self-contained and defines its own buy/sell logic and risk management rules.

### Built-in Strategies

#### Goliath Strategy

- **Buy Signal**: Price above 20-period moving average with high volume (>1.5x average)
- **Sell Signals**:
  - Stop loss: 10% loss
  - Take profit: 20% gain
  - Time exit: 1 hour maximum hold time
- **Cooldown**: 5 minutes after exit before next trade

#### Momentum Strategy

- **Buy Signal**: Positive price momentum (>2%), high volume momentum (>50%), RSI < 70
- **Sell Signals**:
  - Stop loss: 8% loss (tighter than Goliath)
  - Take profit: 15% gain (more conservative)
  - Time exit: 30 minutes maximum hold time
- **Cooldown**: 3 minutes after exit before next trade

### Strategy Architecture

Each strategy implements the `TradingStrategy` abstract base class with two main methods:

- `should_buy()`: Determines if a buy signal should be triggered
- `should_sell()`: Determines if an existing position should be sold

The strategy pattern provides:

- **Clean separation** of trading logic from execution
- **Easy testing** of individual strategies
- **Simple extension** for new strategies
- **Configuration isolation** per strategy

## Creating New Strategies

The modular architecture makes it easy to add new trading strategies.

**To add a new strategy:**

1. **Create the Strategy File and Class**

   - Add a new file in the `strategies/` directory named `{name}.py` (e.g., `momentum.py` for a strategy called “Momentum”).
   - Inside, define a class named `{Name}Strategy` (e.g., `MomentumStrategy`) that implements the `TradingStrategy` interface.

2. **Update the Config**

   - Add an entry to `strategies/config.json`:
     ```json
     {
       "name": "Momentum",
       "description": "Captures price momentum."
     }
     ```
   - The `name` field (case-insensitive) must match the filename and class name pattern.

3. **That’s it!**
   - The system will automatically detect and load your new strategy.
   - If the file or class is missing or misnamed, the bot will show a clear error and exit.

**Example:**

- File: `strategies/mycustom.py`
- Class: `MycustomStrategy`
- Config:
  ```json
  {
    "name": "Mycustom",
    "description": "My custom trading strategy."
  }
  ```

### Strategy Development Tips

1. **Start Simple**: Begin with basic indicators like moving averages
2. **Test Thoroughly**: Use historical data to backtest your strategy
3. **Risk Management**: Always implement stop-loss and take-profit
4. **Cooldown Periods**: Add delays between trades to avoid overtrading
5. **Logging**: Use descriptive info messages for debugging
6. **Configuration**: Make parameters configurable through StrategyConfig

### Available Data

Your strategy methods receive the following data:

**Buy Signal Data:**

- `lookback`: List of historical candles (Candle objects)
- `curr`: Current candle (Candle object)
- `last_exit_time`: Last exit time for cooldown logic

**Sell Signal Data:**

- `position`: Position object with entry details
- `curr`: Current candle (Candle object)
- `entry_price`: Original entry price
- `entry_time`: Original entry time

**Candle Object Properties:**

- `timestamp`: Candle timestamp
- `open`, `high`, `low`, `close`: OHLC prices
- `volume`: Trading volume

## Project Structure

```
maix-strategy/
├── trade_executor.py          # Main trading script with interactive CLI
├── requirements.txt           # Python dependencies
├── env.example               # Environment variables template
├── prisma/
│   └── schema.prisma         # Database schema
├── core/                     # Core trading system components
│   ├── __init__.py
│   ├── strategy_interface.py # Abstract base classes and interfaces
│   └── strategy_factory.py   # Strategy factory pattern
├── strategies/               # Concrete strategy implementations
│   ├── __init__.py
│   ├── goliath_strategy.py   # Goliath trading strategy
│   └── momentum_strategy.py  # Momentum trading strategy
├── utils/
│   ├── __init__.py
│   ├── debugger.py           # Logging utility
│   ├── secrets.py            # Environment variable management
│   └── solana_wallet.py      # Wallet management utilities
└── lib/
    ├── __init__.py
    ├── helius_client.py      # Helius API client
    └── jupiter_client.py     # Jupiter DEX client
```

## API Dependencies

### Helius API

- Used for Solana blockchain interactions
- Token metadata and balance queries
- Transaction details

### Jupiter API

- Used for token swaps on Solana
- Quote generation and transaction execution
- Slippage management

## Database Schema

The bot uses PostgreSQL with the following key models:

- `SolanaWallet`: Wallet information
- `TelegramChat`: Telegram chat associations
- `MigratedToken`: Token metadata
- `TokenOHLCV`: Price and volume data
- `Position`: Trading positions

## Error Handling

The bot includes comprehensive error handling:

- Network request retries
- Transaction failure recovery
- Database connection management
- Graceful shutdown on signals

## Monitoring

The bot provides detailed logging through the Debugger utility:

- Trade execution details
- Balance and position information
- Error messages and stack traces
- Performance metrics

## Security Considerations

- Store API keys securely in environment variables
- Use dedicated wallets for trading
- Monitor transaction fees and slippage
- Implement proper risk management
- Regular security audits

## Troubleshooting

### Externally-Managed-Environment Error

If you encounter the "externally-managed-environment" error on macOS with Python 3.11+, try these solutions:

1. **Use pip3 instead of pip:**

   ```bash
   pip3 install -r requirements.txt
   ```

2. **Recreate the virtual environment:**

   ```bash
   # Deactivate current venv
   deactivate

   # Remove old venv
   rm -rf venv

   # Create new venv with python3
   python3 -m venv venv

   # Activate and install
   source venv/bin/activate
   pip3 install -r requirements.txt
   ```

3. **Verify virtual environment is properly activated:**
   ```bash
   which python
   which pip
   # Both should point to your venv directory
   ```

### Other Common Issues

- **Permission errors**: Use `sudo` only as a last resort, prefer virtual environments
- **Missing dependencies**: Ensure all system-level dependencies are installed
- **Database connection issues**: Verify PostgreSQL is running and credentials are correct
- **Environment variables not found**: Make sure you've copied `env.example` to `.env` and updated the values
- **API key errors**: Verify your Helius and Jupiter API keys are correct and have proper permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License - see the LICENSE file for details.

**Important**: This software is for educational and research purposes only. Commercial use is not permitted under this license.

## Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk and never invest more than you can afford to lose.

**License Notice**: This project is licensed under Creative Commons Attribution-NonCommercial 4.0 International License. Commercial use is not permitted. For commercial licensing inquiries, please contact Prysma Labs.
