from typing import Dict, Any
from datetime import datetime, timedelta
import pytz
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position
from core.indicators.ema import calculate_ema

class EMA_GradientStrategy(TradingStrategy):
    """EMA Gradient strategy: buys on positive EMA gradient, sells on negative gradient or profit targets."""
    
    def __init__(self):
        config = StrategyConfig(
            name="EMA_Gradient",
            token_id=15156,
            lookback_periods=50,
            balance_percentage=0.4,
            default_slippage_bps=400,
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)
        self.ema_period = 20
        self.gradient_threshold = 0.001  # Minimum gradient to trigger buy

    def _calculate_ema_gradient(self, candles: list) -> float:
        """Calculate the current EMA gradient (rate of change)."""
        if len(candles) < self.ema_period + 2:
            return 0.0
        
        ema_values = calculate_ema(candles, self.ema_period)
        if len(ema_values) < 2:
            return 0.0
        
        # Calculate gradient as (current_ema - previous_ema) / previous_ema
        current_ema = ema_values[-1][1]
        previous_ema = ema_values[-2][1]
        
        if previous_ema == 0:
            return 0.0
        
        gradient = (current_ema - previous_ema) / previous_ema
        return gradient

    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lookback = data.get('lookback', [])
        curr = data.get('curr')
        last_exit_time = data.get('last_exit_time')
        
        if not lookback or not curr or len(lookback) < self.ema_period + 2:
            return {'action': 'hold', 'info': 'Insufficient data for EMA calculation'}
        
        # Add current candle to lookback for EMA calculation
        all_candles = lookback + [curr]
        
        # Calculate EMA gradient
        gradient = self._calculate_ema_gradient(all_candles)
        
        # Check cooldown period
        cooldown_ok = last_exit_time is None or (datetime.now(pytz.UTC) - last_exit_time) > timedelta(minutes=5)
        
        # Buy signal: positive gradient above threshold and cooldown passed
        if gradient > self.gradient_threshold and cooldown_ok:
            return {
                'action': 'buy', 
                'info': f'EMA gradient: {gradient:.4f} (threshold: {self.gradient_threshold})'
            }
        
        return {
            'action': 'hold', 
            'info': f'No buy: EMA gradient {gradient:.4f} (threshold: {self.gradient_threshold})'
        }

    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        position = data.get('position')
        curr = data.get('curr')
        entry_price = data.get('entry_price')
        entry_time = data.get('entry_time')
        lookback = data.get('lookback', [])
        
        if not position or not curr or entry_price is None or entry_time is None:
            return {'shouldSell': False, 'reason': 'Missing data', 'info': ''}
        
        # Calculate PnL
        pnl_pct = ((curr.close - entry_price) / entry_price) * 100
        time_held = datetime.now(pytz.UTC) - entry_time
        
        # Calculate current EMA gradient
        all_candles = lookback + [curr]
        gradient = self._calculate_ema_gradient(all_candles)
        
        # Sell conditions:
        # 1. Stop loss: -5% loss
        if pnl_pct < -5:
            return {
                'shouldSell': True, 
                'reason': 'stop_loss', 
                'info': f'Stop loss: {pnl_pct:.2f}%'
            }
        
        # 2. Take profit: +10% gain
        if pnl_pct > 10:
            return {
                'shouldSell': True, 
                'reason': 'take_profit', 
                'info': f'Take profit: {pnl_pct:.2f}%'
            }
        
        # 3. EMA gradient turned negative
        if gradient < -self.gradient_threshold:
            return {
                'shouldSell': True, 
                'reason': 'ema_gradient_negative', 
                'info': f'EMA gradient negative: {gradient:.4f}'
            }
        
        # 4. Time-based exit: hold for max 45 minutes
        if time_held > timedelta(minutes=45):
            return {
                'shouldSell': True, 
                'reason': 'time_exit', 
                'info': f'Time exit: held {time_held.total_seconds()/60:.1f} min'
            }
        
        return {
            'shouldSell': False, 
            'reason': 'hold', 
            'info': f'PnL: {pnl_pct:.2f}%, EMA gradient: {gradient:.4f}'
        } 