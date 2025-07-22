from typing import Dict, Any
from datetime import datetime, timedelta
from core.strategy_interface import TradingStrategy, StrategyConfig, Candle, Position

class MomentumStrategy(TradingStrategy):
    """Momentum trading strategy: price/volume momentum, RSI, with stop loss, take profit, and cooldown."""
    def __init__(self):
        config = StrategyConfig(
            name="Momentum",
            token_id=15156,  # Example token ID, adjust as needed
            lookback_periods=20,
            balance_percentage=0.4,  # 40% of wallet balance
            default_slippage_bps=400,  # 4% slippage
            min_trade_size_sol=0.001,
            fee_buffer_sol=0.01,
            rent_buffer_sol=0.002,
            loop_delay_ms=1000
        )
        super().__init__(config)

    def _calc_rsi(self, closes, period=14):
        if len(closes) < period + 1:
            return 50  # Neutral
        gains = [max(0, closes[i] - closes[i-1]) for i in range(1, period+1)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(1, period+1)]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def should_buy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lookback = data.get('lookback', [])
        curr = data.get('curr')
        last_exit_time = data.get('last_exit_time')
        if not lookback or not curr or len(lookback) < 20:
            return {'action': 'hold', 'info': 'Insufficient data'}
        price_momentum = ((curr.close - lookback[-2].close) / lookback[-2].close) * 100
        avg_vol = sum(c.volume for c in lookback[-20:]) / 20
        vol_momentum = ((curr.volume - avg_vol) / avg_vol) * 100
        closes = [c.close for c in lookback[-15:]] + [curr.close]
        rsi = self._calc_rsi(closes)
        cooldown_ok = last_exit_time is None or (datetime.now() - last_exit_time) > timedelta(minutes=3)
        if price_momentum > 2 and vol_momentum > 50 and rsi < 70 and cooldown_ok:
            return {'action': 'buy', 'info': f'Price momentum: {price_momentum:.2f}%, Vol momentum: {vol_momentum:.2f}%, RSI: {rsi:.1f}'}
        return {'action': 'hold', 'info': f'No buy: Price momentum {price_momentum:.2f}%, Vol momentum {vol_momentum:.2f}%, RSI {rsi:.1f}'}

    def should_sell(self, data: Dict[str, Any]) -> Dict[str, Any]:
        position = data.get('position')
        curr = data.get('curr')
        entry_price = data.get('entry_price')
        entry_time = data.get('entry_time')
        if not position or not curr or entry_price is None or entry_time is None:
            return {'shouldSell': False, 'reason': 'Missing data', 'info': ''}
        pnl_pct = ((curr.close - entry_price) / entry_price) * 100
        time_held = datetime.now() - entry_time
        if pnl_pct < -8:
            return {'shouldSell': True, 'reason': 'stop_loss', 'info': f'Stop loss: {pnl_pct:.2f}%'}
        if pnl_pct > 15:
            return {'shouldSell': True, 'reason': 'take_profit', 'info': f'Take profit: {pnl_pct:.2f}%'}
        if time_held > timedelta(minutes=30):
            return {'shouldSell': True, 'reason': 'time_exit', 'info': f'Time exit: held {time_held.total_seconds()/60:.1f} min'}
        return {'shouldSell': False, 'reason': 'hold', 'info': f'PnL: {pnl_pct:.2f}%'} 