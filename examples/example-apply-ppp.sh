#!/bin/bash
# Example: Apply PPP pricing using config file
# Copy and customize for your app

set -e

CONFIG_FILE="configs/myapp.yaml"

echo "🎯 Applying PPP Pricing"
echo "======================="
echo ""
echo "Config: $CONFIG_FILE"
echo ""

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    echo ""
    echo "Create one from example:"
    echo "  cp configs/example.yaml $CONFIG_FILE"
    echo "  vim $CONFIG_FILE"
    exit 1
fi

echo "Running dry-run first..."
python3 src/apply_ppp_pricing_from_config.py \
    --config "$CONFIG_FILE" \
    --dry-run

echo ""
read -p "Apply for real? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying..."
    python3 src/apply_ppp_pricing_from_config.py \
        --config "$CONFIG_FILE"
    
    echo ""
    echo "✅ Done. Check App Store Connect for scheduled price changes."
else
    echo "Cancelled."
fi
