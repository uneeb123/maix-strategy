import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from prisma import Prisma

def fetch_token_data(token_id=15158):
    """Fetch all real trading data from database using Prisma and save as JSON"""
    prisma = Prisma()
    prisma.connect()
    
    try:
        token_meta = prisma.migratedtoken.find_unique(where={'id': token_id})
        if not token_meta:
            raise ValueError(f"Token ID {token_id} not found in database")
        
        ohlcv = prisma.tokenohlcv.find_many(
            where={'tokenId': token_id, 'interval': '1s'},
            order=[{'timestamp': 'desc'}]
        )
        
        print(f"📊 Found {len(ohlcv)} total records")
        
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
        
        # Create complete data structure with token meta and OHLCV data
        complete_data = {
            'token_meta': {
                'id': token_meta.id,
                'symbol': token_meta.symbol,
                'name': token_meta.name,
                'address': token_meta.address,
                'networkId': token_meta.networkId,
                'marketCap': float(token_meta.marketCap),
                'priceUSD': float(token_meta.priceUSD),
                'twitter': token_meta.twitter,
                'website': token_meta.website,
                'description': token_meta.description
            },
            'ohlcv_data': data
        }
        
        # Save to JSON file
        file_path = "tests/helper/sample_data.json"
        with open(file_path, 'w') as f:
            json.dump(complete_data, f, indent=2)
        
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
    fetch_token_data(15156) 