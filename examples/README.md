# Example Scripts

This directory contains example shell scripts for common workflows.

## Available Examples

### `example-apply-ppp.sh`

Apply PPP pricing using a config file with dry-run confirmation.

**Usage:**
```bash
# 1. Copy and customize config
cp configs/example.yaml configs/apps/myapp.yaml
vim configs/apps/myapp.yaml

# 2. Update the script to use your config
vim examples/example-apply-ppp.sh
# Change: CONFIG_FILE="configs/apps/myapp.yaml"

# 3. Run
./examples/example-apply-ppp.sh
```

## Creating Your Own Scripts

Copy `example-apply-ppp.sh` and customize:

```bash
cp examples/example-apply-ppp.sh examples/myapp-ppp.sh
chmod +x examples/myapp-ppp.sh
vim examples/myapp-ppp.sh
```

**Tip:** Add your app-specific scripts to `.gitignore` if you're open-sourcing this toolkit:

```bash
# In .gitignore
examples/myapp-*
examples/mycompany-*
```

## Common Patterns

### Dry-run with confirmation
```bash
python3 src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml --dry-run
read -p "Apply? (y/N) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml
fi
```

### Compare indexes before applying
```bash
echo "Comparing PPP indexes..."
python3 src/compare_indexes.py --baseline 7.99 --territories USA,GBR,IND,BRA

echo "Applying pricing..."
python3 src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml
```

### Audit current prices first
```bash
echo "Auditing current prices..."
python3 src/compare_ppp_prices.py \\
    --app-id YOUR_APP_ID \\
    --subscription-id YOUR_SUB_ID \\
    --baseline-usd 7.99 \\
    --show-only misaligned

echo "Applying PPP adjustments..."
python3 src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml
```
