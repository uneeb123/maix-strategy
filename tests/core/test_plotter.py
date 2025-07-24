import os
import pytest
from datetime import datetime, timedelta
from core.plotter import plot_trading_signals
from core.strategy_interface import Candle
from tests.helper.load_data import load_sample_candles

@pytest.fixture
def sample_data():
    """Load real sample candle data and token meta for testing"""
    return load_sample_candles(15158)

@pytest.fixture
def sample_candles(sample_data):
    """Extract candles from sample data"""
    return sample_data[0]

@pytest.fixture
def token_meta(sample_data):
    """Extract token meta from sample data"""
    return sample_data[1]

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

def test_basic_plot(sample_candles, token_meta):
    """Test basic plotting without signals"""
    strategy_name = f"test_strategy_{token_meta.get('symbol', 'UNKNOWN') if token_meta else 'UNKNOWN'}"
    result = plot_trading_signals(sample_candles, 1, strategy_name)
    assert result is not None
    assert os.path.exists(result)

def test_plot_with_signals(sample_candles, buy_points, sell_points, token_meta):
    """Test plotting with buy/sell signals"""
    strategy_name = f"momentum_strategy_{token_meta.get('symbol', 'UNKNOWN') if token_meta else 'UNKNOWN'}"
    result = plot_trading_signals(
        sample_candles, 
        2, 
        strategy_name,
        buy_points=buy_points,
        sell_points=sell_points
    )
    assert result is not None
    assert os.path.exists(result)

def test_empty_candles():
    """Test plotting with empty candle data"""
    result = plot_trading_signals([], 3, "empty_test")
    assert result == ""

def test_plot_file_extension(sample_candles, token_meta):
    """Test that generated plot files have correct extension"""
    strategy_name = f"extension_test_{token_meta.get('symbol', 'UNKNOWN') if token_meta else 'UNKNOWN'}"
    result = plot_trading_signals(sample_candles, 4, strategy_name)
    assert result.endswith('.png')

def test_plot_artifacts_directory():
    """Test that plots are saved in artifacts directory"""
    sample_data = load_sample_candles(15158)
    candles = sample_data[0][:5]  # Use first 5 candles from real data
    token_meta = sample_data[1]
    
    strategy_name = f"directory_test_{token_meta.get('symbol', 'UNKNOWN') if token_meta else 'UNKNOWN'}"
    result = plot_trading_signals(candles, 5, strategy_name)
    assert 'artifacts' in result

def test_token_meta_information(token_meta):
    """Test that token meta information is properly loaded"""
    if token_meta:
        assert 'symbol' in token_meta
        assert 'name' in token_meta
        assert 'id' in token_meta
        assert 'address' in token_meta
        assert 'networkId' in token_meta
        assert 'marketCap' in token_meta
        assert 'priceUSD' in token_meta
        print(f"✅ Token meta loaded: {token_meta['symbol']} ({token_meta['name']})")
        print(f"   Market Cap: ${token_meta['marketCap']:,.2f}")
        print(f"   Price: ${token_meta['priceUSD']:.6f}")
    else:
        print("⚠️ No token meta available") 