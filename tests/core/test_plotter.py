import os
import pytest
from datetime import datetime, timedelta
from core.plotter import plot_trading_signals
from core.strategy_interface import Candle
from tests.helper.load_data import load_sample_candles

@pytest.fixture
def sample_candles():
    """Load real sample candle data for testing"""
    return load_sample_candles(15158)

@pytest.fixture
def buy_points(sample_candles):
    """Create sample buy points"""
    return [
        (sample_candles[3].timestamp, sample_candles[3].low),
        (sample_candles[8].timestamp, sample_candles[8].low),
        (sample_candles[15].timestamp, sample_candles[15].low)
    ]

@pytest.fixture
def sell_points(sample_candles):
    """Create sample sell points"""
    return [
        (sample_candles[6].timestamp, sample_candles[6].high),
        (sample_candles[12].timestamp, sample_candles[12].high),
        (sample_candles[18].timestamp, sample_candles[18].high)
    ]

def test_basic_plot(sample_candles):
    """Test basic plotting without signals"""
    result = plot_trading_signals(sample_candles, 1, "test_strategy")
    assert result is not None
    assert os.path.exists(result)

def test_plot_with_signals(sample_candles, buy_points, sell_points):
    """Test plotting with buy/sell signals"""
    result = plot_trading_signals(
        sample_candles, 
        2, 
        "momentum_strategy",
        buy_points=buy_points,
        sell_points=sell_points
    )
    assert result is not None
    assert os.path.exists(result)

def test_empty_candles():
    """Test plotting with empty candle data"""
    result = plot_trading_signals([], 3, "empty_test")
    assert result == ""

def test_plot_file_extension(sample_candles):
    """Test that generated plot files have correct extension"""
    result = plot_trading_signals(sample_candles, 4, "extension_test")
    assert result.endswith('.png')

def test_plot_artifacts_directory():
    """Test that plots are saved in artifacts directory"""
    candles = load_sample_candles(15158)[:5]  # Use first 5 candles from real data
    
    result = plot_trading_signals(candles, 5, "directory_test")
    assert 'artifacts' in result 