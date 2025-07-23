import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.strategy_interface import Candle
from tests.helper.fetch_data import fetch_token_data

def load_sample_candles(token_id=15158):
    """Load sample candles from saved JSON data"""
    file_path = "tests/helper/sample_data.json"
    
    if not os.path.exists(file_path):
        print(f"📥 Data file not found, fetching fresh data...")
        fetch_token_data(token_id)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        candles = []
        for item in data:
            # Parse timestamp from ISO format
            timestamp = datetime.fromisoformat(item['timestamp'])
            candles.append(Candle(
                timestamp=timestamp,
                open=float(item['open']),
                high=float(item['high']),
                low=float(item['low']),
                close=float(item['close']),
                volume=float(item['volume'])
            ))
        
        print(f"✅ Loaded {len(candles)} candles from {file_path}")
        return candles
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        raise 