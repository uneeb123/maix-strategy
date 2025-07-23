#!/usr/bin/env python3

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from prisma import Prisma
from core.strategy_interface import Candle, Position, StrategyConfig
from core.strategy_factory import StrategyFactory
from core.plotter import plot_trading_signals
from utils.debugger import Debugger

console = Console()

@dataclass
class BacktestPosition:
    id: int
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    size: float = 1.0
    pnl: Optional[float] = None
    exit_reason: Optional[str] = None

@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    max_drawdown: float
    sharpe_ratio: float
    avg_hold_time: timedelta
    final_capital: float
    initial_capital: float
    positions: List[BacktestPosition]
    equity_curve: List[float]
    timestamps: List[datetime]

class Backtester:
    def __init__(self, strategy_name: str, token_id: int, initial_capital: float = 1000.0):
        self.strategy = StrategyFactory.create_strategy(strategy_name)
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
        self.initial_capital = initial_capital
        self.debug = Debugger.getInstance()
        self.current_position: Optional[BacktestPosition] = None
        self.positions: List[BacktestPosition] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[datetime] = []
        self.last_exit_time: Optional[datetime] = None
        self.position_id_counter = 1

    def get_historical_data(self, prisma: Prisma) -> List[Candle]:
        try:
            ohlcv = prisma.tokenohlcv.find_many(
                where={
                    'tokenId': self.config.token_id,
                    'interval': '1s'
                },
                order=[{'timestamp': 'asc'}]
            )
            if len(ohlcv) < self.config.lookback_periods + 10:
                raise ValueError(f"Insufficient historical data. Need at least {self.config.lookback_periods + 10} candles, got {len(ohlcv)}")
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
        except Exception as e:
            self.debug.error(f"Error fetching historical data: {str(e)}")
            raise

    def should_buy(self, lookback_candles: List[Candle], curr_candle: Candle) -> Dict[str, Any]:
        return self.strategy.should_buy({
            'lookback': lookback_candles,
            'curr': curr_candle,
            'last_exit_time': self.last_exit_time
        })

    def should_sell(self, curr_candle: Candle) -> Dict[str, Any]:
        if not self.current_position:
            return {'shouldSell': False, 'reason': 'No position', 'info': ''}
        position = self.strategy.create_position(
            self.current_position.id,
            self.current_position.entry_price,
            self.current_position.entry_time,
            self.current_position.size
        )
        return self.strategy.should_sell({
            'position': position,
            'curr': curr_candle,
            'entry_price': self.current_position.entry_price,
            'entry_time': self.current_position.entry_time
        })

    def open_position(self, price: float, timestamp: datetime) -> None:
        self.current_position = BacktestPosition(
            id=self.position_id_counter,
            entry_price=price,
            entry_time=timestamp,
            size=1.0
        )
        self.position_id_counter += 1

    def close_position(self, price: float, timestamp: datetime, reason: str) -> None:
        if not self.current_position:
            return
        self.current_position.exit_price = price
        self.current_position.exit_time = timestamp
        self.current_position.exit_reason = reason
        self.current_position.pnl = (price - self.current_position.entry_price) * self.current_position.size
        self.positions.append(self.current_position)
        self.current_position = None
        self.last_exit_time = timestamp

    def update_equity_curve(self, current_price: float, timestamp: datetime) -> None:
        current_equity = self.initial_capital
        for position in self.positions:
            if position.pnl is not None:
                current_equity += position.pnl
        if self.current_position:
            unrealized_pnl = (current_price - self.current_position.entry_price) * self.current_position.size
            current_equity += unrealized_pnl
        self.equity_curve.append(current_equity)
        self.timestamps.append(timestamp)

    def calculate_metrics(self) -> BacktestResult:
        if not self.positions:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_pnl_per_trade=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                avg_hold_time=timedelta(0),
                final_capital=self.initial_capital,
                initial_capital=self.initial_capital,
                positions=[],
                equity_curve=self.equity_curve,
                timestamps=self.timestamps
            )
        total_trades = len(self.positions)
        winning_trades = len([p for p in self.positions if p.pnl and p.pnl > 0])
        losing_trades = len([p for p in self.positions if p.pnl and p.pnl < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        total_pnl = sum(p.pnl for p in self.positions if p.pnl is not None)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        hold_times = []
        for position in self.positions:
            if position.exit_time and position.entry_time:
                hold_time = position.exit_time - position.entry_time
                hold_times.append(hold_time)
        avg_hold_time = sum(hold_times, timedelta(0)) / len(hold_times) if hold_times else timedelta(0)
        max_drawdown = 0.0
        peak = self.initial_capital
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl_per_trade=avg_pnl_per_trade,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            avg_hold_time=avg_hold_time,
            final_capital=final_capital,
            initial_capital=self.initial_capital,
            positions=self.positions,
            equity_curve=self.equity_curve,
            timestamps=self.timestamps
        )

    def run_backtest(self) -> BacktestResult:
        prisma = Prisma()
        try:
            prisma.connect()
            candles = self.get_historical_data(prisma)
            self.debug.info(f"Running backtest on {len(candles)} candles from {candles[0].timestamp} to {candles[-1].timestamp}")
            for i in range(self.config.lookback_periods, len(candles)):
                curr_candle = candles[i]
                lookback_candles = candles[i - self.config.lookback_periods:i]
                self.update_equity_curve(curr_candle.close, curr_candle.timestamp)
                if self.current_position:
                    sell_signal = self.should_sell(curr_candle)
                    if sell_signal['shouldSell']:
                        self.close_position(curr_candle.close, curr_candle.timestamp, sell_signal['reason'])
                elif not self.current_position:
                    buy_signal = self.should_buy(lookback_candles, curr_candle)
                    if buy_signal['action'] == 'buy':
                        self.open_position(curr_candle.close, curr_candle.timestamp)
            if self.current_position:
                self.close_position(candles[-1].close, candles[-1].timestamp, "End of backtest")
                self.update_equity_curve(candles[-1].close, candles[-1].timestamp)
            return self.calculate_metrics()
        except Exception as e:
            self.debug.error(f"Error in backtest: {str(e)}")
            raise
        finally:
            try:
                prisma.disconnect()
            except:
                pass

    def plot_results(self, result: BacktestResult, candles: List[Candle]) -> None:
        if not candles or not result.timestamps:
            console.print("[red]No data to plot[/red]")
            return
        
        # Extract buy and sell points from positions
        buy_points = [(p.entry_time, p.entry_price) for p in result.positions]
        sell_points = [(p.exit_time, p.exit_price) for p in result.positions if p.exit_time and p.exit_price]
        
        # Use the core plotter
        try:
            plot_path = plot_trading_signals(
                candles=candles,
                token_id=self.config.token_id,
                strategy_name=self.config.name.lower().replace(' ', '_'),
                buy_points=buy_points,
                sell_points=sell_points
            )
            console.print(f"[green]Saved backtest plot to {plot_path}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating backtest plot: {e}[/red]")
            raise

    def display_results(self, result: BacktestResult, show_trade_details: bool = False) -> None:
        results_table = Table(
            title=f"{self.config.name} Strategy Backtest Results",
            show_header=True,
            header_style="bold cyan"
        )
        results_table.add_column("Metric", style="bold white", width=20)
        results_table.add_column("Value", style="green", width=20)
        results_table.add_row("Total Trades", str(result.total_trades))
        results_table.add_row("Winning Trades", str(result.winning_trades))
        results_table.add_row("Losing Trades", str(result.losing_trades))
        results_table.add_row("Win Rate", f"{result.win_rate:.2%}")
        results_table.add_row("Total PnL", f"${result.total_pnl:.2f}")
        results_table.add_row("Avg PnL/Trade", f"${result.avg_pnl_per_trade:.2f}")
        results_table.add_row("Max Drawdown", f"{result.max_drawdown:.2%}")
        results_table.add_row("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
        results_table.add_row("Avg Hold Time", str(result.avg_hold_time))
        results_table.add_row("Initial Capital", f"${result.initial_capital:.2f}")
        results_table.add_row("Final Capital", f"${result.final_capital:.2f}")
        results_table.add_row("Return", f"{((result.final_capital / result.initial_capital) - 1):.2%}")
        console.print(results_table)
        if show_trade_details and result.positions:
            positions_table = Table(
                title="Trade Details",
                show_header=True,
                header_style="bold cyan"
            )
            positions_table.add_column("ID", style="bold yellow", width=5)
            positions_table.add_column("Entry Time", style="white", width=20)
            positions_table.add_column("Entry Price", style="green", width=12)
            positions_table.add_column("Exit Time", style="white", width=20)
            positions_table.add_column("Exit Price", style="red", width=12)
            positions_table.add_column("PnL", style="bold", width=12)
            positions_table.add_column("Reason", style="blue", width=15)
            for position in result.positions:
                pnl_color = "green" if position.pnl and position.pnl > 0 else "red"
                positions_table.add_row(
                    str(position.id),
                    position.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                    f"${position.entry_price:.6f}",
                    position.exit_time.strftime("%Y-%m-%d %H:%M:%S") if position.exit_time else "Open",
                    f"${position.exit_price:.6f}" if position.exit_price else "-",
                    f"${position.pnl:.2f}" if position.pnl else "-",
                    position.exit_reason or "-"
                )
            console.print(positions_table)

def run_backtest(strategy_name: str, token_id: int, show_trade_details: bool = False) -> None:
    console.print(f"\n[bold cyan]Running {strategy_name.upper()} backtest on token {token_id} using all available data...[/bold cyan]")
    backtester = Backtester(strategy_name, token_id)
    try:
        result = backtester.run_backtest()
        backtester.display_results(result, show_trade_details)
        prisma = Prisma()
        try:
            prisma.connect()
            candles = backtester.get_historical_data(prisma)
            backtester.plot_results(result, candles)
        finally:
            try:
                prisma.disconnect()
            except:
                pass
    except Exception as e:
        console.print(f"[red]Backtest failed: {str(e)}[/red]")
        raise 