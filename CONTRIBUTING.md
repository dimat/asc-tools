# Contributing to ASC Tools

Thanks for your interest in contributing! This toolkit is designed to be open-source friendly.

## Development Setup

```bash
# Clone
git clone https://github.com/yourorg/asc-tools
cd asc-tools

# Install ASC CLI
brew install asc
asc login

# Optional: Install PyYAML for YAML config support
pip install pyyaml
```

## Project Structure

```
asc-tools/
├── src/              # Core tools (Python scripts)
├── data/             # PPP index data (JSON)
├── configs/          # Config templates (keep app-specific ones private)
├── examples/         # Example shell scripts
├── README.md         # Main documentation
└── QUICKSTART.md     # Quick start guide
```

## What's Public vs Private

### ✅ Public (commit to git)

- All Python tools in `src/`
- All PPP indexes in `data/`
- `configs/example.yaml` (template)
- `examples/example-*.sh` (generic examples)
- All documentation (`*.md` files)

### 🔒 Private (gitignored, keep local)

- `configs/apps/*` (app-specific configs)
- Any files with real App Store IDs, subscription IDs, or app names

**Why?** This keeps the toolkit reusable for everyone while protecting your app-specific data.

## Adding New Features

### Adding a new PPP index

1. Create `data/ppp-index-{source}-{year}.json`
2. Follow the format in existing indexes
3. Update `README.md` data sources section
4. Test with `compare_indexes.py`

### Adding a new tool

1. Create `src/your_tool.py`
2. Add CLI argument parser
3. Follow existing tool patterns (JSON/CSV/table output)
4. Document in `README.md`
5. Add example usage

### Adding a new config field

1. Update `configs/example.yaml` with documentation
2. Update `apply_ppp_pricing_from_config.py` to handle it
3. Update `configs/README.md` field table

## Code Style

- Python: PEP 8
- Keep it simple — stdlib only (except PyYAML for configs)
- CLI-first — all tools should work standalone
- Output formats: table (default), CSV, JSON

## Testing

Before submitting:

1. Test with `--dry-run` first
2. Verify help output: `python src/your_tool.py --help`
3. Test all output formats (table, CSV, JSON)
4. Ensure no app-specific data in examples

## Pull Requests

1. Fork the repo
2. Create a feature branch
3. Keep commits focused and atomic
4. Update documentation
5. Submit PR with clear description

## License

MIT — see LICENSE file
