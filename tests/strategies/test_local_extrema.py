import unittest
from datetime import datetime, timedelta
import pytz
from strategies.local_extrema import LocalExtremaStrategy
from core.strategy_interface import Candle, Position
from core.plotter import plot_trading_signals

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
    
    def test_extrema_detection_with_plot(self):
        """Test local extrema detection and generate a plot showing the results."""
        # Create a price series with clear local minima and maxima
        # Pattern: 100 -> 95 -> 90 -> 95 -> 100 -> 105 -> 100 -> 95 -> 90 -> 95
        # Local minima at 90 (positions 2 and 8), local maxima at 105 (position 5)
        candles = [
            self.create_candle(0, 100.0),
            self.create_candle(1, 95.0),
            self.create_candle(2, 90.0),  # First local minimum
            self.create_candle(3, 95.0),
            self.create_candle(4, 100.0),
            self.create_candle(5, 105.0),  # Local maximum
            self.create_candle(6, 100.0),
            self.create_candle(7, 95.0),
            self.create_candle(8, 90.0),   # Second local minimum
            self.create_candle(9, 95.0),
        ]
        
        buy_points = []
        sell_points = []
        
        # Test each candle for extrema detection
        for i in range(2, len(candles) - 1):  # Skip first and last candles
            curr = candles[i]
            lookback = candles[:i]
            
            # Test for local minimum (buy signal)
            buy_data = {
                'lookback': lookback,
                'curr': curr,
                'last_exit_time': None
            }
            
            buy_result = self.strategy.should_buy(buy_data)
            if buy_result['action'] == 'buy':
                buy_points.append((curr.timestamp, curr.close))
                print(f"Local minimum detected at {curr.timestamp}: ${curr.close:.2f}")
        
        # Test for local maximum (sell signal) - simulate having a position
        position = Position(
            id=1,
            entry_price=90.0,
            entry_time=self.base_time,
            size=1.0
        )
        
        for i in range(2, len(candles) - 1):
            curr = candles[i]
            lookback = candles[:i]
            
            sell_data = {
                'position': position,
                'curr': curr,
                'entry_price': 90.0,
                'entry_time': self.base_time,
                'lookback': lookback
            }
            
            sell_result = self.strategy.should_sell(sell_data)
            if sell_result['shouldSell'] and sell_result['reason'] == 'local_maximum':
                sell_points.append((curr.timestamp, curr.close))
                print(f"Local maximum detected at {curr.timestamp}: ${curr.close:.2f}")
        
        # Verify we detected the expected extrema
        detected_minima = [price for _, price in buy_points]
        detected_maxima = [price for _, price in sell_points]
        
        print(f"\nDetected local minima: {detected_minima}")
        print(f"Detected local maxima: {detected_maxima}")
        
        # Check that we detected at least one of each type
        self.assertGreater(len(buy_points), 0, "No local minima detected")
        self.assertGreater(len(sell_points), 0, "No local maxima detected")
        
        # Verify that the main expected extrema are detected
        self.assertIn(90.0, detected_minima, "Main local minimum at 90.0 not detected")
        self.assertIn(105.0, detected_maxima, "Main local maximum at 105.0 not detected")
        
        # Generate plot
        try:
            plot_path = plot_trading_signals(
                candles=candles,
                token_id=0,
                strategy_name="local_extrema",
                buy_points=buy_points,
                sell_points=sell_points
            )
            print(f"\nPlot saved to: {plot_path}")
            self.assertIsNotNone(plot_path, "Plot generation failed")
        except Exception as e:
            print(f"Plot generation failed: {e}")
            # Don't fail the test if plotting fails, just warn
            self.skipTest(f"Plotting not available: {e}")

if __name__ == '__main__':
    unittest.main() 