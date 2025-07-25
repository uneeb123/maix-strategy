import pytest
from core.plotter import plot_trading_signals
from tests.helper.load_data import load_sample_candles

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

def test_plot(sample_candles, token_meta):
    """Test basic plot without any indicators"""
    strategy_name = "Test Strategy"
    token_title = f"{token_meta.get('name')} ({token_meta.get('id')})"
    
    result = plot_trading_signals(
        sample_candles, 
        token_title, 
        strategy_name
    )
    assert result is not None

def test_plot_with_pivot_points(sample_candles, token_meta):
    """Test plot with pivot points indicator"""
    strategy_name = "Test Strategy with Pivot Points"
    token_title = f"{token_meta.get('name')} ({token_meta.get('id')})"
    
    # Define indicators with parameters
    indicators = {
        "pivot_points": {
            "window": 50
        }
    }
    
    result = plot_trading_signals(
        sample_candles, 
        token_title, 
        strategy_name,
        indicators=indicators
    )
    assert result is not None