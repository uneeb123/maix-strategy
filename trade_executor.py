#!/usr/bin/env python3
"""
Trade Executor - CLI interface for trading bot with strategy pattern
"""

import asyncio
import signal
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.align import Align
from rich import box

from prisma import Prisma
from core.strategy_factory import StrategyFactory
from core.backtest import run_backtest
from core.executor import Executor

import importlib
import json
from pathlib import Path

# Initialize Rich console
console = Console()

# Global signal handler will be set up in main() to avoid conflicts with Executor


def get_token_id() -> int:
    """Get token ID from user input with Rich UI and database validation"""
    # Initialize Prisma client for validation
    prisma = Prisma()
    prisma.connect()
    
    try:
        while True:
            try:
                token_id = Prompt.ask(
                    "\n[bold cyan]Enter the token ID to trade[/bold cyan]",
                    default="15156"
                )
                token_id_int = int(token_id)
                
                # Validate token exists in database
                token_meta = prisma.migratedtoken.find_unique(where={'id': token_id_int})
                if not token_meta:
                    console.print(f"❌ [red]Token ID {token_id_int} not found in database. Please enter a valid token ID.[/red]")
                    continue
                
                # Display token info for confirmation
                console.print(f"✅ [green]Token found: {token_meta.symbol} ({token_meta.name})[/green]")
                return token_id_int
                
            except ValueError:
                console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
            except KeyboardInterrupt:
                console.print("\n👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)
    finally:
        prisma.disconnect()

def select_strategy() -> str:
    """Interactive strategy selection with Rich UI"""
    strategies = StrategyFactory.list_strategies()
    
    # Create strategy selection table
    table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Strategy", style="bold green", width=15)
    table.add_column("Description", style="white", width=25)
    table.add_column("Lookback", style="yellow", width=10)
    
    strategy_names = []
    for strategy_info in strategies:
        strategy_name = strategy_info['name'].lower()
        strategy_names.append(strategy_name)
        config = StrategyFactory.get_strategy_config(strategy_name)
        table.add_row(
            f"[bold]{strategy_info['name'].upper()}[/bold]",
            strategy_info['description'],
            f"{config.lookback_periods} periods"
        )
    
    console.print(table)
    
    # Get user selection
    while True:
        try:
            choice = Prompt.ask(
                "\n[bold cyan]Select strategy[/bold cyan]",
                choices=strategy_names,
                default=strategy_names[0]
            )
            return choice
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)
    


def simple_strategy_selection() -> str:
    """Fallback simple strategy selection with Rich UI"""
    strategies = StrategyFactory.list_strategies()
    
    # Create numbered strategy list
    table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="bold yellow", width=5)
    table.add_column("Strategy", style="bold green", width=15)
    table.add_column("Description", style="white", width=25)
    table.add_column("Lookback", style="yellow", width=10)
    
    strategy_names = []
    for i, strategy_info in enumerate(strategies, 1):
        strategy_name = strategy_info['name'].lower()
        strategy_names.append(strategy_name)
        config = StrategyFactory.get_strategy_config(strategy_name)
        table.add_row(
            str(i),
            f"[bold]{strategy_info['name'].upper()}[/bold]",
            strategy_info['description'],
            f"{config.lookback_periods} periods"
        )
    
    console.print(table)
    
    while True:
        try:
            choice = Prompt.ask(
                f"\n[bold cyan]Enter your choice[/bold cyan] (1-{len(strategies)})",
                default="1"
            )
            choice_num = int(choice)
            if 1 <= choice_num <= len(strategies):
                return strategy_names[choice_num - 1]
            else:
                console.print(f"❌ [red]Please enter a number between 1 and {len(strategies)}[/red]")
        except ValueError:
            console.print("❌ [red]Invalid input. Please enter a valid number.[/red]")
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)


def select_mode() -> str:
    """Select between backtest and auto-trade modes"""
    console.print("\n[bold cyan]Select Mode:[/bold cyan]")
    
    mode_table = Table(
        show_header=True,
        header_style="bold cyan"
    )
    
    mode_table.add_column("Mode", style="bold green", width=15)
    mode_table.add_column("Description", style="white", width=40)
    
    mode_table.add_row(
        "[bold]BACKTEST[/bold]",
        "Test strategy on historical data with analysis and plots"
    )
    mode_table.add_row(
        "[bold]AUTO-TRADE[/bold]",
        "Run live trading bot with real-time execution"
    )
    
    console.print(mode_table)
    
    while True:
        try:
            choice = Prompt.ask(
                "\n[bold cyan]Select mode[/bold cyan]",
                choices=["backtest", "auto-trade"],
                default="backtest"
            )
            return choice
        except KeyboardInterrupt:
            console.print("\n👋 [yellow]Exiting...[/yellow]")
            sys.exit(0)





