#!/usr/bin/env python3
"""
Executor - Abstracted trading bot with strategy pattern
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from prisma import Prisma
from utils.debugger import Debugger
from utils.solana_wallet import get_wallet_for_telegram_chat
from lib.jupiter_client import JupiterClient
from lib.helius_client import HeliusClient
from core.strategy_factory import StrategyFactory
from core.strategy_interface import Candle, StrategyConfig


# Initialize Rich console
console = Console()

# Global signal handler will be set up in main() to avoid conflicts with Executor


class Executor:
    """Generic trade executor that works with any strategy"""
    
    @staticmethod
    def prompt_for_trade_configs(strategy_name: str) -> dict:
        """Prompt user for trade-specific configurations"""
        config = StrategyFactory.get_strategy_config(strategy_name)
        
        console.print("\n[bold cyan]Trade Configuration:[/bold cyan]")
        console.print("Configure your trading parameters (press Enter to use defaults):")
        
        trade_configs = {}
        
        # Balance percentage
        while True:
            try:
                balance_input = Prompt.ask(
                    f"\n[bold cyan]Balance percentage[/bold cyan] (default: {config.balance_percentage * 100:.1f}%)",
                    default=str(config.balance_percentage * 100)
                )
                balance_pct = float(balance_input) / 100
                if 0 < balance_pct <= 1:
                    trade_configs['balance_percentage'] = balance_pct
                    break
                else:
                    console.print("❌ [red]Balance must be between 0% and 100%[/red]")
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
        
        # Slippage
        while True:
            try:
                slippage_input = Prompt.ask(
                    f"\n[bold cyan]Slippage tolerance[/bold cyan] (default: {config.default_slippage_bps / 100:.2f}%)",
                    default=str(config.default_slippage_bps / 100)
                )
                slippage_pct = float(slippage_input)
                if slippage_pct >= 0:
                    trade_configs['default_slippage_bps'] = slippage_pct * 100
                    break
                else:
                    console.print("❌ [red]Slippage must be 0% or higher[/red]")
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
        
        # Min trade size
        while True:
            try:
                min_trade_input = Prompt.ask(
                    f"\n[bold cyan]Minimum trade size[/bold cyan] (default: {config.min_trade_size_sol} SOL)",
                    default=str(config.min_trade_size_sol)
                )
                min_trade = float(min_trade_input)
                if min_trade > 0:
                    trade_configs['min_trade_size_sol'] = min_trade
                    break
                else:
                    console.print("❌ [red]Minimum trade size must be greater than 0[/red]")
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
        
        # Fee buffer
        while True:
            try:
                fee_buffer_input = Prompt.ask(
                    f"\n[bold cyan]Fee buffer[/bold cyan] (default: {config.fee_buffer_sol} SOL)",
                    default=str(config.fee_buffer_sol)
                )
                fee_buffer = float(fee_buffer_input)
                if fee_buffer >= 0:
                    trade_configs['fee_buffer_sol'] = fee_buffer
                    break
                else:
                    console.print("❌ [red]Fee buffer must be 0 or higher[/red]")
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
        
        return trade_configs
    
    def display_final_config(self):
        """Display the final configuration after trade configs are set"""
        from rich.table import Table
        
        config_table = Table(
            show_header=True,
            header_style="bold cyan"
        )
        
        config_table.add_column("Parameter", style="bold white", width=15)
        config_table.add_column("Value", style="green", width=20)
        
        config_table.add_row("Token ID", str(self.config.token_id))
        config_table.add_row("Strategy", f"[bold]{self.config.name.upper()}[/bold]")
        config_table.add_row("Lookback", f"{self.config.lookback_periods} periods")
        config_table.add_row("Balance", f"{self.config.balance_percentage * 100:.1f}%")
        config_table.add_row("Slippage", f"{self.config.default_slippage_bps / 100:.2f}%")
        config_table.add_row("Min Trade", f"{self.config.min_trade_size_sol} SOL")
        config_table.add_row("Fee Buffer", f"{self.config.fee_buffer_sol} SOL")
        
        console.print("\n[bold cyan]Final Configuration:[/bold cyan]")
        console.print(config_table)
    
    def __init__(self, strategy_name: str, token_id: int, trade_configs: dict = None, prompt_for_configs: bool = False):
        self.strategy = StrategyFactory.create_strategy(strategy_name)
        strategy_config = self.strategy.get_config()
        
        # Prompt for trade configs if requested
        if prompt_for_configs:
            trade_configs = self.prompt_for_trade_configs(strategy_name)
        
        # Use custom trade configs if provided, otherwise use strategy defaults
        if trade_configs:
            balance_percentage = trade_configs.get('balance_percentage', strategy_config.balance_percentage)
            default_slippage_bps = trade_configs.get('default_slippage_bps', strategy_config.default_slippage_bps)
            min_trade_size_sol = trade_configs.get('min_trade_size_sol', strategy_config.min_trade_size_sol)
            fee_buffer_sol = trade_configs.get('fee_buffer_sol', strategy_config.fee_buffer_sol)
        else:
            balance_percentage = strategy_config.balance_percentage
            default_slippage_bps = strategy_config.default_slippage_bps
            min_trade_size_sol = strategy_config.min_trade_size_sol
            fee_buffer_sol = strategy_config.fee_buffer_sol
        
        # Override the strategy's token_id with the user's choice
        self.config = StrategyConfig(
            name=strategy_config.name,
            token_id=token_id,
            lookback_periods=strategy_config.lookback_periods,
            balance_percentage=balance_percentage,
            default_slippage_bps=default_slippage_bps,
            min_trade_size_sol=min_trade_size_sol,
            fee_buffer_sol=fee_buffer_sol,
            rent_buffer_sol=strategy_config.rent_buffer_sol,
            loop_delay_ms=strategy_config.loop_delay_ms
        )
        
        # Display final config if prompted for configs
        if prompt_for_configs:
            self.display_final_config()
            
            # Confirm before starting
            from rich.prompt import Confirm
            if not Confirm.ask("\n🚀 [bold cyan]Start auto-trading with these settings?[/bold cyan]"):
                console.print("👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
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