#!/usr/bin/env python3
"""
Apply PPP (Purchasing Power Parity) pricing to App Store subscriptions.

Uses the ASC CLI to update subscription prices across all territories
based on a PPP index (default: Numbeo 2026).

Features:
- Automatic price point matching (finds closest valid ASC price)
- Psychological pricing rounding (.99, .49 endings)
- Carrier-billing country handling (caps PP to avoid microtransactions)
- Preserved pricing flag (existing customers keep current price)
- Dry-run mode
- Progress logging

Usage:
    python apply_ppp_pricing.py \\
        --app-id 1584962857 \\
        --subscription-group 20883030 \\
        --monthly-id 1586316851 --monthly-baseline 7.99 \\
        --annual-id 1586316153 --annual-baseline 69.99 \\
        --start-date 2026-04-14 \\
        --preserved

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_PPP_INDEX = DATA_DIR / "ppp-index-numbeo-2026.json"

# Territories to skip by default (usually just baseline)
# For strategic markets you want manual control over, pass via --skip-territories
SKIP_TERRITORIES = {"USA"}  # Baseline only

# Carrier-billing territories where PP is capped to avoid microtransactions
CARRIER_BILLING_TERRITORIES = {"RUS", "BLR", "UZB", "TJK", "KGZ", "AZE", "ARM", "GEO", "MDA"}
CARRIER_BILLING_PP_CAP = 80.0

# Currency-conversion issue territories (prices set too low, needs manual review)
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
    import os
    env = os.environ.copy()
    env["ASC_TIMEOUT"] = "120s"  # Increase timeout for slow Apple APIs
    
    cmd = ["asc"] + args
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    else:
        return subprocess.run(cmd, check=False, env=env)


def get_proposed_prices(subscription_id: str, target_usd: float) -> Dict[str, Tuple[float, str]]:
    """
    Fetch what Apple would set the local price to if we applied target_usd.
    Uses disk caching to prevent 40+ API calls on subsequent runs.
    Returns dict: {territory: (local_price_number, price_point_id)}
    """
    cache_dir = DATA_DIR / ".cache"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"proposed_{subscription_id}_{target_usd:.2f}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                data = json.load(f)
            # Reconstruct tuples
            return {terr: (float(val[0]), val[1]) for terr, val in data.items()}
        except Exception:
            pass # fallback to API
            
    print(f"   Fetching local currency mapping for ${target_usd:.2f}...")
    result = run_asc([
        "subscriptions", "pricing", "equalize",
        "--subscription-id", subscription_id,
        "--base-price", str(target_usd),
        "--dry-run", "--output", "json"
    ])
    
    if result.returncode != 0:
        print(f"❌ Failed to calculate proposed prices for ${target_usd}: {result.stderr}")
        return {}
        
    try:
        data = json.loads(result.stdout)
        proposed = {}
        for terr in data.get("territories", []):
            proposed[terr["territory"]] = (float(terr["price"]), terr["pricePointId"])
            
        # Save to cache
        with open(cache_file, "w") as f:
            json.dump(proposed, f)
            
        return proposed
    except json.JSONDecodeError:
        print("❌ Invalid JSON response for proposed prices")
        return {}


def extract_tier_from_price_point(price_point_id: str) -> Optional[int]:
    """
    Extract the universal tier ID from a Base64-encoded subscriptionPricePoint ID.
    The 'p' field in the decoded JSON contains the tier.
    """
    import base64
    import json
    try:
        # Add padding if needed
        padded = price_point_id + '=' * (-len(price_point_id) % 4)
        decoded = base64.b64decode(padded).decode('utf-8')
        data = json.loads(decoded)
        return int(data.get("p"))
    except Exception:
        return None


def get_usa_price_points(subscription_id: str) -> Dict[float, str]:
    """
    Fetch USA price points to map USD prices to Tier IDs.
    Returns dict: {usd_price: tier_id}
    """
    result = run_asc([
        "subscriptions", "pricing", "price-points", "list",
        "--subscription-id", subscription_id,
        "--territory", "USA",
        "--paginate", "--output", "json"
    ])
    
    if result.returncode != 0:
        print(f"❌ Failed to fetch USA price points: {result.stderr}")
        sys.exit(1)
        
    try:
        data = json.loads(result.stdout)
        mapping = {}
        for pp in data.get("data", []):
            attrs = pp.get("attributes", {})
            customer_price = attrs.get("customerPrice")
            
            pp_id = pp["id"]
            
            if customer_price is not None:
                mapping[float(customer_price)] = pp_id
                
        return mapping
    except json.JSONDecodeError:
        print("❌ Invalid JSON response for USA price points")
        sys.exit(1)


def find_closest_usd_price(
    usd_price_points: Dict[float, str],
    target_usd: float,
    prefer_99_ending: bool = True
) -> Optional[Tuple[float, str]]:
    """
    Find closest USD price point.
    Returns (matched_usd_price, price_point_id)
    """
    if not usd_price_points:
        return None
        
    available_prices = list(usd_price_points.keys())
    available_prices.sort(key=lambda x: abs(x - target_usd))
    
    if prefer_99_ending:
        for price in available_prices[:5]:
            price_str = f"{price:.2f}"
            if price_str.endswith(".99") or price_str.endswith(".49"):
                return price, usd_price_points[price]
                
    best_price = available_prices[0]
    return best_price, usd_price_points[best_price]


def extract_tier_from_price_point(price_point_id: str) -> Optional[int]:
    """
    Extract the universal tier ID from a Base64-encoded subscriptionPricePoint ID.
    The 'p' field in the decoded JSON contains the tier.
    """
    import base64
    import json
    try:
        padded = price_point_id + '=' * (-len(price_point_id) % 4)
        decoded = base64.b64decode(padded).decode('utf-8')
        data = json.loads(decoded)
        return int(data.get("p"))
    except Exception:
        return None


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


def schedule_price_change(
    subscription_id: str,
    territory: str,
    tier_id: Optional[int] = None,
    price_point_id: Optional[str] = None,
    start_date: str = "",
    preserved: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Schedule a subscription price change via ASC API.
    
    Returns True on success, False otherwise.
    """
    cmd = [
        "subscriptions", "pricing", "prices", "set",
        "--subscription-id", subscription_id,
        "--territory", territory,
        "--start-date", start_date,
        "--output", "json"
    ]
    
    if price_point_id:
        cmd.extend(["--price-point", price_point_id])
    elif tier_id:
        cmd.extend(["--tier", str(tier_id)])
    
    if preserved:
        cmd.append("--preserved")
    
    if dry_run:
        print(f"  [DRY RUN] Would run: asc {' '.join(cmd)}")
        return True
    
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = run_asc(cmd)
            
            if result.returncode != 0:
                error = result.stderr.strip() if result.stderr else result.stdout.strip()
                
                if "context deadline exceeded" in error and attempt < max_retries - 1:
                    print(f"  ⚠️ Timeout. Retrying ({attempt+1}/{max_retries})...", end="")
                    time.sleep(2)
                    continue
                    
                if "more than one future prices" in error.lower():
                    print("  ⏭️  Already scheduled (future price exists)")
                    return True  # Treat as success to continue
                    
                print(f"  ❌ Error: {error}")
                return False
            
            return True
        except Exception as e:
            if "Timeout" in str(e) and attempt < max_retries - 1:
                print(f"  ⚠️ Exception Timeout. Retrying ({attempt+1}/{max_retries})...", end="")
                time.sleep(2)
                continue
                
            print(f"  ❌ Exception: {e}")
            return False
            
    return False


