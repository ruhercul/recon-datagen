# 🔄 Reconciliation Test Data Generator

Generate realistic matched, potentially matched, and unmatched transaction datasets for reconciliation testing at scale.

## Overview

`recon-datagen` is a CLI tool that produces synthetic reconciliation test data across **10 industry-standard scenarios**. Each run creates a timestamped output folder containing:

| File | Description |
|------|-------------|
| `<name>.xlsx` | Excel workbook with two data sheets + a Generation Stats sheet |
| `<Source>.csv` | CSV export of the source dataset |
| `<Target>.csv` | CSV export of the target dataset |

The generated data includes controlled distributions of **exact 1:1 matched records**, **potentially matched 1:N aggregate records**, **potential tolerance/partial records**, and **unmatched records** — making it ideal for validating reconciliation engines such as Microsoft Copilot for Finance.

---

## Quick Start

### Install

```bash
pip install -e .
```

### Run (Quick Mode)

```bash
recon-datagen --quick -s bank-recon -n 500 --seed 42
```

### Run (Interactive Mode)

```bash
recon-datagen
```

The interactive CLI walks you through scenario selection, row counts, match distributions, 1:N potential-match configuration, variance tolerances, and output options.

---

## Available Scenarios

| Scenario | Source Dataset | Target Dataset |
|----------|--------------|----------------|
| `bank-recon` | Cash Ledger | Bank Statement |
| `vendor-recon` | AP Ledger | Vendor Statement |
| `customer-recon` | AR Ledger | Customer Statement |
| `intercompany` | Entity A IC Ledger | Entity B IC Ledger |
| `gl-subledger` | GL Summary | Subledger Detail |
| `inventory-recon` | ERP Inventory | Physical Count |
| `fixed-asset-recon` | FA Register | GL FA Accounts |
| `payroll-recon` | Payroll System | GL Payroll |
| `tax-recon` | ERP Tax Calculation | Filed Tax Return |
| `expense-recon` | T&E Expense Reports | Corporate Card Statement |

List all scenarios:

```bash
recon-datagen --list
```

---

## CLI Reference

```
recon-datagen [OPTIONS]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--quick` | `-q` | Skip interactive prompts | — |
| `--scenario` | `-s` | Scenario name (required in quick mode) | — |
| `--rows` | `-n` | Number of source rows (required in quick mode) | — |
| `--match-pct` | `-m` | Exact match percentage (0–100) | `60` |
| `--potential-pct` | `-p` | Potential match percentage (0–100) | `25` |
| `--num-keys` | `-k` | Non-monetary mapping keys per dataset (1–3) | `2` |
| `--output` | `-o` | Custom output folder name | auto-timestamped |
| `--seed` | | Random seed for reproducibility | random |
| `--list` | `-l` | List available scenarios and exit | — |

### Examples

```bash
# 10k rows, high-match distribution, reproducible
recon-datagen -q -s vendor-recon -n 10000 -m 80 -p 15 --seed 123

# 3 mapping keys (composite + allocation key) for complex key-detection tests
recon-datagen -q -s intercompany -n 5000 -k 3 --seed 42

# Single mapping key (unique reference only)
recon-datagen -q -s tax-recon -n 2000 -k 1

# 1M rows, default distribution
recon-datagen -q -s bank-recon -n 1000000

# Interactive mode (guided prompts)
recon-datagen
```

---

## Output Structure

Each run creates a timestamped folder:

```
recon_test_data_bank_recon_20260211_134217/
├── recon_test_data_bank_recon_20260211_134217.xlsx
├── Cash_Ledger.csv
└── Bank_Statement.csv
```

### Excel Workbook Sheets

| Sheet | Content |
|-------|---------|
| Sheet 1 (e.g. `Cash_Ledger`) | Source dataset with all columns |
| Sheet 2 (e.g. `Bank_Statement`) | Target dataset with all columns |
| `Generation_Stats` | Summary statistics, distribution percentages, mapping key guidance, and example records for 1:1, 1:N, and partial matches |

