import unittest
from datetime import datetime, timedelta
import pytz
from strategies.local_extrema import LocalExtremaStrategy
from core.strategy_interface import Candle, Position

class TestLocalExtremaStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = LocalExtremaStrategy()
        self.base_time = datetime.now(pytz.UTC)
        
    def create_candle(self, minutes_offset: int, close: float, volume: float = 1000.0) -> Candle:
        """Helper method to create a candle with given close price."""
        timestamp = self.base_time + timedelta(minutes=minutes_offset)
        return Candle(
            timestamp=timestamp,
            open=close * 0.99,  # Slightly lower open
            high=close * 1.01,  # Slightly higher high
            low=close * 0.98,   # Slightly lower low
            close=close,
            volume=volume
        )
    
    def test_local_minima_detection(self):
        """Test that local minima are correctly detected."""
        # Create a price series with a clear local minimum
        # Pattern: 100 -> 95 -> 90 -> 95 -> 100 (90 is local minimum)
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 95.0),
            self.create_candle(2, 90.0),  # Local minimum
            self.create_candle(3, 95.0),
            self.create_candle(4, 100.0),
        ]
        
        # Test with current price at the local minimum
        curr = candles[2]  # Price 90.0
        lookback = candles[:2]  # Previous 2 candles
        
        data = {
            'lookback': lookback,
            'curr': curr,
            'last_exit_time': None
        }
        
        result = self.strategy.should_buy(data)
        self.assertEqual(result['action'], 'buy')
        self.assertIn('Local minimum detected', result['info'])
    
    def test_local_maxima_detection(self):
        """Test that local maxima are correctly detected."""
        # Create a price series with a clear local maximum
        # Pattern: 100 -> 105 -> 110 -> 105 -> 100 (110 is local maximum)
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 105.0),
            self.create_candle(2, 110.0),  # Local maximum
            self.create_candle(3, 105.0),
            self.create_candle(4, 100.0),
        ]
        
        # Create a position to test selling
        position = Position(
            id=1,
            entry_price=100.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        curr = candles[2]  # Price 110.0
        lookback = candles[:2]  # Previous 2 candles
        
        data = {
            'position': position,
            'curr': curr,
            'entry_price': 100.0,
            'entry_time': self.base_time,
            'lookback': lookback
        }
        
        result = self.strategy.should_sell(data)
        self.assertTrue(result['shouldSell'])
        self.assertEqual(result['reason'], 'local_maximum')
        self.assertIn('Local maximum detected', result['info'])
    
    def test_insufficient_data(self):
        """Test behavior when insufficient data is available."""
        # Not enough candles for extrema detection
        candles = []  # Empty lookback
        
        curr = self.create_candle(0, 90.0)
        
        data = {
            'lookback': candles,
            'curr': curr,
            'last_exit_time': None
        }
        
        result = self.strategy.should_buy(data)
        self.assertEqual(result['action'], 'hold')
        self.assertIn('Insufficient data', result['info'])
    
    def test_cooldown_period(self):
        """Test that buy signals are blocked during cooldown period."""
        # Create a local minimum scenario
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 95.0),
            self.create_candle(2, 90.0),  # Local minimum
            self.create_candle(3, 95.0),
            self.create_candle(4, 100.0),
        ]
        
        curr = candles[2]
        lookback = candles[:2]
        
        # Set last exit time to 5 minutes ago (within 10-minute cooldown)
        last_exit_time = datetime.now(pytz.UTC) - timedelta(minutes=5)
        
        data = {
            'lookback': lookback,
            'curr': curr,
            'last_exit_time': last_exit_time
        }
        
        result = self.strategy.should_buy(data)
        self.assertEqual(result['action'], 'hold')
        self.assertIn('cooldown period', result['info'])
    
    def test_stop_loss(self):
        """Test stop loss functionality."""
        position = Position(
            id=1,
            entry_price=100.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        # Current price is 94.0 (6% loss, should trigger stop loss)
        curr = self.create_candle(0, 94.0)
        
        data = {
            'position': position,
            'curr': curr,
            'entry_price': 100.0,
            'entry_time': self.base_time,
            'lookback': []
        }
        
        result = self.strategy.should_sell(data)
        self.assertTrue(result['shouldSell'])
        self.assertEqual(result['reason'], 'stop_loss')
        self.assertIn('Stop loss triggered', result['info'])
    
    def test_take_profit(self):
        """Test take profit functionality."""
        position = Position(
            id=1,
            entry_price=100.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        # Current price is 111.0 (11% gain, should trigger take profit)
        curr = self.create_candle(0, 111.0)
        
        data = {
            'position': position,
            'curr': curr,
            'entry_price': 100.0,
            'entry_time': self.base_time,
            'lookback': []
        }
        
        result = self.strategy.should_sell(data)
        self.assertTrue(result['shouldSell'])
        self.assertEqual(result['reason'], 'take_profit')
        self.assertIn('Take profit triggered', result['info'])
    
    def test_time_exit(self):
        """Test time-based exit functionality."""
        position = Position(
            id=1,
            entry_price=100.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        # Current price is 101.0 (1% gain, no other exit conditions)
        curr = self.create_candle(0, 101.0)
        
        # Set entry time to 2.5 hours ago (should trigger time exit)
        entry_time = datetime.now(pytz.UTC) - timedelta(hours=2, minutes=30)
        
        data = {
            'position': position,
            'curr': curr,
            'entry_price': 100.0,
            'entry_time': entry_time,
            'lookback': []
        }
        
        result = self.strategy.should_sell(data)
        self.assertTrue(result['shouldSell'])
        self.assertEqual(result['reason'], 'time_exit')
        self.assertIn('Time exit', result['info'])
    
    def test_complex_price_pattern(self):
        """Test with a more complex price pattern with multiple extrema."""
        # Create a complex pattern: 100 -> 95 -> 90 -> 95 -> 100 -> 105 -> 100 -> 95
        # Local minima at 90, local maxima at 105
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 95.0),
            self.create_candle(2, 90.0),  # First local minimum
            self.create_candle(3, 95.0),
            self.create_candle(4, 100.0),
            self.create_candle(5, 105.0),  # Local maximum
            self.create_candle(6, 100.0),
            self.create_candle(7, 95.0),   # Second local minimum
        ]
        
        # Test buying at first local minimum
        curr = candles[2]
        lookback = candles[:2]
        
        data = {
            'lookback': lookback,
            'curr': curr,
            'last_exit_time': None
        }
        
        result = self.strategy.should_buy(data)
        self.assertEqual(result['action'], 'buy')
        
        # Test selling at local maximum
        position = Position(
            id=1,
            entry_price=90.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        curr = candles[5]  # Price 105.0
        lookback = candles[:5]
        
        data = {
            'position': position,
            'curr': curr,
            'entry_price': 90.0,
            'entry_time': self.base_time,
            'lookback': lookback
        }
        
        result = self.strategy.should_sell(data)
        self.assertTrue(result['shouldSell'])
        self.assertEqual(result['reason'], 'local_maximum')
    
    def test_no_extrema_detection(self):
        """Test when no extrema are present in the data."""
        # Create a monotonically increasing price series (no local extrema)
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 101.0),
            self.create_candle(2, 102.0),
            self.create_candle(3, 103.0),
            self.create_candle(4, 104.0),
            self.create_candle(5, 105.0),
        ]
        
        curr = candles[5]
        lookback = candles[:5]
        
        data = {
            'lookback': lookback,
            'curr': curr,
            'last_exit_time': None
        }
        
        result = self.strategy.should_buy(data)
        self.assertEqual(result['action'], 'hold')
        self.assertIn('No local minimum detected', result['info'])

if __name__ == '__main__':
    unittest.main() 