def get_current_prices(app_id: str, subscription_id: str) -> Dict[str, Tuple[float, str]]:
    """
    Fetch current subscription prices from ASC.
    Returns dict: {territory_code: (customer_price, currency)}
    """
    result = run_asc([
        "subscriptions", "pricing", "prices", "list",
        "--subscription-id", subscription_id,
        "--resolved", "--output", "json"
    ])
    
    prices = {}
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            for price_entry in data.get("prices", []):
                territory_id = price_entry.get("territory")
                customer_price = price_entry.get("customerPrice")
                currency = price_entry.get("currency", "USD")
                
                if territory_id and customer_price is not None:
                    prices[territory_id] = (float(customer_price), currency)
        except json.JSONDecodeError:
            pass
            
    # Fallback: If resolved prices are empty (e.g., equalized prices not yet materialized),
    # use the raw prices endpoint to find explicit overrides
    if not prices:
        raw_result = run_asc([
            "get", f"/v1/subscriptions/{subscription_id}/prices",
            "limit=200", "include=subscriptionPricePoint,territory"
        ])
        if raw_result.returncode == 0:
            try:
                raw_data = json.loads(raw_result.stdout)
                included = {item["id"]: item for item in raw_data.get("included", [])}
                
                for price_entry in raw_data.get("data", []):
                    territory_rel = price_entry.get("relationships", {}).get("territory", {}).get("data")
                    if not territory_rel: continue
                        
                    price_point_rel = price_entry.get("relationships", {}).get("subscriptionPricePoint", {}).get("data")
                    if not price_point_rel: continue
                        
                    price_point = included.get(price_point_rel["id"])
                    if not price_point: continue
                        
                    customer_price = price_point.get("attributes", {}).get("customerPrice")
                    if customer_price is not None:
                        prices[territory_rel["id"]] = (float(customer_price), "USD") # ASC generic endpoint assumes USD tier base
            except json.JSONDecodeError:
                pass
                
    return prices

