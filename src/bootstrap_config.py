#!/usr/bin/env python3
"""
Interactive config bootstrapper - creates app config from App Store Connect data.

Fetches your apps, subscription groups, and subscriptions via ASC CLI,
then generates a ready-to-use config file.

Usage:
    python bootstrap_config.py
    python bootstrap_config.py --app-id 1234567890
    python bootstrap_config.py --app-id 1234567890 --output configs/myapp.yaml

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
CONFIGS_DIR = SCRIPT_DIR.parent / "configs"
APPS_DIR = CONFIGS_DIR / "apps"

# --- ASC CLI Utilities ---

def run_asc(args: List[str]) -> Tuple[bool, str]:
    """Run ASC CLI command and return (success, output)."""
    cmd = ["asc"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return False, result.stderr.strip()
    
    return True, result.stdout.strip()


def fetch_apps() -> List[Dict]:
    """Fetch all apps from ASC."""
    success, output = run_asc(["apps", "list", "--limit", "200", "--output", "json"])
    
    if not success:
        print(f"❌ Failed to fetch apps: {output}")
        return []
    
    try:
        data = json.loads(output)
        apps = []
        
        for app in data.get("data", []):
            attrs = app.get("attributes", {})
            apps.append({
                "id": app["id"],
                "name": attrs.get("name", "Unknown"),
                "bundle_id": attrs.get("bundleId", "")
            })
        
        return apps
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response")
        return []


def fetch_subscription_groups(app_id: str) -> List[Dict]:
    """Fetch subscription groups for an app."""
    success, output = run_asc(["subscriptions", "groups", "list", "--app", app_id, "--output", "json"])
    
    if not success:
        print(f"❌ Failed to fetch subscription groups: {output}")
        return []
    
    try:
        data = json.loads(output)
        groups = []
        
        for group in data.get("data", []):
            attrs = group.get("attributes", {})
            groups.append({
                "id": group["id"],
                "name": attrs.get("referenceName", "Unknown")
            })
        
        return groups
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response")
        return []


def fetch_subscriptions(group_id: str) -> List[Dict]:
    """Fetch subscriptions in a group."""
    success, output = run_asc(["subscriptions", "list", "--group-id", group_id, "--output", "json"])
    
    if not success:
        print(f"❌ Failed to fetch subscriptions: {output}")
        return []
    
    try:
        data = json.loads(output)
        subs = []
        
        for sub in data.get("data", []):
            attrs = sub.get("attributes", {})
            name = attrs.get("name", "Unknown")
            product_id = attrs.get("productId", "")
            
            # Infer type from name or product ID
            name_lower = name.lower()
            product_lower = product_id.lower()
            
            if "week" in name_lower or "week" in product_lower:
                sub_type = "weekly"
            elif "month" in name_lower or "month" in product_lower:
                sub_type = "monthly"
            elif "annual" in name_lower or "year" in name_lower or "annual" in product_lower or "year" in product_lower:
                sub_type = "annual"
            else:
                sub_type = "subscription"
            
            subs.append({
                "id": sub["id"],
                "name": name,
                "product_id": product_id,
                "type": sub_type
            })
        
        return subs
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response")
        return []


def fetch_current_usd_price(app_id: str, subscription_id: str) -> Optional[float]:
    """Fetch the current USD price for a subscription via summary endpoint."""
    success, output = run_asc([
        "subscriptions", "pricing", "summary",
        "--app", str(app_id),
        "--output", "json"
    ])
    
    if not success:
        return None
        
    try:
        data = json.loads(output)
        for sub in data.get("subscriptions", []):
            if str(sub.get("id")) == str(subscription_id):
                price = sub.get("currentPrice", {}).get("amount")
                if price is not None:
                    return float(price)
    except json.JSONDecodeError:
        pass
        
    return None


# --- Interactive UI ---

def select_from_list(items: List[Dict], key: str, prompt: str) -> Optional[Dict]:
    """Interactive list selection."""
    if not items:
        print("❌ No items available")
        return None
    
    if len(items) == 1:
        print(f"✅ Auto-selected: {items[0][key]}")
        return items[0]
    
    print(f"\n{prompt}")
    print("-" * 60)
    
    for i, item in enumerate(items, 1):
        print(f"{i}. {item[key]}")
    
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"Select (1-{len(items)}): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(items):
                return items[idx]
            else:
                print(f"❌ Invalid choice. Enter 1-{len(items)}")
        except ValueError:
            print(f"❌ Invalid input. Enter a number 1-{len(items)}")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled")
            sys.exit(0)


def multiselect_from_list(items: List[Dict], key: str, prompt: str) -> List[Dict]:
    """Interactive multi-select."""
    if not items:
        return []
    
    print(f"\n{prompt}")
    print("-" * 60)
    
    for i, item in enumerate(items, 1):
        print(f"{i}. [{item['type']:8}] {item[key]}")
    
    print("-" * 60)
    print("Enter numbers separated by commas (e.g., 1,3,4) or 'all'")
    
    while True:
        try:
            choice = input("Select: ").strip().lower()
            
            if choice == "all":
                return items
            
            if not choice:
                return []
            
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected = [items[i] for i in indices if 0 <= i < len(items)]
            
            if selected:
                return selected
            else:
                print("❌ Invalid selection")
        except (ValueError, IndexError):
            print("❌ Invalid input. Use numbers separated by commas")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled")
            sys.exit(0)


def prompt_baseline_price(sub_name: str, current_price: Optional[float] = None) -> float:
    """Prompt for baseline price, offering current USD price as default if available."""
    default_prompt = f" [default: {current_price}]" if current_price else ""
    
    while True:
        try:
            price_str = input(f"Baseline price for '{sub_name}' (USD){default_prompt}: $").strip()
            
            if not price_str and current_price:
                return current_price
                
            price = float(price_str)
            
            if price > 0:
                return price
            else:
                print("❌ Price must be > 0")
        except ValueError:
            print("❌ Invalid price. Enter a number (e.g., 7.99)")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled")
            sys.exit(0)


def select_ppp_index() -> str:
    """Interactive PPP index selection."""
    indexes = [
        {"name": "Numbeo (Cost of Living)", "file": "ppp-index-numbeo-2026.json", "desc": "Broad consumer basket, 116 territories"},
        {"name": "Big Mac", "file": "ppp-index-bigmac-2026.json", "desc": "Consumer goods, 57 territories"},
        {"name": "Netflix", "file": "ppp-index-netflix-2026.json", "desc": "Digital entertainment, 58 territories"},
        {"name": "Spotify", "file": "ppp-index-spotify-2026.json", "desc": "Music/lifestyle, 58 territories"},
    ]
    
    print("\n📊 Select PPP Index")
    print("-" * 60)
    
    for i, idx in enumerate(indexes, 1):
        print(f"{i}. {idx['name']:25} - {idx['desc']}")
    
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"Select (1-{len(indexes)}): ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(indexes):
                return indexes[idx]["file"]
            else:
                print(f"❌ Invalid choice. Enter 1-{len(indexes)}")
        except ValueError:
            print(f"❌ Invalid input. Enter a number 1-{len(indexes)}")
        except KeyboardInterrupt:
            print("\n\n❌ Cancelled")
            sys.exit(0)


# --- Config Generation ---

def generate_config(
    app: Dict,
    group: Dict,
    subscriptions: List[Dict],
    ppp_index: str,
    skip_territories: List[str]
) -> Dict:
    """Generate config dictionary."""
    # Calculate default start date (14 days from now)
    start_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    
    config = {
        "app_name": app["name"],
        "app_id": int(app["id"]),
        "subscription_group": int(group["id"]),
        "subscriptions": [
            {
                "type": sub["type"],
                "id": int(sub["id"]),
                "baseline": sub.get("baseline", 0.0)
            }
            for sub in subscriptions
        ],
        "ppp_index": ppp_index,
        "skip_territories": skip_territories,
        "start_date": start_date,
        "preserved": True
    }
    
    return config


def save_config(config: Dict, output_path: Path, format: str = "yaml"):
    """Save config to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "yaml":
        if not HAS_YAML:
            print("⚠️  PyYAML not installed. Install: pip install pyyaml")
            print("   Falling back to JSON format")
            format = "json"
            output_path = output_path.with_suffix(".json")
    
    with open(output_path, "w") as f:
        if format == "yaml":
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(config, f, indent=2)
    
    print(f"\n✅ Config saved: {output_path}")


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Interactive config bootstrapper for ASC Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--app-id", help="Skip app selection, use this app ID")
    parser.add_argument("--output", type=Path, help="Output path (default: configs/<app-name>.yaml)")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Output format")
    
    args = parser.parse_args()
    
    print("🚀 ASC Tools - Config Bootstrapper")
    print("=" * 60)
    
    # Step 1: Select app
    if args.app_id:
        print(f"\n📱 Using app ID: {args.app_id}")
        # Fetch app details
        success, output = run_asc(["apps", "view", "--id", args.app_id, "--output", "json"])
        if not success:
            print(f"❌ Failed to fetch app: {output}")
            sys.exit(1)
        
        try:
            data = json.loads(output)
            app_data = data.get("data", {})
            attrs = app_data.get("attributes", {})
            app = {
                "id": args.app_id,
                "name": attrs.get("name", "Unknown"),
                "bundle_id": attrs.get("bundleId", "")
            }
        except json.JSONDecodeError:
            print("❌ Invalid JSON response")
            sys.exit(1)
    else:
        print("\n📱 Fetching your apps...")
        apps = fetch_apps()
        
        if not apps:
            print("❌ No apps found")
            sys.exit(1)
        
        app = select_from_list(apps, "name", "Select your app:")
    
    print(f"\n   App: {app['name']}")
    print(f"   ID:  {app['id']}")
    
    # Step 2: Select subscription group
    print(f"\n📦 Fetching subscription groups...")
    groups = fetch_subscription_groups(app["id"])
    
    if not groups:
        print("❌ No subscription groups found for this app")
        sys.exit(1)
    
    group = select_from_list(groups, "name", "Select subscription group:")
    print(f"   Group: {group['name']}")
    print(f"   ID:    {group['id']}")
    
    # Step 3: Select subscriptions
    print(f"\n💰 Fetching subscriptions...")
    subs = fetch_subscriptions(group["id"])
    
    if not subs:
        print("❌ No subscriptions found in this group")
        sys.exit(1)
    
    selected_subs = multiselect_from_list(subs, "name", "Select subscriptions to include:")
    
    if not selected_subs:
        print("❌ No subscriptions selected")
        sys.exit(1)
    
    # Step 4: Set baseline prices
    print("\n💵 Set baseline prices (USD)")
    print("   Fetching current USD prices...")
    for sub in selected_subs:
        current = fetch_current_usd_price(str(app["id"]), str(sub["id"]))
        sub["baseline"] = prompt_baseline_price(sub["name"], current)
    
    # Step 5: Select PPP index
    ppp_index = select_ppp_index()
    
    # Step 6: Skip territories
    print("\n🌍 Skip territories (optional)")
    print("Common: USA (baseline), GBR, DEU, FRA for manual control")
    skip_input = input("Enter comma-separated codes (or press Enter to skip USA only): ").strip()
    
    if skip_input:
        skip_territories = [t.strip().upper() for t in skip_input.split(",")]
    else:
        skip_territories = ["USA"]
    
    # Step 7: Generate config
    config = generate_config(app, group, selected_subs, ppp_index, skip_territories)
    
    # Step 8: Save
    if args.output:
        output_path = args.output
    else:
        # Generate filename from app name
        safe_name = app["name"].lower().replace(" ", "-").replace(":", "").replace("/", "-")
        output_path = APPS_DIR / f"{safe_name}.{args.format}"
    
    save_config(config, output_path, args.format)
    
    print("\n📋 Next steps:")
    print(f"   1. Review: vim {output_path}")
    print(f"   2. Dry run: python src/apply_ppp_pricing_from_config.py --config {output_path} --dry-run")
    print(f"   3. Apply: python src/apply_ppp_pricing_from_config.py --config {output_path}")


if __name__ == "__main__":
    main()
