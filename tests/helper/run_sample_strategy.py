import sys
from pathlib import Path
import os
import json
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.helper.load_data import load_sample_candles
from tests.helper.algorithms.zigzag import find_zigzag
from tests.helper.algorithms.zigzag_modified import find_zigzag_signals
from tests.helper.algorithms.fractals import find_fractals
from tests.helper.algorithms.pivot_points import find_pivot_points
from tests.helper.algorithms.swing_detection import find_swings

def save_analysis_to_json(buy_points: List[Tuple], sell_points: List[Tuple], 
                         token_meta: Dict[str, Any], output_file: str = "tests/helper/sample_analysis_zigzag.json"):
    analysis_data = {
        "algorithm": "zigzag",
        "token_meta": token_meta,
        "buy_points": [
            {
                "timestamp": point[0].isoformat(),
                "price": point[1]
            }
            for point in buy_points
        ],
        "sell_points": [
            {
                "timestamp": point[0].isoformat(),
                "price": point[1]
            }
            for point in sell_points
        ],
        "summary": {
            "total_buy_points": len(buy_points),
            "total_sell_points": len(sell_points),
            "deviation": 0.05,
            "max_points": 15
        }
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"✅ ZigZag analysis saved to {output_file}")
    print(f"📊 Found {len(buy_points)} valleys and {len(sell_points)} peaks")

def run_sample_strategy(token_id: int = 15158, deviation: float = 0.05, window: int = 5, strength: int = 2):
    candles, token_meta = load_sample_candles(token_id)
    
    # buy_points, sell_points = find_zigzag(candles, 0.05)
    # buy_points, sell_points = find_zigzag_signals(candles, 0.03)
    # buy_points, sell_points = find_fractals(candles, 50)
    buy_points, sell_points = find_pivot_points(candles, 50)
    # buy_points, sell_points = find_swings(candles, 50)
    save_analysis_to_json(buy_points, sell_points, token_meta, output_file="tests/helper/sample_analysis.json")

if __name__ == "__main__":
    run_sample_strategy() 