#!/usr/bin/env python3
"""
Trade Executor V2 - Abstracted trading bot with strategy pattern
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich import box

from prisma import Prisma
from utils.debugger import Debugger
from utils.solana_wallet import get_wallet_for_telegram_chat
from lib.jupiter_client import JupiterClient
from lib.helius_client import HeliusClient
from core.strategy_factory import StrategyFactory
from core.strategy_interface import Candle, StrategyConfig
from core.backtest import run_backtest

import os
import importlib
import json
from pathlib import Path

# Initialize Rich console
console = Console()

# Global signal handler will be set up in main() to avoid conflicts with TradeExecutor


class TradeExecutor:
    """Generic trade executor that works with any strategy"""
    
    def __init__(self, strategy_name: str, token_id: int):
        self.strategy = StrategyFactory.create_strategy(strategy_name)
        # Override the strategy's token_id with the user's choice
        self.config = StrategyConfig(
            name=self.strategy.get_config().name,
            token_id=token_id,
            lookback_periods=self.strategy.get_config().lookback_periods,
            balance_percentage=self.strategy.get_config().balance_percentage,
            default_slippage_bps=self.strategy.get_config().default_slippage_bps,
            min_trade_size_sol=self.strategy.get_config().min_trade_size_sol,
            fee_buffer_sol=self.strategy.get_config().fee_buffer_sol,
            rent_buffer_sol=self.strategy.get_config().rent_buffer_sol,
            loop_delay_ms=self.strategy.get_config().loop_delay_ms
        )
        self.telegram_chat_id = 'dummy_174546'  # Hardcoded value
        
        # Global state
        self.should_exit = False
        self.is_processing_buy = False
        self.last_exit_time: Optional[datetime] = None
        
        # Initialize clients
        self.jupiter = JupiterClient()
        self.helius = HeliusClient()
        self.debug = Debugger.getInstance()
        
        # Register signal handlers for trading loop
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.should_exit = True
        print("\nShutdown signal received. Exiting gracefully...")
    
    async def get_token_meta(self, prisma: Prisma):
        """Get token metadata from database"""
        return prisma.migratedtoken.find_unique(where={'id': self.config.token_id})
    
    async def get_lookback_ohlcv(self, prisma: Prisma):
        """Get lookback OHLCV data from database"""
        # Fetch lookback+2 candles (for prev, curr, next)
        ohlcv = prisma.tokenohlcv.find_many(
            where={'tokenId': self.config.token_id, 'interval': '1s'},
            order=[{'timestamp': 'desc'}],
            take=self.config.lookback_periods + 2
        )
        
        if len(ohlcv) < self.config.lookback_periods + 2:
            return None
        
        # Return in ascending order (oldest first)
        ohlcv.reverse()
        return [
            Candle(
                timestamp=row.timestamp,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volumeUSD
            )
            for row in ohlcv
        ]
    
    async def calculate_trade_size(self, wallet_public_key: str) -> float:
        """Calculate trade size based on wallet balance"""
        balance_lamports = await self.helius.get_sol_balance(wallet_public_key)
        balance_sol = balance_lamports / 1e9  # Convert lamports to SOL
        
        # Calculate available balance after reserving for fees and rent
        reserved_for_fees = self.config.fee_buffer_sol + self.config.rent_buffer_sol
        available_balance = max(0, balance_sol - reserved_for_fees)
        
        # Use configured percentage of available balance
        trade_size = available_balance * self.config.balance_percentage
        
        # Ensure minimum trade size
        if trade_size < self.config.min_trade_size_sol:
            raise ValueError(
                f"Insufficient balance for minimum trade. Available: {available_balance:.4f} SOL, Required: {self.config.min_trade_size_sol} SOL"
            )
        
        return trade_size
    
    async def execute_buy(self, wallet, token_mint: str, trade_size: float):
        """Execute buy transaction with retry logic"""
        slippage_levels = [self.config.default_slippage_bps, 1000, 2000, 5000]  # 5%, 10%, 20%, 50%
        last_error = None
        
        for slippage_bps in slippage_levels:
            try:
                self.debug.info(f'Attempting buy with {slippage_bps / 100}% slippage...')
                buy_result = await self.jupiter.buy_token(
                    {'publicKey': wallet.publicKey, 'secretKey': wallet.secretKey},
                    token_mint,
                    trade_size,
                    slippage_bps
                )
                self.debug.info(f'Buy successful with {slippage_bps / 100}% slippage')
                return buy_result
            except Exception as error:
                last_error = error
                self.debug.info(f'Buy failed with {slippage_bps / 100}% slippage: {str(error)}')
                if slippage_bps == slippage_levels[-1]:
                    raise last_error
                await asyncio.sleep(0.5)
        
        raise ValueError('Buy transaction failed after all retry attempts')
    
    async def execute_sell(self, wallet, token_mint: str, token_balance: float):
        """Execute sell transaction with retry logic"""
        slippage_levels = [self.config.default_slippage_bps, 1000, 2000, 5000]  # 5%, 10%, 20%, 50%
        last_error = None
        
        for slippage_bps in slippage_levels:
            try:
                self.debug.info(f'Attempting sell with {slippage_bps / 100}% slippage...')
                signature = await self.jupiter.sell_token(
                    {'publicKey': wallet.publicKey, 'secretKey': wallet.secretKey},
                    token_mint,
                    token_balance,
                    slippage_bps
                )
                self.debug.info(f'Sell successful with {slippage_bps / 100}% slippage')
                return signature
            except Exception as error:
                last_error = error
                self.debug.info(f'Sell failed with {slippage_bps / 100}% slippage: {str(error)}')
                if slippage_bps == slippage_levels[-1]:
                    raise last_error
                await asyncio.sleep(0.5)
        
        raise ValueError('Sell transaction failed after all retry attempts')
    
    async def run(self):
        """Main trading loop"""
        # Initialize Prisma client
        prisma = Prisma()
        await prisma.connect()
        
        try:
            # Get wallet
            wallet = get_wallet_for_telegram_chat(prisma, self.telegram_chat_id)
            if not wallet:
                self.debug.error(f'No Solana wallet found for TelegramChat chatId: {self.telegram_chat_id}')
                sys.exit(1)
            
            # Get token metadata
            token_meta = await self.get_token_meta(prisma)
            if not token_meta:
                self.debug.error(f'No token found for id: {self.config.token_id}')
                sys.exit(1)
            
            token_mint = token_meta.address
            token_symbol = token_meta.symbol
            
            self.debug.info(f'Starting {self.config.name} trading loop:', {
                'TOKEN_ID': self.config.token_id,
                'TOKEN_MINT': token_mint,
                'TOKEN_SYMBOL': token_symbol,
                'LOOKBACK': self.config.lookback_periods,
                'BALANCE_PERCENTAGE': f'{self.config.balance_percentage * 100:.1f}%'
            })
            
            while not self.should_exit:
                try:
                    # 1. Load open position
                    existing_position = prisma.position.find_first(
                        where={
                            'walletId': wallet.id,
                            'tokenAddress': token_mint,
                            'status': 'OPEN'
                        }
                    )
                    
                    # 2. Get lookback window of OHLCV candles
                    candles = await self.get_lookback_ohlcv(prisma)
                    if not candles:
                        self.debug.error('Not enough OHLCV data')
                        await asyncio.sleep(self.config.loop_delay_ms / 1000)
                        continue
                    
                    lookback_candles = candles[:self.config.lookback_periods]
                    curr_candle = candles[self.config.lookback_periods + 1]
                    
                    # 3. Use strategy to decide
                    signal_data = self.strategy.should_buy({
                        'lookback': lookback_candles,
                        'curr': curr_candle,
                        'last_exit_time': self.last_exit_time
                    })
                    
                    # Visual indicator for hold signals
                    if signal_data['action'] == 'hold':
                        console.print('.', end='', style="dim")
                    else:
                        console.print()  # Newline to end the dot sequence
                    
                    # --- BUY LOGIC ---
                    if not existing_position and signal_data['action'] == 'buy' and not self.is_processing_buy:
                        self.is_processing_buy = True
                        
                        self.debug.info(f'{self.config.name} buy signal detected:', signal_data['info'])
                        
                        try:
                            # Get current balance for logging
                            balance_lamports = await self.helius.get_sol_balance(wallet.publicKey)
                            balance_sol = balance_lamports / 1e9
                            
                            # Check if we have minimum balance for any trade
                            min_required_balance = self.config.fee_buffer_sol + self.config.rent_buffer_sol + self.config.min_trade_size_sol
                            if balance_sol < min_required_balance:
                                self.debug.info('Insufficient balance for any trade:', {
                                    'balance': f'{balance_sol:.4f}',
                                    'minRequired': f'{min_required_balance:.4f}'
                                })
                                continue
                            
                            trade_size = await self.calculate_trade_size(wallet.publicKey)
                            self.debug.info(f'{self.config.name} trade size calculated:', {
                                'totalBalance': f'{balance_sol:.4f}',
                                'reservedForFees': f'{self.config.fee_buffer_sol + self.config.rent_buffer_sol:.4f}',
                                'availableBalance': f'{balance_sol - self.config.fee_buffer_sol - self.config.rent_buffer_sol:.4f}',
                                'tradeSize': f'{trade_size:.4f}',
                                'balancePercentage': f'{self.config.balance_percentage * 100:.1f}%'
                            })
                            
                            # Double-check we have enough balance for the trade + fees
                            total_required = trade_size + self.config.fee_buffer_sol + self.config.rent_buffer_sol
                            if balance_sol < total_required:
                                raise ValueError(
                                    f"Insufficient balance for trade. Required: {total_required:.4f} SOL, Available: {balance_sol:.4f} SOL"
                                )
                            
                            start_time = datetime.now()
                            self.debug.info(f'Sending {self.config.name} buy transaction...')
                            
                            buy_result = await self.execute_buy(wallet, token_mint, trade_size)
                            
                            end_time = datetime.now()
                            time_taken = (end_time - start_time).total_seconds() * 1000
                            
                            self.debug.info(f'{self.config.name} buy transaction confirmed:', {
                                'signature': buy_result['signature'],
                                'tradeSize': f'{trade_size:.4f}',
                                'outputAmount': buy_result['outputAmount'],
                                'timeTakenMs': time_taken,
                                'timeTakenSeconds': f'{time_taken / 1000:.2f}'
                            })
                            
                            # Create position in database
                            prisma.position.create(data={
                                'tokenAddress': token_mint,
                                'tokenSymbol': token_symbol,
                                'walletId': wallet.id,
                                'side': 'BUY',
                                'size': trade_size,
                                'entryPrice': curr_candle.close,
                                'entryTime': datetime.now(),
                                'status': 'OPEN',
                                'txOpen': buy_result['signature']
                            })
                            
                            self.debug.info(f'{self.config.name} position recorded in database with SOL value:', trade_size)
                            
                        except Exception as error:
                            self.debug.error(f'Error placing {self.config.name} buy order:', str(error))
                        finally:
                            self.is_processing_buy = False
                    
                    # --- SELL LOGIC ---
                    elif existing_position:
                        # Create position object with proper structure
                        position = self.strategy.create_position(
                            existing_position.id,
                            existing_position.entryPrice,
                            existing_position.entryTime,
                            existing_position.size
                        )
                        
                        sell_signal = self.strategy.should_sell({
                            'position': position,
                            'curr': curr_candle,
                            'entry_price': existing_position.entryPrice,
                            'entry_time': existing_position.entryTime
                        })
                        
                        if sell_signal['shouldSell']:
                            try:
                                # Get actual token balance from wallet
                                token_balances = await self.helius.get_all_token_balances_for_wallet(wallet.publicKey)
                                token_balance = next(
                                    (balance for balance in token_balances if balance['mint'] == token_mint),
                                    None
                                )
                                actual_token_balance = token_balance['amount'] if token_balance else 0
                                
                                if actual_token_balance <= 0:
                                    self.debug.error(f'No {self.config.name} tokens to sell. Actual balance:', actual_token_balance)
                                    continue
                                
                                self.debug.info(f'Selling {self.config.name} tokens:', {
                                    'storedPositionSize': existing_position.size,
                                    'actualTokenBalance': actual_token_balance,
                                    'sellReason': sell_signal['reason'],
                                    'sellInfo': sell_signal['info']
                                })
                                
                                start_time = datetime.now()
                                self.debug.info(f'Sending {self.config.name} sell transaction...')
                                
                                signature = await self.execute_sell(wallet, token_mint, actual_token_balance)
                                
                                end_time = datetime.now()
                                time_taken = (end_time - start_time).total_seconds() * 1000
                                
                                self.debug.info(f'{self.config.name} sell transaction confirmed:', {
                                    'signature': signature,
                                    'size': actual_token_balance,
                                    'timeTakenMs': time_taken,
                                    'timeTakenSeconds': f'{time_taken / 1000:.2f}'
                                })
                                
                                # Calculate PnL and update position
                                pnl = (curr_candle.close - existing_position.entryPrice) * existing_position.size
                                prisma.position.update(
                                    where={'id': existing_position.id},
                                    data={
                                        'exitPrice': curr_candle.close,
                                        'exitTime': datetime.now(),
                                        'status': 'CLOSED',
                                        'pnl': pnl,
                                        'txClose': signature
                                    }
                                )
                                
                                # Update last exit time for cooldown
                                self.last_exit_time = datetime.now()
                                
                                self.debug.info(f'[{self.config.name.upper()} EXIT]', {
                                    'signature': signature,
                                    'price': curr_candle.close,
                                    'time': curr_candle.timestamp,
                                    'pnl': pnl,
                                    'reason': sell_signal['reason'],
                                    'info': sell_signal['info']
                                })
                                
                            except Exception as error:
                                self.debug.error(f'Error placing {self.config.name} sell order:', str(error))
                
                except Exception as err:
                    self.debug.error(f'Error in {self.config.name} trading loop:', str(err))
                
                await asyncio.sleep(self.config.loop_delay_ms / 1000)
            
            self.debug.info(f'{self.config.name} trading loop exited.')
        
        finally:
            await prisma.disconnect()


def get_token_id() -> int:
    """Get token ID from user input with Rich UI and database validation"""
    # Initialize Prisma client for validation
    prisma = Prisma()
    prisma.connect()
    
    try:
        while True:
            try:
                token_id = Prompt.ask(
                    "\n[bold cyan]Enter the token ID to trade[/bold cyan]",
                    default="15156"
                )
                token_id_int = int(token_id)
                
                # Validate token exists in database
                token_meta = prisma.migratedtoken.find_unique(where={'id': token_id_int})
                if not token_meta:
                    console.print(f"❌ [red]Token ID {token_id_int} not found in database. Please enter a valid token ID.[/red]")
                    continue
                
                # Display token info for confirmation
                console.print(f"✅ [green]Token found: {token_meta.symbol} ({token_meta.name})[/green]")
                return token_id_int
                
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
    finally:
        prisma.disconnect()

def select_strategy() -> str:
    """Interactive strategy selection with Rich UI"""
    strategies = StrategyFactory.list_strategies()
    
    # Create strategy selection table
    table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Strategy", style="bold green", width=15)
    table.add_column("Description", style="white", width=25)
    table.add_column("Lookback", style="yellow", width=10)
    table.add_column("Balance", style="blue", width=12)
    table.add_column("Slippage", style="red", width=10)
    
    strategy_names = []
    for strategy_info in strategies:
        strategy_name = strategy_info['name'].lower()
        strategy_names.append(strategy_name)
        config = StrategyFactory.get_strategy_config(strategy_name)
        table.add_row(
            f"[bold]{strategy_info['name'].upper()}[/bold]",
            strategy_info['description'],
            f"{config.lookback_periods} periods",
            f"{config.balance_percentage * 100:.1f}%",
            f"{config.default_slippage_bps / 100}%"
        )
    
    console.print(table)
    
    # Get user selection
    while True:
        try:
            choice = Prompt.ask(
                "\n[bold cyan]Select strategy[/bold cyan]",
                choices=strategy_names,
                default=strategy_names[0]
            )
            return choice
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)
    


def simple_strategy_selection() -> str:
    """Fallback simple strategy selection with Rich UI"""
    strategies = StrategyFactory.list_strategies()
    
    # Create numbered strategy list
    table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="bold yellow", width=5)
    table.add_column("Strategy", style="bold green", width=15)
    table.add_column("Description", style="white", width=25)
    table.add_column("Lookback", style="yellow", width=10)
    table.add_column("Balance", style="blue", width=12)
    table.add_column("Slippage", style="red", width=10)
    
    strategy_names = []
    for i, strategy_info in enumerate(strategies, 1):
        strategy_name = strategy_info['name'].lower()
        strategy_names.append(strategy_name)
        config = StrategyFactory.get_strategy_config(strategy_name)
        table.add_row(
            str(i),
            f"[bold]{strategy_info['name'].upper()}[/bold]",
            strategy_info['description'],
            f"{config.lookback_periods} periods",
            f"{config.balance_percentage * 100:.1f}%",
            f"{config.default_slippage_bps / 100}%"
        )
    
    console.print(table)
    
    while True:
        try:
            choice = Prompt.ask(
                f"\n[bold cyan]Enter your choice[/bold cyan] (1-{len(strategies)})",
                default="1"
            )
            choice_num = int(choice)
            if 1 <= choice_num <= len(strategies):
                return strategy_names[choice_num - 1]
            else:
                console.print(f"❌ [red]Please enter a number between 1 and {len(strategies)}[/red]")
        except ValueError:
            console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)


def select_mode() -> str:
    """Select between backtest and auto-trade modes"""
    console.print("\n[bold cyan]Select Mode:[/bold cyan]")
    
    mode_table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    mode_table.add_column("Mode", style="bold green", width=15)
    mode_table.add_column("Description", style="white", width=40)
    
    mode_table.add_row(
        "[bold]BACKTEST[/bold]",
        "Test strategy on historical data with analysis and plots"
    )
    mode_table.add_row(
        "[bold]AUTO-TRADE[/bold]",
        "Run live trading bot with real-time execution"
    )
    
    console.print(mode_table)
    
    while True:
        try:
            choice = Prompt.ask(
                "\n[bold cyan]Select mode[/bold cyan]",
                choices=["backtest", "auto-trade"],
                default="backtest"
            )
            return choice
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)




def validate_strategies_config():
    """Validate that all strategies in config.json exist as files and classes."""
    config_path = Path(__file__).parent / 'strategies' / 'config.json'
    strategies_dir = Path(__file__).parent / 'strategies'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading config.json: {e}[/red]")
        sys.exit(1)
    errors = []
    for entry in config:
        name = entry.get('name')
        if not name:
            errors.append("Missing 'name' in config entry.")
            continue
        file_path = strategies_dir / f"{name.lower()}.py"
        if not file_path.exists():
            errors.append(f"Missing file: {file_path}")
            continue
        try:
            module = importlib.import_module(f"strategies.{name.lower()}")
            class_name = f"{name}Strategy"
            getattr(module, class_name)
        except Exception as e:
            errors.append(f"Missing or invalid class {class_name} in {file_path}: {e}")
    if errors:
        console.print("[red]Strategy config is ill-formed:[/red]")
        for err in errors:
            console.print(f"[red]- {err}[/red]")
        sys.exit(1)

async def main():
    """Main entry point with interactive CLI"""
    # Set up global signal handler for graceful shutdown
    def global_signal_handler(signum, frame):
        console.print("\n\n👋 [yellow]Graceful shutdown requested. Exiting...[/yellow]")
        sys.exit(0)
    
    # Register global signal handlers (will be overridden by TradeExecutor when needed)
    signal.signal(signal.SIGINT, global_signal_handler)
    signal.signal(signal.SIGTERM, global_signal_handler)
    
    validate_strategies_config()
    
    while True:
        try:
            # Beautiful ASCII art header
            header = Panel(
                Align.center(
                    Text("███╗   ███╗ █████╗ ██╗██╗  ██╗", style="bold cyan") + "\n" +
                    Text("████╗ ████║██╔══██╗██║╚██╗██╔╝", style="bold cyan") + "\n" +
                    Text("██╔████╔██║███████║██║ ╚███╔╝ ", style="bold cyan") + "\n" +
                    Text("██║╚██╔╝██║██╔══██║██║ ██╔██╗ ", style="bold cyan") + "\n" +
                    Text("██║ ╚═╝ ██║██║  ██║██║██╔╝ ██╗", style="bold cyan") + "\n" +
                    Text("╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝", style="bold cyan") + "\n\n" +
                    Text("    Algorithmic Trading Platform", style="bold white"),
                    vertical="middle"
                ),
                box=box.DOUBLE,
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(header)
            
            # Get token ID
            token_id = get_token_id()
            
            while True:
                # Get strategy selection
                try:
                    strategy_name = select_strategy()
                except (ImportError, OSError):
                    # Fallback to simple selection if cursor navigation fails
                    console.print("⚠️  [yellow]Cursor navigation not available, using simple selection...[/yellow]")
                    strategy_name = simple_strategy_selection()
                
                # Display final configuration in a beautiful table
                config = StrategyFactory.get_strategy_config(strategy_name)
                
                config_table = Table(
                    show_header=True,
                    header_style="bold cyan"
                )
                
                config_table.add_column("Parameter", style="bold white", width=15)
                config_table.add_column("Value", style="green", width=20)
                
                config_table.add_row("Token ID", str(token_id))
                config_table.add_row("Strategy", f"[bold]{strategy_name.upper()}[/bold]")
                config_table.add_row("Lookback", f"{config.lookback_periods} periods")
                config_table.add_row("Balance", f"{config.balance_percentage * 100:.1f}%")
                config_table.add_row("Slippage", f"{config.default_slippage_bps / 100}%")
                config_table.add_row("Min Trade", f"{config.min_trade_size_sol} SOL")
                config_table.add_row("Fee Buffer", f"{config.fee_buffer_sol} SOL")
                
                console.print(config_table)
                
                # Select mode
                mode = select_mode()
                
                if mode == "backtest":
                    # Run backtest with all available data
                    try:
                        run_backtest(strategy_name, token_id)
                        
                        # Ask if user wants to try another strategy or exit
                        if Confirm.ask("\n🔄 [bold cyan]Try another strategy?[/bold cyan]"):
                            console.print("\n" + "="*80 + "\n")
                            continue  # Go back to strategy selection, same token_id
                        else:
                            console.print("👋 [yellow]Exiting...[/yellow]")
                            sys.exit(0)
                            
                    except Exception as e:
                        console.print(f"[red]Backtest failed: {str(e)}[/red]")
                        if Confirm.ask("\n🔄 [bold cyan]Try again?[/bold cyan]"):
                            continue
                        else:
                            console.print("👋 [yellow]Exiting...[/yellow]")
                            sys.exit(0)
                
                elif mode == "auto-trade":
                    # Confirm before starting auto-trade
                    if Confirm.ask("\n🚀 [bold cyan]Start auto-trading?[/bold cyan]"):
                        console.print("\n🔄 [bold green]Starting trading bot...[/bold green]")
                        executor = TradeExecutor(strategy_name, token_id)
                        await executor.run()
                        
                        # After auto-trade ends, ask if user wants to try another strategy
                        if Confirm.ask("\n🔄 [bold cyan]Try another strategy?[/bold cyan]"):
                            console.print("\n" + "="*80 + "\n")
                            continue  # Go back to strategy selection, same token_id
                        else:
                            console.print("👋 [yellow]Exiting...[/yellow]")
                            sys.exit(0)
                    else:
                        console.print("👋 [yellow]Exiting...[/yellow]")
                        sys.exit(0)
                
        except KeyboardInterrupt:
            console.print("\n\n👋 [yellow]Graceful shutdown requested. Exiting...[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
            if Confirm.ask("\n🔄 [bold cyan]Try again?[/bold cyan]"):
                console.print("\n" + "="*80 + "\n")
                continue
            else:
                console.print("👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main()) 