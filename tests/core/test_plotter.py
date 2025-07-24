import os
import pytest
from core.plotter import plot_trading_signals
from tests.helper.load_data import load_sample_candles
from tests.helper.analyze_extrema import load_analysis_from_json

@pytest.fixture
def sample_data():
    """Load real sample candle data and token meta for testing"""
    candles = load_sample_candles(15158)
    return candles

@pytest.fixture
def sample_candles(sample_data):
    """Extract candles from sample data"""
    return sample_data[0]

@pytest.fixture
def token_meta(sample_data):
    """Extract token meta from sample data"""
    return sample_data[1]

@pytest.fixture
def buy_points():
    """Load actual buy points from extrema analysis"""
    buy_points, _, _ = load_analysis_from_json()
    return buy_points  # Use all significant buy points

@pytest.fixture
def sell_points():
    """Load actual sell points from extrema analysis"""
    _, sell_points, _ = load_analysis_from_json()
    return sell_points  # Use all significant sell points

def test_plot_with_signals(sample_candles, buy_points, sell_points, token_meta):
    strategy_name = f"test_strategy_{token_meta.get('name')}"
    result = plot_trading_signals(
        sample_candles, 
        0, 
        strategy_name,
        buy_points=buy_points,
        sell_points=sell_points
    )
    assert result is not None
    assert os.path.exists(result)