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
        
        # Handle both old format (list) and new format (dict with token_meta and ohlcv_data)
        if isinstance(data, list):
            # Old format - just OHLCV data
            ohlcv_data = data
            token_meta = None
        else:
            # New format - structured data
            ohlcv_data = data.get('ohlcv_data', [])
            token_meta = data.get('token_meta')
        
        candles = []
        for item in ohlcv_data:
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
        if token_meta:
            print(f"✅ Token: {token_meta.get('symbol', 'Unknown')} ({token_meta.get('name', 'Unknown')})")
        
        return candles, token_meta
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        raise 