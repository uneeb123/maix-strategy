from typing import Dict, Any
from datetime import datetime, timedelta
import pytz
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position

class GoliathStrategy(TradingStrategy):
    """Goliath trading strategy: large-volume, MA-based, with stop loss, take profit, and cooldown."""
    def __init__(self):
        config = StrategyConfig(
            name="Goliath",
            token_id=15156,  # Example token ID, adjust as needed
            lookback_periods=20,
            balance_percentage=0.5,  # 50% of wallet balance
            default_slippage_bps=500,  # 5% slippage
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)

    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lookback = data.get('lookback', [])
        curr = data.get('curr')
        last_exit_time = data.get('last_exit_time')
        if not lookback or not curr or len(lookback) < 20:
            return {'action': 'hold', 'info': 'Insufficient data'}
        ma20 = sum(c.close for c in lookback[-20:]) / 20
        avg_vol = sum(c.volume for c in lookback[-20:]) / 20
        high_vol = curr.volume > 1.5 * avg_vol
        price_above_ma = curr.close > ma20
        cooldown_ok = last_exit_time is None or (datetime.now(pytz.UTC) - last_exit_time) > timedelta(minutes=5)
        if price_above_ma and high_vol and cooldown_ok:
            return {'action': 'buy', 'info': f'Price {curr.close:.6f} > MA20 {ma20:.6f}, High Vol: {curr.volume:.2f} > {1.5*avg_vol:.2f}'}
        return {'action': 'hold', 'info': 'No buy signal'}

    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        position = data.get('position')
        curr = data.get('curr')
        entry_price = data.get('entry_price')
        entry_time = data.get('entry_time')
        if not position or not curr or entry_price is None or entry_time is None:
            return {'shouldSell': False, 'reason': 'Missing data', 'info': ''}
        pnl_pct = ((curr.close - entry_price) / entry_price) * 100
        time_held = datetime.now(pytz.UTC) - entry_time
        if pnl_pct < -10:
            return {'shouldSell': True, 'reason': 'stop_loss', 'info': f'Stop loss: {pnl_pct:.2f}%'}
        if pnl_pct > 20:
            return {'shouldSell': True, 'reason': 'take_profit', 'info': f'Take profit: {pnl_pct:.2f}%'}
        if time_held > timedelta(hours=1):
            return {'shouldSell': True, 'reason': 'time_exit', 'info': f'Time exit: held {time_held.total_seconds()/60:.1f} min'}
        return {'shouldSell': False, 'reason': 'hold', 'info': f'PnL: {pnl_pct:.2f}%'} 