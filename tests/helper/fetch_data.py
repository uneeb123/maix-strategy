import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from prisma import Prisma

def fetch_token_data(token_id=15158, lookback_periods=100):
    """Fetch real trading data from database using Prisma and save as JSON"""
    prisma = Prisma()
    prisma.connect()
    
    try:
        token_meta = prisma.migratedtoken.find_unique(where={'id': token_id})
        if not token_meta:
            raise ValueError(f"Token ID {token_id} not found in database")
        
        ohlcv = prisma.tokenohlcv.find_many(
            where={'tokenId': token_id, 'interval': '1s'},
            order=[{'timestamp': 'desc'}],
            take=lookback_periods
        )
        
        if len(ohlcv) < lookback_periods:
            print(f"⚠️  Only {len(ohlcv)} records found, requested {lookback_periods}")
        
        data = []
        for row in reversed(ohlcv):
            data.append({
                'timestamp': row.timestamp.isoformat(),
                'open': float(row.open),
                'high': float(row.high),
                'low': float(row.low),
                'close': float(row.close),
                'volume': float(row.volumeUSD)
            })
        
        # Save to JSON file
        file_path = "tests/helper/sample_data.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Fetched {len(data)} records for token {token_id} ({token_meta.symbol})")
        print(f"✅ Data saved to {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ Failed to fetch data from database: {e}")
        raise
    finally:
        prisma.disconnect()

if __name__ == "__main__":
    # Fetch data when run directly
    fetch_token_data(15158, 100) 