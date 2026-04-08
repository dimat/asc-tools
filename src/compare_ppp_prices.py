#!/usr/bin/env python3
"""
Compare current App Store prices with PPP-adjusted recommendations.

Fetches actual current prices from ASC for a subscription and compares them
with what PPP pricing would recommend. Shows which territories are:
- ✅ Already PPP-aligned
- ⬆️ Underpriced (leaving money on the table)
- ⬇️ Overpriced (could hurt conversions)

Usage:
    python compare_ppp_prices.py \\
        --app-id 1584962857 \\
        --subscription-id 1586316851 \\
        --baseline-usd 7.99

    python compare_ppp_prices.py \\
        --app-id 1584962857 \\
        --subscription-id 1586316851 \\
        --baseline-usd 7.99 \\
        --output csv > comparison.csv

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_PPP_INDEX = DATA_DIR / "ppp-index-numbeo-2026.json"

CARRIER_BILLING_TERRITORIES = {"RUS", "BLR", "UZB", "TJK", "KGZ", "AZE", "ARM", "GEO", "MDA"}
CARRIER_BILLING_PP_CAP = 80.0

CURRENCY_CONVERSION_ISSUES = {
    "HUN", "IDN", "NGA", "KOR", "JPN", "PAK", "TZA", "VNM", "KAZ"
}

# --- Utilities ---

def load_ppp_index(path: Path) -> Dict:
    """Load PPP index from JSON file."""
    with open(path) as f:
        return json.load(f)


def run_asc(args: List[str], capture=True) -> subprocess.CompletedProcess:
    """Run ASC CLI command."""
    cmd = ["asc"] + args
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    else:
        return subprocess.run(cmd, check=False)


def calculate_ppp_price(
    baseline_usd: float,
    baseline_pp: float,
    territory_pp: float,
    carrier_billing_cap: Optional[float] = None
) -> float:
    """Calculate PPP-adjusted price."""
    effective_pp = territory_pp
    if carrier_billing_cap and territory_pp < carrier_billing_cap:
        effective_pp = carrier_billing_cap
    
    return baseline_usd * (effective_pp / baseline_pp)


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


def get_current_prices(subscription_id: str) -> Dict[str, Tuple[float, str]]:
    """
    Fetch current subscription prices from ASC.
    
    Returns dict: {territory_code: (price, currency)}
    """
    print("🔍 Fetching current prices from App Store Connect...", file=sys.stderr)
    
    result = run_asc([
        "subscriptions", "pricing", "prices", "list",
        "--subscription-id", subscription_id,
        "--resolved", "--output", "json"
    ])
    
    if result.returncode != 0:
        print(f"❌ Failed to fetch prices: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response", file=sys.stderr)
        sys.exit(1)
    
    # Extract current prices
    prices = {}
    
    for price_entry in data.get("prices", []):
        territory_id = price_entry.get("territory")
        customer_price = price_entry.get("customerPrice")
        currency = price_entry.get("currency", "USD")
        
        if territory_id and customer_price is not None:
            prices[territory_id] = (float(customer_price), currency)
    
    print(f"   Found prices for {len(prices)} territories", file=sys.stderr)
    return prices


def get_territory_name(territory_code: str) -> str:
    """Get human-readable territory name."""
    common_names = {
        "USA": "United States", "GBR": "United Kingdom", "DEU": "Germany",
        "FRA": "France", "JPN": "Japan", "CHN": "China", "IND": "India",
        "BRA": "Brazil", "RUS": "Russia", "CAN": "Canada", "AUS": "Australia",
        "MEX": "Mexico", "KOR": "South Korea", "ESP": "Spain", "ITA": "Italy",
        "NLD": "Netherlands", "CHE": "Switzerland", "SWE": "Sweden", "POL": "Poland",
        "TUR": "Turkey", "IDN": "Indonesia", "THA": "Thailand", "SGP": "Singapore",
        "MYS": "Malaysia", "PHL": "Philippines", "VNM": "Vietnam",
        "ARE": "United Arab Emirates", "SAU": "Saudi Arabia", "ZAF": "South Africa",
        "EGY": "Egypt", "NGA": "Nigeria", "ARG": "Argentina", "CHL": "Chile",
        "COL": "Colombia", "PER": "Peru", "UKR": "Ukraine", "ROU": "Romania",
        "CZE": "Czech Republic", "HUN": "Hungary", "GRC": "Greece", "PRT": "Portugal",
        "IRL": "Ireland", "NZL": "New Zealand", "ISR": "Israel", "HKG": "Hong Kong",
        "TWN": "Taiwan",
    }
    return common_names.get(territory_code, territory_code)


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Compare current ASC prices with PPP recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare Carousel monthly subscription
  python compare_ppp_prices.py \\
      --app-id 1584962857 \\
      --subscription-id 1586316851 \\
      --baseline-usd 7.99

  # Export comparison as CSV
  python compare_ppp_prices.py \\
      --app-id 1584962857 \\
      --subscription-id 1586316851 \\
      --baseline-usd 7.99 \\
      --output csv > comparison.csv

  # Show only misaligned territories
  python compare_ppp_prices.py \\
      --app-id 1584962857 \\
      --subscription-id 1586316851 \\
      --baseline-usd 7.99 \\
      --show-only misaligned
        """
    )
    
    parser.add_argument("--app-id", required=True, help="App Store app ID")
    parser.add_argument("--subscription-id", required=True, help="Subscription ID to compare")
    parser.add_argument("--baseline-usd", type=float, required=True, help="Baseline price in USD")
    
    parser.add_argument(
        "--output",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--show-only",
        choices=["all", "misaligned", "underpriced", "overpriced"],
        default="all",
        help="Filter results (default: all)"
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="Price difference tolerance in USD (default: 0.5)"
    )
    parser.add_argument(
        "--ppp-index",
        type=Path,
        default=DEFAULT_PPP_INDEX,
        help="Path to PPP index JSON"
    )
    
    args = parser.parse_args()
    
    # Load PPP index
    ppp_data = load_ppp_index(args.ppp_index)
    baseline_pp = ppp_data["baseline_value"]
    index = ppp_data["index"]
    
    # Fetch current prices
    current_prices = get_current_prices(args.subscription_id)
    
    # Compare
    results = []
    stats = {"aligned": 0, "underpriced": 0, "overpriced": 0, "missing": 0}
    
    for territory, territory_pp in index.items():
        carrier_cap = CARRIER_BILLING_PP_CAP if territory in CARRIER_BILLING_TERRITORIES else None
        
        # Calculate PPP recommendation
        raw_price = calculate_ppp_price(args.baseline_usd, baseline_pp, territory_pp, carrier_cap)
        ppp_recommended = round_to_psychological(raw_price)
        
        # Get current price
        current = current_prices.get(territory)
        
        if not current:
            status = "missing"
            current_price = None
            current_currency = ""
            diff = None
            stats["missing"] += 1
        else:
            current_price, current_currency = current
            
            # We can only compute a diff if the territory uses USD natively
            if current_currency == "USD":
                diff = current_price - ppp_recommended
                
                if abs(diff) <= args.tolerance:
                    status = "aligned"
                    stats["aligned"] += 1
                elif diff < 0:
                    status = "underpriced"
                    stats["underpriced"] += 1
                else:
                    status = "overpriced"
                    stats["overpriced"] += 1
            else:
                diff = None
                status = "unknown (non-USD)"
        
        row = {
            "territory": territory,
            "territory_name": get_territory_name(territory),
            "pp_index": territory_pp,
            "current_price": current_price,
            "current_currency": current_currency,
            "ppp_recommended_usd": ppp_recommended,
            "diff_usd": diff,
            "status": status,
            "carrier_billing": territory in CARRIER_BILLING_TERRITORIES,
            "currency_issue": territory in CURRENCY_CONVERSION_ISSUES,
        }
        
        # Apply filter
        if args.show_only == "misaligned" and status == "aligned":
            continue
        elif args.show_only == "underpriced" and status != "underpriced":
            continue
        elif args.show_only == "overpriced" and status != "overpriced":
            continue
        
        results.append(row)
    
    # Sort by absolute difference (only for those with a valid USD diff)
    results.sort(key=lambda x: abs(x["diff_usd"]) if x["diff_usd"] is not None else -1, reverse=True)
    
    # Output
    if args.output == "json":
        output_data = {
            "subscription_id": args.subscription_id,
            "baseline_usd": args.baseline_usd,
            "ppp_source": ppp_data["source"],
            "tolerance": args.tolerance,
            "stats": stats,
            "territories": results
        }
        print(json.dumps(output_data, indent=2))
    
    elif args.output == "csv":
        fieldnames = [
            "territory", "territory_name", "pp_index",
            "current_price", "current_currency", "ppp_recommended_usd", "diff_usd", "status"
        ]
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    else:  # table
        print(f"\n📊 PPP Price Comparison", file=sys.stderr)
        print(f"Subscription: {args.subscription_id}", file=sys.stderr)
        print(f"Baseline: ${args.baseline_usd} USD", file=sys.stderr)
        print(f"Tolerance: ±${args.tolerance}", file=sys.stderr)
        print(f"", file=sys.stderr)
        
        # Stats
        total = sum(stats.values())
        print(f"📈 Summary:", file=sys.stderr)
        print(f"   ✅ Aligned:      {stats['aligned']:3d} ({stats['aligned']/total*100:.0f}%)", file=sys.stderr)
        print(f"   ⬆️  Underpriced:  {stats['underpriced']:3d} ({stats['underpriced']/total*100:.0f}%) — leaving money on table", file=sys.stderr)
        print(f"   ⬇️  Overpriced:   {stats['overpriced']:3d} ({stats['overpriced']/total*100:.0f}%) — could hurt conversions", file=sys.stderr)
        print(f"   ❓ Missing:      {stats['missing']:3d} ({stats['missing']/total*100:.0f}%) — no current price set", file=sys.stderr)
        print(f"", file=sys.stderr)
        
        if not results:
            print("No territories match the filter.\n")
            return
        
        # Table
        print("Territory       | PP    | Current       | PPP Rec | Diff   | Status")
        print("----------------|-------|---------------|---------|--------|------------")
        
        for row in results:
            territory_display = f"{row['territory']} ({row['territory_name'][:10]})"
            pp = f"{row['pp_index']:.1f}"
            current = f"{row['current_price']:.2f} {row['current_currency']}" if row['current_price'] else "—"
            recommended = f"${row['ppp_recommended_usd']:.2f}"
            
            if row['diff_usd'] is not None:
                diff = f"{row['diff_usd']:+.2f}"
                
                if row['status'] == "aligned":
                    status = "✅ OK"
                elif row['status'] == "underpriced":
                    status = "⬆️ Under"
                elif row['status'] == "overpriced":
                    status = "⬇️ Over"
            else:
                diff = "—"
                if row['status'] == "unknown (non-USD)":
                    status = "🌐 Local"
                else:
                    status = "❓ Missing"
            
            print(f"{territory_display:16}| {pp:5} | {current:13} | {recommended:7} | {diff:6} | {status}")
        
        print()


if __name__ == "__main__":
    main()
