from typing import Dict, Any
from datetime import datetime, timedelta
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position


class MomentumStrategy(TradingStrategy):
    """Momentum-based trading strategy"""
    
    def __init__(self):
        config = StrategyConfig(
            name="Momentum",
            token_id=15153,  # Same token for example
            lookback_periods=20,
            balance_percentage=0.3,  # More conservative
            default_slippage_bps=300,  # Lower slippage
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)
    
    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Momentum buy signal logic.
        
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
        
        if not lookback or not curr or len(lookback) < 10:
            return {'action': 'hold', 'info': 'Insufficient data'}
        
        # Calculate momentum indicators
        # 1. Price momentum (rate of change)
        price_5_periods_ago = lookback[-5].close
        price_momentum = (curr.close - price_5_periods_ago) / price_5_periods_ago * 100
        
        # 2. Volume momentum
        recent_volume_avg = sum(candle.volume for candle in lookback[-5:]) / 5
        older_volume_avg = sum(candle.volume for candle in lookback[-10:-5]) / 5
        volume_momentum = (recent_volume_avg - older_volume_avg) / older_volume_avg * 100
        
        # 3. RSI-like indicator (simplified)
        gains = [max(0, candle.close - candle.open) for candle in lookback[-14:]]
        losses = [max(0, candle.open - candle.close) for candle in lookback[-14:]]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Buy conditions:
        # 1. Positive price momentum (>2%)
        # 2. High volume momentum (>50%)
        # 3. RSI not overbought (<70)
        # 4. Cooldown period passed
        if (price_momentum > 2 and 
            volume_momentum > 50 and 
            rsi < 70):
            
            # Check cooldown period (3 minutes after last exit)
            if last_exit_time is None or (datetime.now() - last_exit_time) > timedelta(minutes=3):
                return {
                    'action': 'buy',
                    'info': f'Price momentum: {price_momentum:.2f}%, Volume momentum: {volume_momentum:.2f}%, RSI: {rsi:.1f}'
                }
        
        return {'action': 'hold', 'info': f'Price momentum: {price_momentum:.2f}%, Volume momentum: {volume_momentum:.2f}%, RSI: {rsi:.1f}'}
    
    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Momentum sell signal logic.
        
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
        
        # Stop loss: Sell if loss is greater than 8% (tighter than Goliath)
        if pnl_pct < -8:
            return {
                'shouldSell': True,
                'reason': 'stop_loss',
                'info': f'Stop loss triggered: {pnl_pct:.2f}% loss'
            }
        
        # Take profit: Sell if profit is greater than 15% (more conservative)
        if pnl_pct > 15:
            return {
                'shouldSell': True,
                'reason': 'take_profit',
                'info': f'Take profit triggered: {pnl_pct:.2f}% gain'
            }
        
        # Time-based exit: Sell if position is held for more than 30 minutes (shorter)
        time_held = datetime.now() - entry_time
        if time_held > timedelta(minutes=30):
            return {
                'shouldSell': True,
                'reason': 'time_exit',
                'info': f'Time-based exit: held for {time_held.total_seconds() / 60:.1f} minutes'
            }
        
        return {'shouldSell': False, 'reason': 'hold', 'info': f'Current PnL: {pnl_pct:.2f}%'} 