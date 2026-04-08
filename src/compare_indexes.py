#!/usr/bin/env python3
"""
Compare different PPP indexes side-by-side to choose the best one for your app.

Shows how different indexes (Numbeo, Big Mac, Netflix, Spotify) would price
the same baseline across territories.

Usage:
    python compare_indexes.py --baseline 7.99
    python compare_indexes.py --baseline 7.99 --territories GBR,IND,BRA,RUS,CHN
    python compare_indexes.py --baseline 7.99 --output csv > index-comparison.csv

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

INDEXES = {
    "numbeo": DATA_DIR / "ppp-index-numbeo-2026.json",
    "bigmac": DATA_DIR / "ppp-index-bigmac-2026.json",
    "netflix": DATA_DIR / "ppp-index-netflix-2026.json",
    "spotify": DATA_DIR / "ppp-index-spotify-2026.json",
}

# --- Utilities ---

def load_ppp_index(path: Path) -> Dict:
    """Load PPP index from JSON file."""
    with open(path) as f:
        return json.load(f)


def calculate_ppp_price(baseline_usd: float, baseline_pp: float, territory_pp: float) -> float:
    """Calculate PPP-adjusted price."""
    return baseline_usd * (territory_pp / baseline_pp)


def round_to_psychological(price: float) -> float:
    """Round to .99 or .49 ending."""
    if price < 1.0:
        return 0.99
    
    integer_part = int(price)
    option_99 = integer_part + 0.99
    option_49 = integer_part + 0.49
    
    if abs(price - option_99) < abs(price - option_49):
        return option_99
    else:
        return option_49


def get_territory_name(territory_code: str) -> str:
    """Get human-readable territory name."""
    common_names = {
        "USA": "United States", "GBR": "United Kingdom", "DEU": "Germany",
        "FRA": "France", "JPN": "Japan", "CHN": "China", "IND": "India",
        "BRA": "Brazil", "RUS": "Russia", "CAN": "Canada", "AUS": "Australia",
        "MEX": "Mexico", "KOR": "South Korea", "ESP": "Spain", "ITA": "Italy",
        "NLD": "Netherlands", "CHE": "Switzerland", "SWE": "Sweden", "POL": "Poland",
        "TUR": "Turkey", "IDN": "Indonesia", "THA": "Thailand", "SGP": "Singapore",
    }
    return common_names.get(territory_code, territory_code)


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Compare different PPP indexes side-by-side",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare all indexes for $7.99 baseline
  python compare_indexes.py --baseline 7.99

  # Show only selected territories
  python compare_indexes.py --baseline 7.99 --territories GBR,IND,BRA,RUS,CHN,USA

  # Export as CSV
  python compare_indexes.py --baseline 7.99 --output csv > index-comparison.csv

  # Compare multiple baselines
  python compare_indexes.py --baseline 4.99 --baseline 7.99 --baseline 9.99
        """
    )
    
    parser.add_argument(
        "--baseline",
        type=float,
        action="append",
        required=True,
        help="Baseline price in USD (can specify multiple)"
    )
    parser.add_argument(
        "--territories",
        help="Comma-separated list of territories to show (default: all common)"
    )
    parser.add_argument(
        "--output",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--indexes",
        help="Comma-separated list of indexes to compare (default: all)"
    )
    
    args = parser.parse_args()
    
    # Load indexes
    index_data = {}
    indexes_to_use = args.indexes.split(",") if args.indexes else list(INDEXES.keys())
    
    for name in indexes_to_use:
        if name not in INDEXES:
            print(f"❌ Unknown index: {name}", file=sys.stderr)
            sys.exit(1)
        
        index_data[name] = load_ppp_index(INDEXES[name])
    
    # Determine territories
    if args.territories:
        territories = args.territories.split(",")
    else:
        # Show common major markets
        territories = [
            "USA", "GBR", "DEU", "FRA", "IND", "BRA", "RUS", "CHN", "JPN",
            "CAN", "AUS", "MEX", "KOR", "ESP", "ITA", "TUR", "IDN", "THA",
            "SGP", "CHE", "SWE", "POL", "ARG", "EGY", "PAK", "VNM"
        ]
    
    # Calculate prices
    results = []
    
    for territory in territories:
        row = {
            "territory": territory,
            "territory_name": get_territory_name(territory),
        }
        
        for baseline_usd in args.baseline:
            baseline_key = f"baseline_{baseline_usd:.2f}".replace(".", "_")
            
            for index_name, data in index_data.items():
                baseline_pp = data["baseline_value"]
                territory_pp = data["index"].get(territory)
                
                if territory_pp is None:
                    price = None
                else:
                    raw_price = calculate_ppp_price(baseline_usd, baseline_pp, territory_pp)
                    price = round_to_psychological(raw_price)
                
                row[f"{baseline_key}_{index_name}"] = price
        
        results.append(row)
    
    # Output
    if args.output == "json":
        output_data = {
            "baselines": args.baseline,
            "indexes": {name: data["source"] for name, data in index_data.items()},
            "territories": results
        }
        print(json.dumps(output_data, indent=2))
    
    elif args.output == "csv":
        fieldnames = ["territory", "territory_name"]
        
        for baseline_usd in args.baseline:
            baseline_key = f"baseline_{baseline_usd:.2f}".replace(".", "_")
            for index_name in indexes_to_use:
                fieldnames.append(f"{baseline_key}_{index_name}")
        
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    else:  # table
        print(f"\n📊 PPP Index Comparison", file=sys.stderr)
        print(f"Baselines: {', '.join(f'${b:.2f}' for b in args.baseline)}", file=sys.stderr)
        print(f"", file=sys.stderr)
        
        for name, data in index_data.items():
            print(f"  {name.upper()}: {data['source']}", file=sys.stderr)
        
        print(f"", file=sys.stderr)
        
        # For simplicity, show only first baseline in table
        baseline_usd = args.baseline[0]
        if len(args.baseline) > 1:
            print(f"ℹ️  Showing prices for ${baseline_usd:.2f} baseline only (use --output csv for all)", file=sys.stderr)
            print(f"", file=sys.stderr)
        
        # Table header
        header = ["Territory", "Name"]
        for index_name in indexes_to_use:
            header.append(index_name.capitalize())
        header.append("Spread")
        
        col_widths = [12, 15] + [10] * len(indexes_to_use) + [8]
        
        print(" | ".join(h.ljust(w) for h, w in zip(header, col_widths)))
        print("-+-".join("-" * w for w in col_widths))
        
        # Table rows
        for row in results:
            territory = row["territory"]
            territory_name = row["territory_name"][:13]
            
            cols = [territory, territory_name]
            
            prices = []
            baseline_key = f"baseline_{baseline_usd:.2f}".replace(".", "_")
            
            for index_name in indexes_to_use:
                price = row.get(f"{baseline_key}_{index_name}")
                if price is not None:
                    cols.append(f"${price:.2f}")
                    prices.append(price)
                else:
                    cols.append("—")
            
            # Calculate spread
            if len(prices) > 1:
                spread = max(prices) - min(prices)
                cols.append(f"${spread:.2f}")
            else:
                cols.append("—")
            
            print(" | ".join(c.ljust(w) for c, w in zip(cols, col_widths)))
        
        print()
        print(f"💡 Recommendations:", file=sys.stderr)
        print(f"   • Numbeo: General cost of living (broad consumer basket)", file=sys.stderr)
        print(f"   • Big Mac: Fast food consumer goods (real purchasing power)", file=sys.stderr)
        print(f"   • Netflix: Digital entertainment subscriptions (streaming apps)", file=sys.stderr)
        print(f"   • Spotify: Music/audio subscriptions (lifestyle/entertainment apps)", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"   Use Netflix/Spotify for entertainment/lifestyle apps.", file=sys.stderr)
        print(f"   Use Big Mac for consumer goods/utilities.", file=sys.stderr)
        print(f"   Use Numbeo for broad demographic data.", file=sys.stderr)


if __name__ == "__main__":
    main()