def validate_strategies_config():
    """Validate that all strategies in config.json exist as files and classes."""
    config_path = Path(__file__).parent / 'strategies' / 'config.json'
    strategies_dir = Path(__file__).parent / 'strategies'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading config.json: {e}[/red]")
        sys.exit(1)
    errors = []
    for entry in config:
        name = entry.get('name')
        if not name:
            errors.append("Missing 'name' in config entry.")
            continue
        file_path = strategies_dir / f"{name.lower()}.py"
        if not file_path.exists():
            errors.append(f"Missing file: {file_path}")
            continue
        try:
            module = importlib.import_module(f"strategies.{name.lower()}")
            class_name = f"{name}Strategy"
            getattr(module, class_name)
        except Exception as e:
            errors.append(f"Missing or invalid class {class_name} in {file_path}: {e}")
    if errors:
        console.print("[red]Strategy config is ill-formed:[/red]")
        for err in errors:
            console.print(f"[red]- {err}[/red]")
        sys.exit(1)

async def main():
    """Main entry point with interactive CLI"""
    # Set up global signal handler for graceful shutdown
    def global_signal_handler(signum, frame):
        console.print("\n\n👋 [yellow]Graceful shutdown requested. Exiting...[/yellow]")
        sys.exit(0)
    
    # Register global signal handlers (will be overridden by TradeExecutor when needed)
    signal.signal(signal.SIGINT, global_signal_handler)
    signal.signal(signal.SIGTERM, global_signal_handler)
    
    validate_strategies_config()
    
    while True:
        try:
            # Beautiful ASCII art header
            header = Panel(
                Align.center(
                    Text("███╗   ███╗ █████╗ ██╗██╗  ██╗", style="bold cyan") + "\n" +
                    Text("████╗ ████║██╔══██╗██║╚██╗██╔╝", style="bold cyan") + "\n" +
                    Text("██╔████╔██║███████║██║ ╚███╔╝ ", style="bold cyan") + "\n" +
                    Text("██║╚██╔╝██║██╔══██║██║ ██╔██╗ ", style="bold cyan") + "\n" +
                    Text("██║ ╚═╝ ██║██║  ██║██║██╔╝ ██╗", style="bold cyan") + "\n" +
                    Text("╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝", style="bold cyan") + "\n\n" +
                    Text("    Algorithmic Trading Platform", style="bold white"),
                    vertical="middle"
                ),
                box=box.DOUBLE,
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(header)
            
            # Get token ID
            token_id = get_token_id()
            
            while True:
                # Get strategy selection
                try:
                    strategy_name = select_strategy()
                except (ImportError, OSError):
                    # Fallback to simple selection if cursor navigation fails
                    console.print("⚠️  [yellow]Cursor navigation not available, using simple selection...[/yellow]")
                    strategy_name = simple_strategy_selection()
                
                # Select mode
                mode = select_mode()
                

                
                if mode == "backtest":
                    # Run backtest with all available data
                    try:
                        run_backtest(strategy_name, token_id)
                        
                        # Ask if user wants to try another strategy or exit
                        if Confirm.ask("\n🔄 [bold cyan]Try another strategy?[/bold cyan]"):
                            console.print("\n" + "="*80 + "\n")
                            continue  # Go back to strategy selection, same token_id
                        else:
                            console.print("👋 [yellow]Exiting...[/yellow]")
                            sys.exit(0)
                            
                    except Exception as e:
                        console.print(f"[red]Backtest failed: {str(e)}[/red]")
                        if Confirm.ask("\n🔄 [bold cyan]Try again?[/bold cyan]"):
                            continue
                        else:
                            console.print("👋 [yellow]Exiting...[/yellow]")
                            sys.exit(0)
                
                elif mode == "auto-trade":
                    console.print("\n🔄 [bold green]Starting trading bot...[/bold green]")
                    executor = Executor(strategy_name, token_id, prompt_for_configs=True)
                    await executor.run()
                    
                    # After auto-trade ends, ask if user wants to try another strategy
                    if Confirm.ask("\n🔄 [bold cyan]Try another strategy?[/bold cyan]"):
                        console.print("\n" + "="*80 + "\n")
                        continue  # Go back to strategy selection, same token_id
                    else:
                        console.print("👋 [yellow]Exiting...[/yellow]")
                        sys.exit(0)
                
        except KeyboardInterrupt:
            console.print("\n\n👋 [yellow]Graceful shutdown requested. Exiting...[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
            if Confirm.ask("\n🔄 [bold cyan]Try again?[/bold cyan]"):
                console.print("\n" + "="*80 + "\n")
                continue
            else:
                console.print("👋 [yellow]Exiting...[/yellow]")
                sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main()) 