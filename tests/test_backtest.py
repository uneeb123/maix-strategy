import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from core.backtest import Backtester, BacktestResult, BacktestPosition, Candle

class DummyStrategy:
    def get_config(self):
        class Config:
            name = 'Dummy'
            token_id = 1
            lookback_periods = 3
            balance_percentage = 1.0
            default_slippage_bps = 0
            min_trade_size_sol = 0.01
            fee_buffer_sol = 0.01
            rent_buffer_sol = 0.01
            loop_delay_ms = 0
        return Config()
    def should_buy(self, _):
        return {'action': 'buy'}
    def should_sell(self, _):
        return {'shouldSell': True, 'reason': 'test'}
    def create_position(self, id, entry_price, entry_time, size):
        return BacktestPosition(id, entry_price, entry_time, size=size)

class DummyBacktester(Backtester):
    def __init__(self):
        self.strategy = DummyStrategy()
        self.config = self.strategy.get_config()
        self.initial_capital = 1000.0
        self.current_position = None
        self.positions = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = []
        self.last_exit_time = None
        self.position_id_counter = 1
    def get_historical_data(self, prisma=None):
        now = datetime.now()
        candles = []
        for i in range(10):
            candles.append(Candle(
                timestamp=now + timedelta(seconds=i),
                open=100 + i,
                high=101 + i,
                low=99 + i,
                close=100 + i + (i % 2),
                volume=1000 + 10 * i
            ))
        return candles

def main():
    tester = DummyBacktester()
    candles = tester.get_historical_data()
    positions = [
        BacktestPosition(id=1, entry_price=100, entry_time=candles[0].timestamp, exit_price=102, exit_time=candles[3].timestamp, size=1, pnl=2, exit_reason='test'),
        BacktestPosition(id=2, entry_price=104, entry_time=candles[4].timestamp, exit_price=106, exit_time=candles[7].timestamp, size=1, pnl=2, exit_reason='test')
    ]
    equity_curve = [1000, 1002, 1002, 1004, 1004, 1006, 1006, 1008, 1008, 1010]
    timestamps = [c.timestamp for c in candles]
    result = BacktestResult(
        total_trades=2,
        winning_trades=2,
        losing_trades=0,
        win_rate=1.0,
        total_pnl=4.0,
        avg_pnl_per_trade=2.0,
        max_drawdown=0.0,
        sharpe_ratio=1.0,
        avg_hold_time=timedelta(seconds=3),
        final_capital=1010.0,
        initial_capital=1000.0,
        positions=positions,
        equity_curve=equity_curve,
        timestamps=timestamps
    )
    tester.plot_results(result, candles)
    files = os.listdir('artifacts')
    plot_files = [f for f in files if f.startswith(f"{tester.config.token_id}_{tester.config.name}_") and f.endswith('.png')]
    if plot_files:
        print("Plot created:", os.path.join('artifacts', plot_files[-1]))
    else:
        print("No plot found.")

if __name__ == "__main__":
    main() 