---

## Match Types

### Exact 1:1 Match
One source record maps to exactly one target record. Mapping keys and amounts match perfectly.

### Potential 1:N Aggregate Match
One source record maps to **N** target records with the same mapping key. The source amount equals the **sum** of all N target amounts. Finance.Copilot reports these same-key multi-row aggregate groups as `PotentiallyMatched`, not `Matched`.

### Potential (Partial) Match
Source and target are related but not identical. Finance.Copilot partial matching calls `IsPartialMatch(primary, secondary)`, so the target key must be a shorter key that matches a word-boundary-aligned portion of the source key. Examples include `2024-123456`, `REF-2024`, or `REF2024123456` for a source key like `REF-2024-123456`.

Amount tolerance potential matches keep the same mapping key and apply a non-zero amount difference. These rows are `PotentiallyMatched` only when the reconciliation request configures an amount tolerance large enough for the generated difference.

### Unmatched Source
A source record with no corresponding target record.

### Unmatched Target
A target record with no corresponding source record (orphan).

---

## Configuration Options (Interactive Mode)

| Setting | Presets |
|---------|--------|
| **Match Distribution** | Balanced (60/25/15), High Match (80/15/5), Low Match (40/30/30), Challenging (30/40/30), Custom |
| **1:N Potential Ratio** | Low (20%, 2-3 splits), Medium (35%, 2-5), High (50%, 2-7), Custom |
| **Variance Tolerance** | Zero (0%/0d), Tight (±2%/±1d), Normal (±5%/±3d), Loose (±10%/±7d), Custom |
| **Row Count** | 500 / 5K / 10K / 50K / 100K / 500K / 1M / Custom |

---

## Example Session

```
╔═══════════════════════════════════════════════════════════════╗
║          🔄 Reconciliation Test Data Generator 🔄              ║
╚═══════════════════════════════════════════════════════════════╝

? Which reconciliation scenario would you like to generate?
  ❯ Bank Reconciliation - Reconcile Cash Ledger entries against...

? How many source records do you want to generate? 500 rows (quick test)

? Proceed with data generation? Yes

  Finalizing files... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Data generation complete!

┌─────────────────────────────┬─────┐
│ Source Dataset Rows         │ 500 │
│ Target Dataset Rows         │ 557 │
│ Matched (Exact 1:1)         │ 300 │
│ Potentially Matched         │ 125 │
│ Potential 1:N Aggregate     │  37 │
│ Potential Tolerance/Partial │  88 │
│ Unmatched (Source Only)     │  75 │
│ Unmatched (Target Only)     │  37 │
└─────────────────────────────┴─────┘

Output folder:  recon_test_data_bank_recon_20260211_134217/
  XLSX:        recon_test_data_bank_recon_20260211_134217.xlsx
  CSV (source): Cash_Ledger.csv
  CSV (target): Bank_Statement.csv
```

---

## Project Structure

```
src/recon_datagen/
├── cli.py                   # Interactive + quick-mode CLI
├── generator.py             # Core generation engine
├── writer.py                # XLSX + CSV output writer
├── models.py                # Data models (config, stats, enums)
└── scenarios/
    ├── base.py              # Abstract scenario base class
    ├── bank_recon.py        # Bank Reconciliation
    ├── vendor_recon.py      # Vendor/Supplier Reconciliation
    ├── customer_recon.py    # Customer/AR Reconciliation
    ├── intercompany.py      # Intercompany Reconciliation
    ├── gl_subledger.py      # GL vs Subledger
    ├── inventory_recon.py   # Inventory Reconciliation
    ├── fixed_asset_recon.py # Fixed Asset Reconciliation
    ├── payroll_recon.py     # Payroll Reconciliation
    ├── tax_recon.py         # Tax Reconciliation
    └── expense_recon.py     # Expense Reconciliation
```

---

## Requirements

- Python ≥ 3.10
- Dependencies: `questionary`, `rich`, `openpyxl`, `faker`

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
