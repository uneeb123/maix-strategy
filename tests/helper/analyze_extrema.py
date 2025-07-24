import json
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.helper.load_data import load_sample_candles

def find_local_extrema(candles: List, window: int = 10, 
                      max_points: int = 15) -> Tuple[List[Tuple], List[Tuple]]:
    """
    Find alternating local minima (buy points) and maxima (sell points) in candle data.
    Starts with the first local minimum, then finds the next local maximum, then minimum, etc.
    Ensures distribution throughout the entire chart.
    
    Args:
        candles: List of Candle objects
        window: Window size for finding extrema (default: 10)
        max_points: Maximum number of points to return per type (default: 15)
    
    Returns:
        Tuple of (buy_points, sell_points) where each point is (timestamp, price)
    """
    all_buy_points = []
    all_sell_points = []
    
    # Find all potential extrema
    for i in range(window, len(candles) - window):
        # Check if current point is a local minimum (buy point)
        is_minimum = True
        for j in range(i - window, i + window + 1):
            if j != i and candles[j].low <= candles[i].low:
                is_minimum = False
                break
        
        if is_minimum:
            all_buy_points.append((candles[i].timestamp, candles[i].low, i))
        
        # Check if current point is a local maximum (sell point)
        is_maximum = True
        for j in range(i - window, i + window + 1):
            if j != i and candles[j].high >= candles[i].high:
                is_maximum = False
                break
        
        if is_maximum:
            all_sell_points.append((candles[i].timestamp, candles[i].high, i))
    
    # Sort all points by timestamp (chronological order)
    all_buy_points.sort(key=lambda x: x[0])
    all_sell_points.sort(key=lambda x: x[0])
    
    # Calculate target spacing to distribute points throughout the chart
    total_candles = len(candles)
    target_spacing = total_candles // (max_points * 2)  # Space for both buy and sell points
    
    # Find alternating pattern with better distribution
    buy_points = []
    sell_points = []
    used_indices = set()
    
    # Find the first local minimum
    if all_buy_points:
        first_min_idx = 0
        while first_min_idx < len(all_buy_points):
            timestamp, price, index = all_buy_points[first_min_idx]
            if index not in used_indices:
                buy_points.append((timestamp, price))
                used_indices.add(index)
                last_index = index
                break
            first_min_idx += 1
    
    # Alternate between finding next maximum and next minimum with distribution
    current_looking_for_max = True
    target_index = last_index + target_spacing
    
    while len(buy_points) + len(sell_points) < max_points * 2:
        if current_looking_for_max:
            # Look for next maximum, prioritizing points near target index
            next_max = None
            best_score = float('inf')
            
            for timestamp, price, index in all_sell_points:
                if index > last_index and index not in used_indices:
                    # Score based on distance from target index (lower is better)
                    distance_from_target = abs(index - target_index)
                    score = distance_from_target
                    
                    if score < best_score:
                        best_score = score
                        next_max = (timestamp, price, index)
            
            if next_max:
                sell_points.append((next_max[0], next_max[1]))
                used_indices.add(next_max[2])
                last_index = next_max[2]
                target_index = last_index + target_spacing
                current_looking_for_max = False
            else:
                break
        else:
            # Look for next minimum, prioritizing points near target index
            next_min = None
            best_score = float('inf')
            
            for timestamp, price, index in all_buy_points:
                if index > last_index and index not in used_indices:
                    # Score based on distance from target index (lower is better)
                    distance_from_target = abs(index - target_index)
                    score = distance_from_target
                    
                    if score < best_score:
                        best_score = score
                        next_min = (timestamp, price, index)
            
            if next_min:
                buy_points.append((next_min[0], next_min[1]))
                used_indices.add(next_min[2])
                last_index = next_min[2]
                target_index = last_index + target_spacing
                current_looking_for_max = True
            else:
                break
    
    return buy_points, sell_points

def save_analysis_to_json(buy_points: List[Tuple], sell_points: List[Tuple], 
                         token_meta: Dict[str, Any], output_file: str = "tests/helper/sample_analysis.json"):
    """
    Save the extrema analysis to a JSON file.
    
    Args:
        buy_points: List of buy points as (timestamp, price) tuples
        sell_points: List of sell points as (timestamp, price) tuples
        token_meta: Token metadata
        output_file: Output file path
    """
    analysis_data = {
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
            "analysis_window": 10,
            "max_points": 15
        }
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"✅ Analysis saved to {output_file}")
    print(f"📊 Found {len(buy_points)} buy points and {len(sell_points)} sell points")

def load_analysis_from_json(file_path: str = "tests/helper/sample_analysis.json") -> Tuple[List[Tuple], List[Tuple], Dict[str, Any]]:
    """
    Load the extrema analysis from a JSON file.
    
    Args:
        file_path: Path to the analysis JSON file
    
    Returns:
        Tuple of (buy_points, sell_points, token_meta) where points are (timestamp, price) tuples
    """
    if not os.path.exists(file_path):
        print(f"❌ Analysis file not found: {file_path}")
        print("🔄 Generating analysis...")
        generate_sample_analysis()
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Convert timestamps back to datetime objects
    from datetime import datetime
    
    buy_points = [
        (datetime.fromisoformat(point["timestamp"]), point["price"])
        for point in data["buy_points"]
    ]
    
    sell_points = [
        (datetime.fromisoformat(point["timestamp"]), point["price"])
        for point in data["sell_points"]
    ]
    
    return buy_points, sell_points, data["token_meta"]

def generate_sample_analysis(token_id: int = 15158, window: int = 5):
    """
    Generate and save extrema analysis for sample data.
    
    Args:
        token_id: Token ID to analyze
        window: Window size for finding extrema
    """
    print(f"🔍 Analyzing extrema for token {token_id}...")
    
    # Load sample data
    candles, token_meta = load_sample_candles(token_id)
    
    # Find local extrema
    buy_points, sell_points = find_local_extrema(candles, window)
    
    # Save analysis
    save_analysis_to_json(buy_points, sell_points, token_meta)

if __name__ == "__main__":
    generate_sample_analysis() 