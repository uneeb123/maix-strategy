from typing import Dict, Any, List
from datetime import datetime, timedelta
import pytz
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position

class Local_ExtremaStrategy(TradingStrategy):
    """Local Extrema trading strategy: buys on local minima, sells on local maxima."""
    
    def __init__(self):
        config = StrategyConfig(
            name="Local_Extrema",
            token_id=15157,  # Example token ID, adjust as needed
            lookback_periods=20,
            balance_percentage=0.3,  # 30% of wallet balance
            default_slippage_bps=300,  # 3% slippage
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)
        self.window_size = 2  # Reduced window size for testing
        self.min_price_change = 0.01  # Reduced minimum price change to 1%

    def _is_local_minima(self, prices: List[float], index: int) -> bool:
        """Check if the price at the given index is a local minimum."""
        if len(prices) < 3:
            return False
        
        current_price = prices[index]
        
        # For edge cases, check if we have enough data
        if index == 0:
            return len(prices) > 1 and current_price <= prices[1]
        elif index == len(prices) - 1:
            return len(prices) > 1 and current_price <= prices[index - 1]
        
        # Check if current price is lower than adjacent prices
        left_price = prices[index - 1]
        right_price = prices[index + 1]
        
        is_min = current_price <= left_price and current_price <= right_price
        
        # Additional check: ensure significant price change
        if is_min:
            avg_adjacent = (left_price + right_price) / 2
            price_change = abs(current_price - avg_adjacent) / avg_adjacent
            return price_change >= self.min_price_change
        
        return False

    def _is_local_maxima(self, prices: List[float], index: int) -> bool:
        """Check if the price at the given index is a local maximum."""
        if len(prices) < 3:
            return False
        
        current_price = prices[index]
        
        # For edge cases, check if we have enough data
        if index == 0:
            return len(prices) > 1 and current_price >= prices[1]
        elif index == len(prices) - 1:
            return len(prices) > 1 and current_price >= prices[index - 1]
        
        # Check if current price is higher than adjacent prices
        left_price = prices[index - 1]
        right_price = prices[index + 1]
        
        is_max = current_price >= left_price and current_price >= right_price
        
        # Additional check: ensure significant price change
        if is_max:
            avg_adjacent = (left_price + right_price) / 2
            price_change = abs(current_price - avg_adjacent) / avg_adjacent
            return price_change >= self.min_price_change
        
        return False

    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lookback = data.get('lookback', [])
        curr = data.get('curr')
        last_exit_time = data.get('last_exit_time')
        
        if not lookback or not curr or len(lookback) < 1:
            return {'action': 'hold', 'info': 'Insufficient data for extrema detection'}
        
        # Extract closing prices
        prices = [c.close for c in lookback] + [curr.close]
        current_index = len(prices) - 1
        
        # Check if current price is a local minimum
        if self._is_local_minima(prices, current_index):
            # Additional check: ensure we're not in a cooldown period
            cooldown_ok = last_exit_time is None or (datetime.now(pytz.UTC) - last_exit_time) > timedelta(minutes=10)
            
            if cooldown_ok:
                return {
                    'action': 'buy', 
                    'info': f'Local minimum detected at {curr.close:.6f}'
                }
            else:
                return {'action': 'hold', 'info': 'In cooldown period after last exit'}
        
        return {'action': 'hold', 'info': 'No local minimum detected'}

    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        position = data.get('position')
        curr = data.get('curr')
        entry_price = data.get('entry_price')
        entry_time = data.get('entry_time')
        lookback = data.get('lookback', [])
        
        if not position or not curr or entry_price is None or entry_time is None:
            return {'shouldSell': False, 'reason': 'Missing data', 'info': ''}
        
        # Check for local maximum
        if lookback and len(lookback) >= 1:
            prices = [c.close for c in lookback] + [curr.close]
            current_index = len(prices) - 1
            
            if self._is_local_maxima(prices, current_index):
                return {
                    'shouldSell': True, 
                    'reason': 'local_maximum', 
                    'info': f'Local maximum detected at {curr.close:.6f}'
                }
        
        # Stop loss check (5% loss)
        pnl_pct = ((curr.close - entry_price) / entry_price) * 100
        if pnl_pct < -5:
            return {
                'shouldSell': True, 
                'reason': 'stop_loss', 
                'info': f'Stop loss triggered: {pnl_pct:.2f}%'
            }
        
        # Take profit check (10% gain)
        if pnl_pct > 10:
            return {
                'shouldSell': True, 
                'reason': 'take_profit', 
                'info': f'Take profit triggered: {pnl_pct:.2f}%'
            }
        
        # Time-based exit (hold for maximum 2 hours)
        time_held = datetime.now(pytz.UTC) - entry_time
        if time_held > timedelta(hours=2):
            return {
                'shouldSell': True, 
                'reason': 'time_exit', 
                'info': f'Time exit: held {time_held.total_seconds()/60:.1f} min'
            }
        
        return {
            'shouldSell': False, 
            'reason': 'hold', 
            'info': f'Holding position, PnL: {pnl_pct:.2f}%'
        } 