# Quick Start Guide

Get PPP pricing running in 5 minutes.

## 1. Prerequisites

```bash
# Install ASC CLI
brew install asc

# Login to App Store Connect
asc login
```

## 2. Find your IDs

You need:
- **App ID** — from App Store Connect URL: `https://appstoreconnect.apple.com/apps/{APP_ID}/...`
- **Subscription group ID** — from the subscription group page
- **Subscription IDs** — individual subscription IDs (monthly, annual, etc.)

**Quick way to find subscription IDs:**

```bash
# List all subscriptions for your app
asc get /v1/apps/{APP_ID}/subscriptionGroups

# Then list subscriptions in a group
asc get /v1/subscriptionGroups/{GROUP_ID}/subscriptions
```

## 3. Run dry-run

```bash

python3 src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --annual-id YOUR_ANNUAL_ID --annual-baseline 69.99 \
    --start-date 2026-05-01 \
    --preserved \
    --dry-run
```

Review the output. Check that:
- ✅ Territories are correct
- ✅ Prices look reasonable
- ✅ Skip list makes sense

## 4. Apply for real

Remove `--dry-run`:

```bash
python3 src/apply_ppp_pricing.py \
    --app-id YOUR_APP_ID \
    --subscription-group YOUR_GROUP_ID \
    --monthly-id YOUR_MONTHLY_ID --monthly-baseline 7.99 \
    --annual-id YOUR_ANNUAL_ID --annual-baseline 69.99 \
    --start-date 2026-05-01 \
    --preserved
```

## 5. Verify in App Store Connect

Go to your app → Subscriptions → Pricing → check scheduled price changes.

**⚠️ Apple limitation:** Only ONE future price change per territory is allowed. If you need to change the date or price, delete the existing scheduled change first.

---

## Common issues

### "No price points found"

The subscription might not be available in that territory yet. Check App Store Connect → Subscriptions → Availability.

### "Future price already exists"

Delete the existing scheduled price change first:

```bash
# List scheduled prices
asc get /v1/subscriptions/{SUB_ID}/prices

# Delete one
asc delete subscriptionPrices/{PRICE_ID}
```

### "Rate limit exceeded"

The script sleeps 0.5s between requests. If you hit rate limits, increase the sleep in the script.

---

## Tips

1. **Always dry-run first** — catches issues before making 300+ API calls
2. **Use `--preserved`** — keeps existing customers happy
3. **Start date 7+ days out** — gives you time to review in ASC
4. **Skip baseline territories** — they're already in the default skip list
5. **Check currency conversion issues** — HUN, IDN, NGA, KOR, JPN, PAK, TZA, VNM, KAZ are auto-skipped (need manual review)

---

## Next steps

- Add more subscriptions (weekly, lifetime, etc.) — just add more `--{period}-id` + `--{period}-baseline` flags
- Create your own PPP index (see `data/ppp-index-numbeo-2026.json` for format)
- Automate monthly updates (cron job that re-runs with updated Numbeo data)

---

**Questions?** Check `README.md` or open an issue.
