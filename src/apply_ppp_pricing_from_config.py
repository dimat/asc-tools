#!/usr/bin/env python3
"""
Apply PPP pricing from a YAML or JSON config file.

Makes it easy to version-control and reuse pricing strategies per app.

Usage:
    python apply_ppp_pricing_from_config.py --config configs/my-app.yaml --dry-run
    python apply_ppp_pricing_from_config.py --config configs/my-app.json

Author: Dmitry Matyukhin / Fancygames
License: MIT
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# --- Configuration ---

SCRIPT_DIR = Path(__file__).parent
CONFIGS_DIR = SCRIPT_DIR.parent / "configs"

# --- Utilities ---

def load_config(path: Path) -> Dict:
    """Load config from YAML or JSON file."""
    with open(path) as f:
        if path.suffix in [".yaml", ".yml"]:
            if not HAS_YAML:
                print("❌ PyYAML not installed. Install: pip install pyyaml")
                sys.exit(1)
            return yaml.safe_load(f)
        elif path.suffix == ".json":
            return json.load(f)
        else:
            print(f"❌ Unsupported config format: {path.suffix}")
            sys.exit(1)


def build_apply_command(config: Dict, dry_run: bool = False) -> List[str]:
    """Build apply_ppp_pricing.py command from config."""
    script = SCRIPT_DIR / "apply_ppp_pricing.py"

    cmd = ["python3", str(script)]

    # Required
    cmd.extend(["--app-id", str(config["app_id"])])
    cmd.extend(["--subscription-group", str(config["subscription_group"])])
    cmd.extend(["--start-date", config["start_date"]])

    # Subscriptions
    for sub in config.get("subscriptions", []):
        sub_type = sub["type"]
        cmd.extend([f"--{sub_type}-id", str(sub["id"])])
        cmd.extend([f"--{sub_type}-baseline", str(sub["baseline"])])

    # Optional
    if config.get("preserved", True):
        cmd.append("--preserved")

    if config.get("skip_territories"):
        cmd.extend(["--skip-territories", ",".join(config["skip_territories"])])

    if config.get("ppp_index"):
        index_path = SCRIPT_DIR.parent / "data" / config["ppp_index"]
        cmd.extend(["--ppp-index", str(index_path)])

    if config.get("dry_run", False) or dry_run:
        cmd.append("--dry-run")

    if config.get("auto_confirm", False):
        cmd.append("--yes")

    return cmd


# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="Apply PPP pricing from a config file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with the app config
  python apply_ppp_pricing_from_config.py --config configs/my-app.yaml --dry-run

  # Apply for real
  python apply_ppp_pricing_from_config.py --config configs/my-app.yaml

  # Use JSON config
  python apply_ppp_pricing_from_config.py --config configs/my-app.json
        """
    )

    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to config file (YAML or JSON)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without making changes"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Load config
    print(f"📋 Loading config: {args.config}")
    config = load_config(args.config)

    app_name = config.get("app_name", "Unknown")
    print(f"   App: {app_name}")
    print(f"   App ID: {config['app_id']}")
    print(f"   Subscriptions: {len(config.get('subscriptions', []))}")
    print(f"   PPP Index: {config.get('ppp_index', 'numbeo (default)')}")
    print()

    # Build command
    cmd = build_apply_command(config, dry_run=args.dry_run)

    if args.yes:
        cmd.append("--yes")


    # Execute
    print(f"🚀 Running apply_ppp_pricing.py...")
    print()

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
