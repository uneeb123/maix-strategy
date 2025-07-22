# Maix Strategy

A Python implementation of a Solana-based trading bot that executes automated trading strategies using Jupiter and Helius APIs.

## Features

- Automated trading on Solana blockchain
- Integration with Jupiter DEX for token swaps
- Real-time market data from Helius
- PostgreSQL database integration with Prisma ORM
- Configurable trading strategies
- Risk management with stop-loss and take-profit
- Retry mechanisms with increasing slippage

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Solana wallet with SOL balance
- Helius API key
- Jupiter API access
- Virtual environment (recommended for dependency isolation)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd maix-strategy
```

2. Set up a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

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
nano .env  # or use your preferred editor
```

The `.env` file should contain:

```env
# Database configuration
DATABASE_URL="postgresql://username:password@localhost:5432/database_name"
DIRECT_URL="postgresql://username:password@localhost:5432/database_name"

# API Keys
HELIUS_API_KEY="your_helius_api_key_here"
JUPITER_API_KEY="your_jupiter_api_key_here"  # Optional for lite API
```

**Important**: Replace the placeholder values with your actual:

- PostgreSQL database credentials
- Helius API key (get from https://dev.helius.xyz/)
- Jupiter API key (get from https://station.jup.ag/)

4. Set up the database:

```bash
# Generate Prisma client
prisma generate
```

5. Deactivate virtual environment when done:

```bash
deactivate
```

## Configuration

The trading bot configuration is managed in `config.py`. Modify this file to customize the trading behavior:

### Trading Parameters

- `TELEGRAM_CHAT_ID`: Telegram chat ID for wallet association
- `TOKEN_ID`: Target token ID for trading
- `SLIPPAGE_BPS`: Slippage tolerance in basis points
- `LOOP_DELAY_MS`: Loop delay in milliseconds
- `LOOKBACK`: Number of candles to look back for strategy
- `BALANCE_PERCENTAGE`: Percentage of wallet balance to use per trade
- `FEE_BUFFER_SOL`: SOL reserved for transaction fees
- `RENT_BUFFER_SOL`: SOL reserved for rent costs

### Risk Management

- `STOP_LOSS_PERCENTAGE`: Stop loss percentage (-10.0 for 10% loss)
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage (20.0 for 20% gain)
- `MAX_HOLD_TIME_HOURS`: Maximum time to hold a position

### Validate Configuration

Test your configuration:

```bash
python config.py
```

## Usage

**Important**: Make sure your virtual environment is activated before running the bot.

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # macOS/Linux

# Run the trading bot
python trade_executor.py
```

The bot will:

1. Connect to the database and load wallet information
2. Fetch token metadata and OHLCV data
3. Execute the trading strategy in a continuous loop
4. Place buy/sell orders based on strategy signals
5. Manage positions with stop-loss and take-profit

## Trading Strategy

The current implementation includes a simplified Goliath strategy that:

- Buys when price is above moving average and volume is high
- Sells on stop-loss (10% loss), take-profit (20% gain), or time-based exit (1 hour)
- Includes cooldown periods between trades

You can customize the strategy by modifying the `trade_strategy.py` file.

## Project Structure

```
maix-strategy/
├── trade_executor.py          # Main trading script
├── trading_strategy.py        # Trading strategy logic
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── env.example               # Environment variables template
├── prisma/
│   └── schema.prisma         # Database schema
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
