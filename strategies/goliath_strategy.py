from typing import Dict, Any
from datetime import datetime, timedelta
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position


class GoliathStrategy(TradingStrategy):
    """Goliath trading strategy implementation"""
    
    def __init__(self):
        config = StrategyConfig(
            name="Goliath",
            token_id=15153,
            lookback_periods=35,
            balance_percentage=0.5,
            default_slippage_bps=500,
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)
    
    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Goliath buy signal logic.
        
        Args:
            data: Dictionary containing:
                - lookback: List of historical candles
                - curr: Current candle
                - last_exit_time: Last exit time for cooldown
        
        Returns:
            Dictionary with 'action' ('buy', 'hold') and 'info'
        """
        lookback = data.get('lookback', [])
        curr = data.get('curr')
        last_exit_time = data.get('last_exit_time')
        
        if not lookback or not curr:
            return {'action': 'hold', 'info': 'Insufficient data'}
        
        # Goliath strategy logic
        if len(lookback) >= 20:
            # Calculate 20-period moving average
            ma_20 = sum(candle.close for candle in lookback[-20:]) / 20
            
            # Calculate volume average
            volume_avg = sum(candle.volume for candle in lookback[-20:]) / 20
            
            # Buy signal: price above MA and high volume
            if curr.close > ma_20 and curr.volume > volume_avg * 1.5:
                # Check cooldown period (5 minutes after last exit)
                if last_exit_time is None or (datetime.now() - last_exit_time) > timedelta(minutes=5):
                    return {
                        'action': 'buy',
                        'info': f'Price {curr.close:.6f} above MA {ma_20:.6f}, volume {curr.volume:.2f} vs avg {volume_avg:.2f}'
                    }
        
        return {'action': 'hold', 'info': 'No signal'}
    
    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Goliath sell signal logic.
        
        Args:
            data: Dictionary containing:
                - position: Position object
                - curr: Current candle
                - entry_price: Entry price
                - entry_time: Entry time
        
        Returns:
            Dictionary with 'shouldSell' (bool), 'reason' (str), and 'info' (str)
        """
        position = data.get('position')
        curr = data.get('curr')
        entry_price = data.get('entry_price')
        entry_time = data.get('entry_time')
        
        if not position or not curr or entry_price is None or entry_time is None:
            return {'shouldSell': False, 'reason': 'Missing data', 'info': ''}
        
        # Calculate profit/loss percentage
        pnl_pct = ((curr.close - entry_price) / entry_price) * 100
        
        # Stop loss: Sell if loss is greater than 10%
        if pnl_pct < -10:
            return {
                'shouldSell': True,
                'reason': 'stop_loss',
                'info': f'Stop loss triggered: {pnl_pct:.2f}% loss'
            }
        
        # Take profit: Sell if profit is greater than 20%
        if pnl_pct > 20:
            return {
                'shouldSell': True,
                'reason': 'take_profit',
                'info': f'Take profit triggered: {pnl_pct:.2f}% gain'
            }
        
        # Time-based exit: Sell if position is held for more than 1 hour
        time_held = datetime.now() - entry_time
        if time_held > timedelta(hours=1):
            return {
                'shouldSell': True,
                'reason': 'time_exit',
                'info': f'Time-based exit: held for {time_held.total_seconds() / 60:.1f} minutes'
            }
        
        return {'shouldSell': False, 'reason': 'hold', 'info': f'Current PnL: {pnl_pct:.2f}%'} 