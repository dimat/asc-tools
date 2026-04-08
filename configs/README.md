# App Configuration Files

Config-driven PPP pricing for all Fancygames apps.

## Usage

```bash
# Copy example and customize
cp configs/example.yaml configs/apps/myapp.yaml
vim configs/apps/myapp.yaml

# Dry run first
python src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml --dry-run

# Apply for real
python src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml

# Show generated command
python src/apply_ppp_pricing_from_config.py --config configs/apps/myapp.yaml --show-command
```

## Example Config

### `example.yaml`
- **Category:** Entertainment app (example)
- **Index:** Netflix (digital content)
- **Subscriptions:** Monthly ($7.99), Annual ($69.99)
- **Skip:** USA (baseline) + strategic markets
- Fully documented with inline comments

## Config Format

Both YAML and JSON are supported. YAML is recommended for readability.

### YAML Example

```yaml
app_name: "My App"
app_id: 1234567890
subscription_group: 12345678

subscriptions:
  - type: monthly
    id: 9876543210
    baseline: 7.99
  
  - type: annual
    id: 9876543211
    baseline: 69.99

ppp_index: ppp-index-netflix-2026.json

skip_territories:
  - GBR
  - DEU
  - FRA

start_date: "2026-05-01"

preserved: true
```

### JSON Example

```json
{
  "app_name": "My App",
  "app_id": 1234567890,
  "subscription_group": 12345678,
  "subscriptions": [
    {"type": "monthly", "id": 9876543210, "baseline": 7.99},
    {"type": "annual", "id": 9876543211, "baseline": 69.99}
  ],
  "ppp_index": "ppp-index-netflix-2026.json",
  "skip_territories": ["GBR", "DEU", "FRA"],
  "start_date": "2026-05-01",
  "preserved": true
}
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `app_name` | ❌ | Human-readable app name (for logs) |
| `app_id` | ✅ | App Store app ID |
| `subscription_group` | ✅ | Subscription group ID |
| `subscriptions` | ✅ | List of subscriptions to update |
| `subscriptions[].type` | ✅ | `monthly`, `annual`, etc. |
| `subscriptions[].id` | ✅ | Subscription ID |
| `subscriptions[].baseline` | ✅ | Baseline price in USD |
| `ppp_index` | ❌ | PPP index filename (default: `ppp-index-numbeo-2026.json`) |
| `skip_territories` | ❌ | List of territory codes to skip |
| `start_date` | ✅ | Price change start date (YYYY-MM-DD) |
| `preserved` | ❌ | Preserve current price for existing customers (default: true) |

## Workflow

1. **Edit config** — update subscription IDs, baselines, start date
2. **Dry run** — `--dry-run` to preview changes
3. **Apply** — remove `--dry-run` to apply
4. **Commit config** — version control your pricing strategy

## Index Selection Guide

Choose your PPP index based on app category:

| App Category | Recommended Index | Why |
|--------------|-------------------|-----|
| Entertainment, Streaming, Video | Netflix | Reflects digital content subscription pricing |
| Music, Audio, Lifestyle | Spotify | Reflects audio/lifestyle subscription pricing |
| Productivity, Business, Utilities | Big Mac | Reflects business/utility purchasing power |
| Broad consumer apps | Numbeo | General cost-of-living data |

**Compare indexes first:**
```bash
python src/compare_indexes.py --baseline 7.99
```

## Notes

- Configs are version-controlled → easy to track pricing strategy changes
- One config per app → clear separation of concerns
- YAML recommended for comments and readability
- All three apps use `preserved: true` to protect existing subscribers
- Weekly subscriptions excluded from configs (apply manually if needed)
