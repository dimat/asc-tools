# ASC Tools

A collection of App Store Connect automation utilities built on the [ASC CLI](https://github.com/AvdLee/appstoreconnect-cli).

## Tools

### `compare_ppp_prices.py`

Compare your **current App Store prices** with PPP recommendations to find misalignments.

**What it does:**
- Fetches current subscription prices from ASC via API
- Calculates what PPP pricing recommends
- Shows which territories are aligned, underpriced, or overpriced
- Identifies revenue opportunities and conversion risks

**Usage:**

```bash
# Compare your app's monthly subscription
python src/compare_ppp_prices.py \
    --app-id YOUR_APP_ID \
    --subscription-id YOUR_MONTHLY_SUB_ID \
    --baseline-usd 7.99

# Show only misaligned territories
python src/compare_ppp_prices.py \
    --app-id YOUR_APP_ID \
    --subscription-id YOUR_MONTHLY_SUB_ID \
    --baseline-usd 7.99 \
    --show-only misaligned

# Export comparison as CSV
python src/compare_ppp_prices.py \
    --app-id YOUR_APP_ID \
    --subscription-id YOUR_MONTHLY_SUB_ID \
    --baseline-usd 7.99 \
    --output csv > comparison.csv
```

**Example output:**

```
📊 PPP Price Comparison
Subscription: YOUR_SUB_ID
Baseline: $7.99 USD
Tolerance: ±$0.5

📈 Summary:
   ✅ Aligned:      78 (67%)
   ⬆️  Underpriced:  24 (21%) — leaving money on table
   ⬇️  Overpriced:   10 (9%)  — could hurt conversions
   ❓ Missing:      4 (3%)  — no current price set

Territory       | PP    | Current | PPP Rec | Diff   | Status
----------------|-------|---------|---------|--------|------------
CHE (Switzerlan)| 178.2 | $7.99   | $9.99   | -2.00  | ⬆️ Under
GBR (UK)        | 130.8 | $9.99   | $7.49   | +2.50  | ⬇️ Over
IND (India)     | 76.4  | $6.99   | $4.49   | +2.50  | ⬇️ Over
BRA (Brazil)    | 63.7  | $2.99   | $3.49   | -0.50  | ⬆️ Under
...
```

**Insights:**
- **⬆️ Underpriced** = you're charging less than PPP suggests → leaving money on the table
- **⬇️ Overpriced** = you're charging more than PPP suggests → might hurt conversions in price-sensitive markets
- **✅ Aligned** = within tolerance (default ±$0.50)

**Use cases:**
1. **Audit existing pricing** — "Are we aligned with local purchasing power?"
2. **Before applying PPP** — "What would change if we switched to PPP?"
3. **Quarterly reviews** — "Which markets need price adjustments?"
4. **Revenue optimization** — "Where are we leaving money on the table?"

---

### `calculate_ppp_prices.py`

Calculate what PPP-adjusted prices WOULD be for all territories without applying them.

**Use cases:**
- Preview prices before applying changes
- Export for stakeholder review (CSV/JSON)
- Compare different baseline strategies
- Generate pricing documentation

**Usage:**

```bash
# Show all prices for $7.99 baseline (table format)
python src/calculate_ppp_prices.py --baseline 7.99 --show-flags

# Compare multiple baselines
python src/calculate_ppp_prices.py --baseline 4.99 --baseline 7.99 --baseline 9.99

# Export as CSV
python src/calculate_ppp_prices.py --baseline 7.99 --output csv > prices.csv

# Export as JSON
python src/calculate_ppp_prices.py --baseline 7.99 --output json > prices.json

# Sort by price (cheapest first)
python src/calculate_ppp_prices.py --baseline 7.99 --sort-by price
```

**Output formats:**
- `table` (default) — human-readable table with territory names
- `csv` — CSV for Excel/Google Sheets
- `json` — structured data for programmatic use

**Example output (table):**

```
📊 PPP Price Calculator
Source: Numbeo Cost of Living Index 2026
Baseline: USA (PP=146.0)

Baselines (USD): $7.99

Territory       | PP Index        | $7.99           | Flags          
----------------+-----------------+-----------------+----------------
AFG (AFG)       | 51.8            | $2.99           |                
IND (India)     | 76.4            | $4.49           |                
RUS (Russia)    | 61.6            | $4.49           | CB             
GBR (UK)        | 130.8           | $7.49           |                
USA (USA)       | 146.0           | $7.99           |                
CHE (Switzerland)| 178.2          | $9.99           |                
...

Flags:
  CB = Carrier-billing cap applied (PP < 80 → PP = 80)
  CI = Currency conversion issue (needs manual review)
```

---

### `bootstrap_config.py`

Interactive configuration bootstrapper. Connects to App Store Connect, fetches your apps and subscriptions, and generates a ready-to-use YAML config file.

**What it does:**
- Fetches your apps (`/v1/apps`)
- Fetches subscription groups (`/v1/apps/{ID}/subscriptionGroups`)
- Fetches subscriptions (`/v1/subscriptionGroups/{ID}/subscriptions`)
- Prompts for baseline USD prices
- Prompts for PPP index selection (Netflix, Spotify, Big Mac, Numbeo)
- Prompts for markets to skip
- Generates a fully populated config in `configs/`

**Usage:**

```bash
# Full interactive mode
python src/bootstrap_config.py

# Skip app selection if you know the ID
python src/bootstrap_config.py --app-id 1584962857

# Generate JSON instead of YAML
python src/bootstrap_config.py --format json
```

**Example flow:**

```
🚀 ASC Tools - Config Bootstrapper
============================================================

📱 Fetching your apps...

Select your app:
------------------------------------------------------------
1. Carousel - Social Media Maker
2. Sleep Relax - Sounds & Meditation
3. InvoiceZap - Invoice Maker
------------------------------------------------------------
Select (1-3): 1

   App: Carousel - Social Media Maker
   ID:  1584962857

📦 Fetching subscription groups...
✅ Auto-selected: Carousel Subscriptions

💰 Fetching subscriptions...

Select subscriptions to include:
------------------------------------------------------------
1. [monthly ] Carousel PRO Monthly
2. [annual  ] Carousel PRO Yearly
3. [weekly  ] Carousel PRO Weekly
------------------------------------------------------------
Enter numbers separated by commas (e.g., 1,3,4) or 'all'
Select: 1,2

💵 Set baseline prices (USD)
Baseline price for 'Carousel PRO Monthly' (USD): $7.99
Baseline price for 'Carousel PRO Yearly' (USD): $69.99
```

---

### `compare_indexes.py`

Compare different PPP indexes side-by-side to choose the best one for your app category.

**Use cases:**
- Choose between Numbeo, Big Mac, Netflix, or Spotify indexes
- See how different indexes would price your app
- Understand spread/variance across indexes

**Usage:**

```bash
# Compare all indexes for $7.99 baseline
python src/compare_indexes.py --baseline 7.99

# Show only selected territories
python src/compare_indexes.py --baseline 7.99 --territories GBR,IND,BRA,RUS,CHN

# Export as CSV
python src/compare_indexes.py --baseline 7.99 --output csv > index-comparison.csv
```

**Example output:**

```
Territory    | Name            | Numbeo     | Bigmac     | Netflix    | Spotify    | Spread  
-------------+-----------------+------------+------------+------------+------------+---------
GBR          | United Kingdom  | $7.49      | $7.49      | $7.49      | $7.99      | $0.50   
IND          | India           | $4.49      | $4.49      | $1.49      | $1.49      | $3.00   
BRA          | Brazil          | $3.49      | $5.49      | $3.49      | $3.49      | $2.00   
```

**Key insight:** Netflix/Spotify indexes price India much lower ($1.49 vs $4.49) because they reflect what consumers actually pay for digital entertainment in those markets.

---

### `apply_ppp_pricing.py`

Apply PPP (Purchasing Power Parity) pricing to App Store subscriptions automatically.

**Features:**
- Adjusts prices across all territories based on local purchasing power
- Uses Numbeo 2026 Cost of Living Index (extensible to other sources)
- Automatic price point matching (finds closest valid ASC price)
- Psychological pricing (.99, .49 endings)
- Carrier-billing territory handling (caps PP to avoid microtransactions)
- Preserved pricing flag (existing customers keep current price)
- Dry-run mode

**Usage:**

```bash
python src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --annual-id YOUR_ANNUAL_ID --annual-baseline 69.99 \
    --start-date 2026-05-01 \
    --preserved \
    --dry-run
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `--app-id` | ✅ | App Store app ID |
| `--subscription-group` | ✅ | Subscription group ID |
| `--monthly-id` | ⚠️ | Monthly subscription ID (required if using monthly) |
| `--monthly-baseline` | ⚠️ | Monthly baseline price in USD |
| `--annual-id` | ⚠️ | Annual subscription ID (required if using annual) |
| `--annual-baseline` | ⚠️ | Annual baseline price in USD |
| `--start-date` | ✅ | Price change start date (YYYY-MM-DD) |
| `--preserved` | ❌ | Preserve current price for existing customers |
| `--dry-run` | ❌ | Simulate without making changes |
| `--ppp-index` | ❌ | Path to custom PPP index JSON (default: `data/ppp-index-numbeo-2026.json`) |
| `--skip-territories` | ❌ | Comma-separated list of territories to skip |

**How it works:**

1. Loads PPP index (default: Numbeo 2026)
2. For each territory:
   - Calculates target price: `baseline_price × (territory_PP / baseline_PP)`
   - Rounds to psychological price (.99 or .49)
   - Queries ASC for available price points
   - Finds closest valid price point
   - Schedules price change via ASC API
3. Reports summary (applied, skipped, errors)

**Automatic handling:**

- **Carrier-billing territories** (RUS, BLR, UZB, TJK, KGZ, AZE, ARM, GEO, MDA): PP capped at 80 to avoid microtransaction issues
- **Currency conversion issues** (HUN, IDN, NGA, KOR, JPN, PAK, TZA, VNM, KAZ): Skipped (needs manual review)
- **Baseline territory** (USA): Skipped by default
- **Strategic markets:** If you want manual control over major markets (GBR, DEU, FRA, IND, BRA, etc.), add them to `--skip-territories`

**Example output:**

```
📊 Loading PPP index: data/ppp-index-numbeo-2026.json
   Baseline: USA (PP=146.0)
   Source: Numbeo Cost of Living Index 2026

⏭️  Skipping 1 territory: USA

🌍 Fetching territories...
   Found 175 territories

🎯 Processing 174 territories

💰 Monthly Subscription (baseline: $7.99)
================================================================================
  AFG: PP=51.8, target=$2.99, matched=$2.99 (tier 5) ✅
  ALB: PP=65.3, target=$3.49, matched=$3.49 (tier 7) ✅
  ...

📊 Summary:
   ✅ Applied: 342
   ⏭️  Skipped: 50
   ❌ Errors: 6
```

---

## Data Sources

### PPP Indexes

PPP indexes live in `data/` and can be swapped via `--ppp-index` argument:

#### Available Indexes

- **`ppp-index-numbeo-2026.json`** — Numbeo Cost of Living Index 2026 (default)
  - **Best for:** Broad demographic apps, general consumer products
  - **Coverage:** 116 territories
  - **Baseline:** USA (PP=146.0)

- **`ppp-index-bigmac-2026.json`** — The Economist Big Mac Index January 2026
  - **Best for:** Consumer goods, utilities, real purchasing power
  - **Coverage:** 57 territories
  - **Baseline:** USA ($5.69)

- **`ppp-index-netflix-2026.json`** — Netflix Standard Plan Pricing Index 2026
  - **Best for:** Streaming apps, video content, entertainment subscriptions
  - **Coverage:** 58 territories
  - **Baseline:** USA ($15.49)

- **`ppp-index-spotify-2026.json`** — Spotify Premium Individual Plan Pricing Index 2026
  - **Best for:** Audio/music apps, lifestyle subscriptions, entertainment
  - **Coverage:** 58 territories
  - **Baseline:** USA ($10.99)

#### Which Index to Use?

**For entertainment/lifestyle apps:**
- Use **Netflix** or **Spotify** — reflects what consumers actually pay for digital content subscriptions

**For productivity/utility apps:**
- Use **Big Mac** — reflects real consumer purchasing power for goods

**For broad-market apps:**
- Use **Numbeo** — comprehensive cost-of-living data

**Compare indexes before choosing:**
```bash
python src/compare_indexes.py --baseline 7.99
```

**Format:**

```json
{
  "source": "Numbeo Cost of Living Index 2026",
  "url": "https://www.numbeo.com/cost-of-living/rankings_by_country.jsp?displayColumn=5",
  "baseline_country": "USA",
  "baseline_value": 146.0,
  "updated": "2026-04-08",
  "index": {
    "USA": 146.0,
    "GBR": 130.8,
    "IND": 76.4,
    ...
  }
}
```

**Territory codes:** ISO 3166-1 alpha-3 (e.g., `USA`, `GBR`, `IND`)

**Adding a new index:**

1. Create `data/ppp-index-<source>-<year>.json`
2. Use `--ppp-index path/to/index.json` when running the tool

---

## Setup

### Prerequisites

1. **ASC CLI** installed and authenticated:
   ```bash
   brew install asc
   asc login
   ```

2. **Python 3.8+**

### Installation

```bash
git clone <repo>
cd asc-tools
```

No dependencies — uses only Python stdlib + `asc` CLI.

---

## Config-Driven Workflow (Recommended)

For production use, **config files** are the recommended approach. You can generate one interactively:

```bash
# 1. Bootstrap config interactively (fetches IDs from ASC)
python src/bootstrap_config.py

# 2. Dry run to preview
python src/apply_ppp_pricing_from_config.py --config configs/apps/your-app.yaml --dry-run

# 3. Apply for real
python src/apply_ppp_pricing_from_config.py --config configs/apps/your-app.yaml

# 4. Commit your config to git (optional)
git add configs/apps/your-app.yaml
git commit -m "Add PPP pricing for My App"
```

**Example config included:**
- `configs/example.yaml` — Template with inline documentation

See `configs/README.md` for format and field descriptions.

---

## Examples

### Basic usage

```bash
# Dry run first
python src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --annual-id YOUR_ANNUAL_ID --annual-baseline 69.99 \
    --start-date 2026-05-01 \
    --preserved \
    --dry-run

# Apply for real
python src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --annual-id YOUR_ANNUAL_ID --annual-baseline 69.99 \
    --start-date 2026-05-01 \
    --preserved
```

### Custom baseline territories

```bash
# Skip additional territories
python src/apply_ppp_pricing.py \
    --app-id 1234567890 \
    --subscription-group 12345678 \
    --monthly-id 9876543210 --monthly-baseline 9.99 \
    --start-date 2026-05-01 \
    --skip-territories "JPN,AUS,CAN" \
    --preserved
```

### Use Netflix index for entertainment apps

```bash
# Better for streaming/creative/entertainment apps
python src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --start-date 2026-05-01 \
    --ppp-index data/ppp-index-netflix-2026.json \
    --preserved
```

### Compare indexes first

```bash
# See which index fits your app best
python src/compare_indexes.py --baseline 7.99
```

---

## Roadmap

- [ ] Support for one-time IAPs (not just subscriptions)
- [ ] Exchange rate integration (live FX data)
- [ ] Bulk operations (multiple apps at once)
- [ ] Rollback command (revert scheduled price changes)
- [ ] Price change history export
- [ ] Support for promotional offers
- [ ] Web UI (Flask/FastAPI wrapper)

---

## Contributing

PRs welcome! This toolkit is designed to be:
- **Universal** — works for any App Store app
- **Extensible** — easy to add new PPP indexes or pricing strategies
- **Production-ready** — battle-tested on real apps

---

## Credits

Built with:
- [ASC CLI](https://github.com/AvdLee/appstoreconnect-cli) by Antoine van der Lee
- [Numbeo Cost of Living Index](https://www.numbeo.com/cost-of-living/)

Developed for [Fancygames](https://fancygames.net) app portfolio.