def get_territory_name(territory_code: str) -> str:
    """Get simplified territory name."""
    common = {"USA": "USA", "GBR": "UK", "DEU": "Germany", "FRA": "France", "IND": "India", "BRA": "Brazil"}
    return common.get(territory_code, territory_code)


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Apply PPP pricing to App Store subscriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run for Carousel app
  python apply_ppp_pricing.py \\
      --app-id 1584962857 \\
      --subscription-group 20883030 \\
      --monthly-id 1586316851 --monthly-baseline 7.99 \\
      --annual-id 1586316153 --annual-baseline 69.99 \\
      --start-date 2026-04-14 \\
      --dry-run

  # Apply with preserved pricing
  python apply_ppp_pricing.py \\
      --app-id 1584962857 \\
      --subscription-group 20883030 \\
      --monthly-id 1586316851 --monthly-baseline 7.99 \\
      --annual-id 1586316153 --annual-baseline 69.99 \\
      --start-date 2026-04-14 \\
      --preserved
        """
    )
    
    parser.add_argument("--app-id", required=True, help="App Store app ID")
    parser.add_argument("--subscription-group", required=True, help="Subscription group ID")
    
    parser.add_argument("--monthly-id", help="Monthly subscription ID")
    parser.add_argument("--monthly-baseline", type=float, help="Monthly baseline price (USD)")
    
    parser.add_argument("--annual-id", help="Annual subscription ID")
    parser.add_argument("--annual-baseline", type=float, help="Annual baseline price (USD)")
    
    parser.add_argument("--weekly-id", help="Weekly subscription ID")
    parser.add_argument("--weekly-baseline", type=float, help="Weekly baseline price (USD)")
    
    parser.add_argument("--subscription-id", help="Generic subscription ID (if not weekly/monthly/annual)")
    parser.add_argument("--subscription-baseline", type=float, help="Generic baseline price (USD)")
    
    parser.add_argument("--start-date", required=True, help="Price change start date (YYYY-MM-DD)")
    parser.add_argument("--preserved", action="store_true", help="Preserve current price for existing customers")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without making changes")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    
    parser.add_argument("--ppp-index", type=Path, default=DEFAULT_PPP_INDEX, help="Path to PPP index JSON")
    parser.add_argument("--skip-territories", help="Comma-separated list of territories to skip")
    
    args = parser.parse_args()
    
    # Validate
    if not any([args.monthly_id, args.annual_id, args.weekly_id, args.subscription_id]):
        print("❌ At least one subscription ID is required")
        sys.exit(1)
    
    if args.monthly_id and not args.monthly_baseline:
        print("❌ --monthly-baseline is required when --monthly-id is provided")
        sys.exit(1)
    
    if args.annual_id and not args.annual_baseline:
        print("❌ --annual-baseline is required when --annual-id is provided")
        sys.exit(1)
        
    if args.weekly_id and not args.weekly_baseline:
        print("❌ --weekly-baseline is required when --weekly-id is provided")
        sys.exit(1)
        
    if args.subscription_id and not args.subscription_baseline:
        print("❌ --subscription-baseline is required when --subscription-id is provided")
        sys.exit(1)
    
    # Load PPP index
    print(f"📊 Loading PPP index: {args.ppp_index}")
    ppp_data = load_ppp_index(args.ppp_index)
    baseline_pp = ppp_data["baseline_value"]
    index = ppp_data["index"]
    
    print(f"   Baseline: {ppp_data['baseline_country']} (PP={baseline_pp})")
    print(f"   Source: {ppp_data['source']}")
    print()
    
    # Parse skip list
    skip_set = set(SKIP_TERRITORIES)
    if args.skip_territories:
        skip_set.update(args.skip_territories.split(","))
    
    print(f"⏭️  Skipping {len(skip_set)} territories: {', '.join(sorted(skip_set))}")
    print()
    
    # Get all territories from the PPP index
    print("🌍 Getting territories from index...")
    all_territories = list(index.keys())
    
    print(f"   Found {len(all_territories)} territories")
    print()
    
    # Filter
    territories_to_process = [t for t in all_territories if t not in skip_set]
    print(f"🎯 Processing {len(territories_to_process)} territories")
    print()
    
    # Process subscriptions
    subscriptions = []
    if args.monthly_id:
        subscriptions.append(("Monthly", args.monthly_id, args.monthly_baseline))
    if args.annual_id:
        subscriptions.append(("Annual", args.annual_id, args.annual_baseline))
    if args.weekly_id:
        subscriptions.append(("Weekly", args.weekly_id, args.weekly_baseline))
    if args.subscription_id:
        subscriptions.append(("Subscription", args.subscription_id, args.subscription_baseline))
    
    stats = {"applied": 0, "skipped": 0, "errors": 0}
    
    for sub_name, sub_id, baseline_usd in subscriptions:
        print(f"💰 {sub_name} Subscription (ID: {sub_id}, baseline: ${baseline_usd})")
        print("=" * 80)
        
        # --- PHASE 1: PLAN & REVIEW ---
        print("🔍 Fetching current prices for comparison...")
        current_prices = get_current_prices(args.app_id, sub_id)
        
        print("🔍 Fetching USA base price points...")
        usa_price_points = get_usa_price_points(sub_id)
        
        print("🔍 Fetching current local prices for all territories...")
        planned_changes = []
        
        # Calculate target USD for each territory to minimize API calls
        targets_usd = {}
        for territory in territories_to_process:
            territory_pp = index.get(territory)
            if not territory_pp: continue
            
            carrier_cap = CARRIER_BILLING_PP_CAP if territory in CARRIER_BILLING_TERRITORIES else None
            target_usd = calculate_ppp_price(baseline_usd, baseline_pp, territory_pp, carrier_cap)
            target_rounded = round_to_psychological(target_usd)
            targets_usd[territory] = target_rounded
            
        # Get unique target USD prices
        unique_targets = set(targets_usd.values())
        
        # We must fetch proposed local prices for ALL unique target USD prices,
        # because this is the ONLY way to get the exact territory-specific pricePointId 
        # (e.g. the base64 string for ALB specifically) that Apple requires for 'prices set'.
        unique_targets = set(targets_usd.values())
                    
        proposed_by_target = {}
        print("🔍 Resolving local currency mappings...")
        for tgt in unique_targets:
            proposed_by_target[tgt] = get_proposed_prices(sub_id, tgt)
            
        for territory in territories_to_process:
            if territory not in targets_usd:
                continue
                
            territory_pp = index.get(territory)
            target_usd = targets_usd[territory]
            
            curr_data = current_prices.get(territory)
            curr_price = curr_data[0] if curr_data else None
            curr_currency = curr_data[1] if curr_data else ""
            
            # Map target USD to explicit Tier via USA price points
            match = find_closest_usd_price(usa_price_points, target_usd)
            if not match:
                print(f"  {territory}: ❌ No valid USA price point found for mapping")
                stats["errors"] += 1
                continue
                
            matched_usd, usa_price_point_id = match
            tier_id = extract_tier_from_price_point(usa_price_point_id)
            
            # Look up proposed local price and exact local price point ID
            proposed_local_price = None
            local_price_point_id = None
            if target_usd in proposed_by_target:
                proposed_data = proposed_by_target[target_usd].get(territory)
                if proposed_data:
                    proposed_local_price, local_price_point_id = proposed_data
            
            planned_changes.append({
                "territory": territory,
                "pp": territory_pp,
                "current_price": curr_price,
                "current_currency": curr_currency,
                "target_usd": target_usd,
                "proposed_local": proposed_local_price,
                "matched_usd": matched_usd,
                "tier_id": tier_id,
                "local_price_point_id": local_price_point_id
            })
            
        # Print table
        print("\n📋 Planned Changes Preview:")
        
        # Check if we have any current prices
        has_any_current = any(p["current_price"] is not None for p in planned_changes)
        if not has_any_current:
            print("   ℹ️ Note: Current prices are showing as '—' because this subscription")
            print("      currently uses auto-equalized pricing. Once explicit PPP prices")
            print("      are applied, future dry-runs will show current values & diffs.")
            print()
            
        print("Territory | PP Index | Current (Local) | Proposed (Local) | Target (USD) | Mapped Tier (USD) | Diff (Local)")
        print("----------+----------+-----------------+------------------+--------------+-------------------+-------------")
        
        for p in planned_changes:
            terr = p["territory"].ljust(9)
            pp = f"{p['pp']:.1f}".rjust(8)
            
            if p["current_price"] is not None:
                curr = f"{p['current_price']:.2f} {p['current_currency']}".rjust(15)
                curr_code = p['current_currency']
            else:
                curr = "—".rjust(15)
                curr_code = ""
                
            if p["proposed_local"] is not None:
                prop = f"{p['proposed_local']:.2f} {curr_code}".strip().rjust(16)
            else:
                prop = "—".rjust(16)
                
            tgt = f"${p['target_usd']:.2f}".rjust(12)
            tier_disp = f"Tier {p['tier_id']} (${p['matched_usd']:.2f})".rjust(17)
            
            diff_str = "—".rjust(12)
            if p["current_price"] is not None and p["proposed_local"] is not None:
                diff = p["proposed_local"] - p["current_price"]
                diff_str = f"{diff:+.2f} {curr_code}".strip().rjust(12)
                
            print(f"{terr} | {pp} | {curr} | {prop} | {tgt} | {tier_disp} | {diff_str}")
        
        print("-" * 92)
        print(f"Total territories to update: {len(planned_changes)}")
        print()
        
        if not args.yes:
            reply = input("Proceed with applying these prices? (y/N): ").strip().lower()
            if reply != 'y':
                print("⏭️  Skipping this subscription.\n")
                continue
            print()
        
        # --- PHASE 2: EXECUTE ---
        print(f"🚀 Applying prices...")
        
        for p in planned_changes:
            territory = p["territory"]
            matched_usd = p["matched_usd"]
            tier_id = p["tier_id"]
            local_price_point_id = p["local_price_point_id"]
            proposed_local = p["proposed_local"]
            territory_pp = p["pp"]
            
            if not local_price_point_id:
                print(f"  {territory}: ❌ Missing local price point ID mapping. Cannot schedule.")
                stats["errors"] += 1
                continue
            
            prop_disp = f"{proposed_local:.2f}" if proposed_local is not None else "Unknown"
            print(f"  {territory}: PP={territory_pp:.1f}, target=${matched_usd:.2f}, local={prop_disp} (Tier {tier_id})", end="")
            
            # Schedule price change using the EXACT LOCAL price point ID (e.g. ALB-specific ID)
            success = schedule_price_change(
                sub_id,
                territory,
                tier_id=None,
                price_point_id=local_price_point_id,
                start_date=args.start_date,
                preserved=args.preserved,
                dry_run=args.dry_run
            )
            
            if success:
                print(" ✅")
                stats["applied"] += 1
            else:
                stats["errors"] += 1
            
            if not args.dry_run:
                time.sleep(0.5)  # Rate limit courtesy
        
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Summary:")
    print(f"   ✅ Applied: {stats['applied']}")
    print(f"   ⏭️  Skipped: {stats['skipped']}")
    print(f"   ❌ Errors: {stats['errors']}")
    
    if args.dry_run:
        print()
        print("   [DRY RUN] No changes were made")


if __name__ == "__main__":
    main()
