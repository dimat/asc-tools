#!/usr/bin/env python3
"""
Calculate PPP-adjusted prices for all territories without applying them.

Shows what the prices WOULD be based on PPP index, useful for:
- Preview before applying changes
- Export for stakeholder review
- Compare different baseline strategies

Usage:
    python calculate_ppp_prices.py --baseline 7.99
    python calculate_ppp_prices.py --baseline 7.99 --output csv
    python calculate_ppp_prices.py --baseline 7.99 --output json > prices.json

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_PPP_INDEX = DATA_DIR / "ppp-index-numbeo-2026.json"

# Carrier-billing territories where PP is capped
CARRIER_BILLING_TERRITORIES = {"RUS", "BLR", "UZB", "TJK", "KGZ", "AZE", "ARM", "GEO", "MDA"}
CARRIER_BILLING_PP_CAP = 80.0

# Currency conversion issue territories
CURRENCY_CONVERSION_ISSUES = {
    "HUN", "IDN", "NGA", "KOR", "JPN", "PAK", "TZA", "VNM", "KAZ"
}

# --- Utilities ---

def load_ppp_index(path: Path) -> Dict:
    """Load PPP index from JSON file."""
    with open(path) as f:
        return json.load(f)


def calculate_ppp_price(
    baseline_usd: float,
    baseline_pp: float,
    territory_pp: float,
    carrier_billing_cap: Optional[float] = None
) -> float:
    """
    Calculate PPP-adjusted price.
    
    Formula: target_price = baseline_price * (territory_PP / baseline_PP)
    
    If carrier_billing_cap is set and territory_PP < cap, use cap instead.
    """
    effective_pp = territory_pp
    if carrier_billing_cap and territory_pp < carrier_billing_cap:
        effective_pp = carrier_billing_cap
    
    return baseline_usd * (effective_pp / baseline_pp)


def round_to_psychological(price: float) -> float:
    """Round to .99 or .49 ending."""
    if price < 1.0:
        return 0.99
    
    integer_part = int(price)
    
    # Try .99 first
    option_99 = integer_part + 0.99
    option_49 = integer_part + 0.49
    
    if abs(price - option_99) < abs(price - option_49):
        return option_99
    else:
        return option_49


def get_territory_name(territory_code: str) -> str:
    """Get human-readable territory name (simplified)."""
    # Could be extended with full ISO 3166-1 lookup
    common_names = {
        "USA": "United States",
        "GBR": "United Kingdom",
        "DEU": "Germany",
        "FRA": "France",
        "JPN": "Japan",
        "CHN": "China",
        "IND": "India",
        "BRA": "Brazil",
        "RUS": "Russia",
        "CAN": "Canada",
        "AUS": "Australia",
        "MEX": "Mexico",
        "KOR": "South Korea",
        "ESP": "Spain",
        "ITA": "Italy",
        "NLD": "Netherlands",
        "CHE": "Switzerland",
        "SWE": "Sweden",
        "POL": "Poland",
        "TUR": "Turkey",
        "IDN": "Indonesia",
        "THA": "Thailand",
        "SGP": "Singapore",
        "MYS": "Malaysia",
        "PHL": "Philippines",
        "VNM": "Vietnam",
        "ARE": "United Arab Emirates",
        "SAU": "Saudi Arabia",
        "ZAF": "South Africa",
        "EGY": "Egypt",
        "NGA": "Nigeria",
        "ARG": "Argentina",
        "CHL": "Chile",
        "COL": "Colombia",
        "PER": "Peru",
        "UKR": "Ukraine",
        "ROU": "Romania",
        "CZE": "Czech Republic",
        "HUN": "Hungary",
        "GRC": "Greece",
        "PRT": "Portugal",
        "IRL": "Ireland",
        "NZL": "New Zealand",
        "ISR": "Israel",
        "HKG": "Hong Kong",
        "TWN": "Taiwan",
    }
    return common_names.get(territory_code, territory_code)


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Calculate PPP-adjusted prices for all territories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all prices for $7.99 baseline
  python calculate_ppp_prices.py --baseline 7.99

  # Export as CSV
  python calculate_ppp_prices.py --baseline 7.99 --output csv > prices.csv

  # Export as JSON
  python calculate_ppp_prices.py --baseline 7.99 --output json > prices.json

  # Compare multiple baselines
  python calculate_ppp_prices.py --baseline 4.99 --baseline 7.99 --baseline 9.99
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
        "--output",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--ppp-index",
        type=Path,
        default=DEFAULT_PPP_INDEX,
        help="Path to PPP index JSON"
    )
    parser.add_argument(
        "--sort-by",
        choices=["territory", "pp", "price"],
        default="territory",
        help="Sort results by territory code, PP index, or adjusted price"
    )
    parser.add_argument(
        "--show-flags",
        action="store_true",
        help="Show carrier-billing and currency-issue flags"
    )
    
    args = parser.parse_args()
    
    # Load PPP index
    ppp_data = load_ppp_index(args.ppp_index)
    baseline_pp = ppp_data["baseline_value"]
    baseline_country = ppp_data["baseline_country"]
    index = ppp_data["index"]
    
    # Calculate for each territory
    results = []
    
    for territory, territory_pp in index.items():
        carrier_cap = CARRIER_BILLING_PP_CAP if territory in CARRIER_BILLING_TERRITORIES else None
        has_currency_issue = territory in CURRENCY_CONVERSION_ISSUES
        
        row = {
            "territory": territory,
            "territory_name": get_territory_name(territory),
            "pp_index": territory_pp,
            "carrier_billing": territory in CARRIER_BILLING_TERRITORIES,
            "currency_issue": has_currency_issue,
        }
        
        for baseline_usd in args.baseline:
            raw_price = calculate_ppp_price(baseline_usd, baseline_pp, territory_pp, carrier_cap)
            rounded_price = round_to_psychological(raw_price)
            
            key = f"baseline_{baseline_usd:.2f}".replace(".", "_")
            row[f"{key}_raw"] = raw_price
            row[f"{key}_rounded"] = rounded_price
        
        results.append(row)
    
    # Sort
    if args.sort_by == "territory":
        results.sort(key=lambda x: x["territory"])
    elif args.sort_by == "pp":
        results.sort(key=lambda x: x["pp_index"])
    elif args.sort_by == "price":
        # Sort by first baseline
        first_baseline = args.baseline[0]
        key = f"baseline_{first_baseline:.2f}_rounded".replace(".", "_")
        results.sort(key=lambda x: x[key])
    
    # Output
    if args.output == "json":
        output_data = {
            "source": ppp_data["source"],
            "baseline_country": baseline_country,
            "baseline_pp": baseline_pp,
            "baselines_usd": args.baseline,
            "territories": results
        }
        print(json.dumps(output_data, indent=2))
    
    elif args.output == "csv":
        fieldnames = ["territory", "territory_name", "pp_index"]
        
        if args.show_flags:
            fieldnames += ["carrier_billing", "currency_issue"]
        
        for baseline_usd in args.baseline:
            key = f"baseline_{baseline_usd:.2f}".replace(".", "_")
            fieldnames.append(f"{key}_rounded")
        
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    
    else:  # table
        # Print header
        print(f"📊 PPP Price Calculator")
        print(f"Source: {ppp_data['source']}")
        print(f"Baseline: {baseline_country} (PP={baseline_pp})")
        print()
        
        # Print baselines
        print(f"Baselines (USD): {', '.join(f'${b:.2f}' for b in args.baseline)}")
        print()
        
        # Table header
        header_cols = ["Territory", "PP Index"]
        for baseline_usd in args.baseline:
            header_cols.append(f"${baseline_usd:.2f}")
        
        if args.show_flags:
            header_cols.append("Flags")
        
        # Calculate column widths
        widths = [max(len(h), 15) for h in header_cols]
        
        # Print header
        print(" | ".join(h.ljust(w) for h, w in zip(header_cols, widths)))
        print("-+-".join("-" * w for w in widths))
        
        # Print rows
        for row in results:
            cols = [
                f"{row['territory']} ({row['territory_name'][:10]})",
                f"{row['pp_index']:.1f}"
            ]
            
            for baseline_usd in args.baseline:
                key = f"baseline_{baseline_usd:.2f}_rounded".replace(".", "_")
                cols.append(f"${row[key]:.2f}")
            
            if args.show_flags:
                flags = []
                if row["carrier_billing"]:
                    flags.append("CB")
                if row["currency_issue"]:
                    flags.append("CI")
                cols.append(", ".join(flags) if flags else "")
            
            print(" | ".join(c.ljust(w) for c, w in zip(cols, widths)))
        
        print()
        print(f"Total territories: {len(results)}")
        
        if args.show_flags:
            print()
            print("Flags:")
            print("  CB = Carrier-billing cap applied (PP < 80 → PP = 80)")
            print("  CI = Currency conversion issue (needs manual review)")


if __name__ == "__main__":
    main()
