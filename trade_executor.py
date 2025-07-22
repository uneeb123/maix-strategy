#!/usr/bin/env python3
"""
Trade Executor - Python version of the TypeScript trading bot
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from prisma import Prisma
from utils.debugger import Debugger
from utils.solana_wallet import get_wallet_for_telegram_chat
from lib.jupiter_client import JupiterClient
from lib.helius_client import HeliusClient
from trading_strategy import trade_strategy, should_sell_position, create_position, Candle

# Configuration constants
TELEGRAM_CHAT_ID = 'dummy_174546'
TOKEN_ID = 15153  # Goliath token ID
SLIPPAGE_BPS = 500  # 5% slippage
LOOP_DELAY_MS = 1000  # 1-second resolution
LOOKBACK = 35  # Need 30+ candles for Goliath strategy
BALANCE_PERCENTAGE = 0.5  # 50% of portfolio per trade
FEE_BUFFER_SOL = 0.01  # Reserve 0.01 SOL for transaction fees
RENT_BUFFER_SOL = 0.002  # Reserve 0.002 SOL for rent costs

# Global state
should_exit = False
is_processing_buy = False  # Flag to prevent race conditions
last_exit_time: Optional[datetime] = None  # Track last exit time for cooldown


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global should_exit
    should_exit = True
    print("\nShutdown signal received. Exiting gracefully...")


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def get_token_meta(prisma: Prisma, token_id: int):
    """Get token metadata from database"""
    return prisma.migratedtoken.find_unique(where={'id': token_id})


async def get_lookback_ohlcv(prisma: Prisma, token_id: int, lookback: int):
    """Get lookback OHLCV data from database"""
    # Fetch lookback+2 candles (for prev, curr, next)
    ohlcv = prisma.tokenohlcv.find_many(
        where={'tokenId': token_id, 'interval': '1s'},
        order=[{'timestamp': 'desc'}],
        take=lookback + 2
    )
    
    if len(ohlcv) < lookback + 2:
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


async def calculate_trade_size(wallet_public_key: str) -> float:
    """Calculate trade size based on wallet balance"""
    helius = HeliusClient()
    balance_lamports = await helius.get_sol_balance(wallet_public_key)
    balance_sol = balance_lamports / 1e9  # Convert lamports to SOL
    
    # Calculate available balance after reserving for fees and rent
    reserved_for_fees = FEE_BUFFER_SOL + RENT_BUFFER_SOL
    available_balance = max(0, balance_sol - reserved_for_fees)
    
    # Use 50% of available balance
    trade_size = available_balance * BALANCE_PERCENTAGE
    
    # Ensure minimum trade size (0.001 SOL)
    min_trade_size = 0.001
    if trade_size < min_trade_size:
        raise ValueError(
            f"Insufficient balance for minimum trade. Available: {available_balance:.4f} SOL, Required: {min_trade_size} SOL"
        )
    
    return trade_size


async def main():
    """Main trading loop"""
    debug = Debugger.getInstance()
    
    # Initialize Prisma client
    prisma = Prisma()
    await prisma.connect()
    
    try:
        # Get wallet
        wallet = get_wallet_for_telegram_chat(prisma, TELEGRAM_CHAT_ID)
        if not wallet:
            debug.error(f'No Solana wallet found for TelegramChat chatId: {TELEGRAM_CHAT_ID}')
            sys.exit(1)
        
        # Get token metadata
        token_meta = await get_token_meta(prisma, TOKEN_ID)
        if not token_meta:
            debug.error(f'No token found for id: {TOKEN_ID}')
            sys.exit(1)
        
        TOKEN_MINT = token_meta.address
        TOKEN_SYMBOL = token_meta.symbol
        
        # Initialize clients
        jupiter = JupiterClient()
        helius = HeliusClient()
        
        debug.info('Starting Goliath trading loop:', {
            'TOKEN_ID': TOKEN_ID,
            'TOKEN_MINT': TOKEN_MINT,
            'TOKEN_SYMBOL': TOKEN_SYMBOL,
            'LOOKBACK': LOOKBACK,
            'BALANCE_PERCENTAGE': f'{BALANCE_PERCENTAGE * 100:.1f}%'
        })
        
        while not should_exit:
            try:
                # 1. Load open position
                existing_position = prisma.position.find_first(
                    where={
                        'walletId': wallet.id,
                        'tokenAddress': TOKEN_MINT,
                        'status': 'OPEN'
                    }
                )
                
                # 2. Get lookback window of OHLCV candles
                candles = await get_lookback_ohlcv(prisma, TOKEN_ID, LOOKBACK)
                if not candles:
                    debug.error('Not enough OHLCV data')
                    await asyncio.sleep(LOOP_DELAY_MS / 1000)
                    continue
                
                lookback_candles = candles[:LOOKBACK]
                curr_candle = candles[LOOKBACK + 1]
                
                # 3. Use strategy to decide
                signal_data = trade_strategy({
                    'lookback': lookback_candles,
                    'curr': curr_candle,
                    'last_exit_time': last_exit_time
                })
                
                # Visual indicator for hold signals
                if signal_data['action'] == 'hold':
                    print('.', end='', flush=True)
                else:
                    print()  # Newline to end the dot sequence
                
                # --- BUY LOGIC ---
                if not existing_position and signal_data['action'] == 'buy' and not is_processing_buy:
                    global is_processing_buy
                    is_processing_buy = True  # Set flag to prevent race conditions
                    
                    debug.info('Goliath buy signal detected:', signal_data['info'])
                    
                    try:
                        # Get current balance for logging
                        balance_lamports = await helius.get_sol_balance(wallet.publicKey)
                        balance_sol = balance_lamports / 1e9
                        
                        # Check if we have minimum balance for any trade
                        min_required_balance = FEE_BUFFER_SOL + RENT_BUFFER_SOL + 0.001  # 0.001 SOL minimum trade
                        if balance_sol < min_required_balance:
                            debug.info('Insufficient balance for any trade:', {
                                'balance': f'{balance_sol:.4f}',
                                'minRequired': f'{min_required_balance:.4f}'
                            })
                            is_processing_buy = False  # Reset flag before returning
                            continue  # Skip this iteration
                        
                        trade_size = await calculate_trade_size(wallet.publicKey)
                        debug.info('Goliath trade size calculated:', {
                            'totalBalance': f'{balance_sol:.4f}',
                            'reservedForFees': f'{FEE_BUFFER_SOL + RENT_BUFFER_SOL:.4f}',
                            'availableBalance': f'{balance_sol - FEE_BUFFER_SOL - RENT_BUFFER_SOL:.4f}',
                            'tradeSize': f'{trade_size:.4f}',
                            'balancePercentage': f'{BALANCE_PERCENTAGE * 100:.1f}%'
                        })
                        
                        # Double-check we have enough balance for the trade + fees
                        total_required = trade_size + FEE_BUFFER_SOL + RENT_BUFFER_SOL
                        if balance_sol < total_required:
                            raise ValueError(
                                f"Insufficient balance for trade. Required: {total_required:.4f} SOL, Available: {balance_sol:.4f} SOL"
                            )
                        
                        start_time = datetime.now()
                        debug.info('Sending Goliath buy transaction...')
                        
                        # Retry mechanism with increasing slippage for volatile tokens
                        buy_result = None
                        slippage_levels = [500, 1000, 2000, 5000]  # 5%, 10%, 20%, 50%
                        last_error = None
                        
                        for slippage_bps in slippage_levels:
                            try:
                                debug.info(f'Attempting buy with {slippage_bps / 100}% slippage...')
                                buy_result = await jupiter.buy_token(
                                    {'publicKey': wallet.publicKey, 'secretKey': wallet.secretKey},
                                    TOKEN_MINT,
                                    trade_size,
                                    slippage_bps
                                )
                                debug.info(f'Buy successful with {slippage_bps / 100}% slippage')
                                break  # Success, exit retry loop
                            except Exception as error:
                                last_error = error
                                debug.info(f'Buy failed with {slippage_bps / 100}% slippage: {str(error)}')
                                if slippage_bps == slippage_levels[-1]:
                                    # This was the last attempt, re-throw the error
                                    raise last_error
                                # Wait a bit before retrying with higher slippage
                                await asyncio.sleep(0.5)
                        
                        if not buy_result:
                            raise ValueError('Buy transaction failed after all retry attempts')
                        
                        end_time = datetime.now()
                        time_taken = (end_time - start_time).total_seconds() * 1000
                        
                        debug.info('Goliath buy transaction confirmed:', {
                            'signature': buy_result['signature'],
                            'tradeSize': f'{trade_size:.4f}',
                            'outputAmount': buy_result['outputAmount'],
                            'timeTakenMs': time_taken,
                            'timeTakenSeconds': f'{time_taken / 1000:.2f}'
                        })
                        
                        # Create position in database
                        prisma.position.create(data={
                            'tokenAddress': TOKEN_MINT,
                            'tokenSymbol': TOKEN_SYMBOL,
                            'walletId': wallet.id,
                            'side': 'BUY',
                            'size': trade_size,  # Store SOL value, not token amount
                            'entryPrice': curr_candle.close,
                            'entryTime': datetime.now(),
                            'status': 'OPEN',
                            'txOpen': buy_result['signature']
                        })
                        
                        debug.info('Goliath position recorded in database with SOL value:', trade_size)
                        
                    except Exception as error:
                        debug.error('Error placing Goliath buy order:', str(error))
                    finally:
                        is_processing_buy = False  # Reset flag regardless of success/failure
                
                # --- SELL LOGIC ---
                elif existing_position:
                    # Create position object with proper structure
                    position = create_position(
                        existing_position.id,
                        existing_position.entryPrice,
                        existing_position.entryTime,
                        existing_position.size
                    )
                    
                    sell_signal = should_sell_position({
                        'position': position,
                        'curr': curr_candle,
                        'entry_price': existing_position.entryPrice,
                        'entry_time': existing_position.entryTime
                    })
                    
                    if sell_signal['shouldSell']:
                        try:
                            # Get actual token balance from wallet
                            token_balances = await helius.get_all_token_balances_for_wallet(wallet.publicKey)
                            token_balance = next(
                                (balance for balance in token_balances if balance['mint'] == TOKEN_MINT),
                                None
                            )
                            actual_token_balance = token_balance['amount'] if token_balance else 0
                            
                            if actual_token_balance <= 0:
                                debug.error('No Goliath tokens to sell. Actual balance:', actual_token_balance)
                                continue
                            
                            debug.info('Selling Goliath tokens:', {
                                'storedPositionSize': existing_position.size,
                                'actualTokenBalance': actual_token_balance,
                                'sellReason': sell_signal['reason'],
                                'sellInfo': sell_signal['info']
                            })
                            
                            start_time = datetime.now()
                            debug.info('Sending Goliath sell transaction...')
                            
                            # Retry mechanism with increasing slippage for volatile tokens
                            signature = None
                            slippage_levels = [500, 1000, 2000, 5000]  # 5%, 10%, 20%, 50%
                            last_error = None
                            
                            for slippage_bps in slippage_levels:
                                try:
                                    debug.info(f'Attempting sell with {slippage_bps / 100}% slippage...')
                                    signature = await jupiter.sell_token(
                                        {'publicKey': wallet.publicKey, 'secretKey': wallet.secretKey},
                                        TOKEN_MINT,
                                        actual_token_balance,
                                        slippage_bps
                                    )
                                    debug.info(f'Sell successful with {slippage_bps / 100}% slippage')
                                    break  # Success, exit retry loop
                                except Exception as error:
                                    last_error = error
                                    debug.info(f'Sell failed with {slippage_bps / 100}% slippage: {str(error)}')
                                    if slippage_bps == slippage_levels[-1]:
                                        # This was the last attempt, re-throw the error
                                        raise last_error
                                    # Wait a bit before retrying with higher slippage
                                    await asyncio.sleep(0.5)
                            
                            if not signature:
                                raise ValueError('Sell transaction failed after all retry attempts')
                            
                            end_time = datetime.now()
                            time_taken = (end_time - start_time).total_seconds() * 1000
                            
                            debug.info('Goliath sell transaction confirmed:', {
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
                            global last_exit_time
                            last_exit_time = datetime.now()
                            
                            debug.info('[GOLIATH EXIT]', {
                                'signature': signature,
                                'price': curr_candle.close,
                                'time': curr_candle.timestamp,
                                'pnl': pnl,
                                'reason': sell_signal['reason'],
                                'info': sell_signal['info']
                            })
                            
                        except Exception as error:
                            debug.error('Error placing Goliath sell order:', str(error))
                
            except Exception as err:
                debug.error('Error in Goliath trading loop:', str(err))
            
            await asyncio.sleep(LOOP_DELAY_MS / 1000)
        
        debug.info('Goliath trading loop exited.')
        
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    asyncio.run(main()) 