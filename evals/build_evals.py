"""Build one example reconciliation dataset per scenario.

Each scenario gets a different combination of record count, match
distribution, 1:N complexity, and variance, so the resulting eval folder
covers a range of difficulty levels. Outputs are written to ``evals/<scenario>/``.

Run with the venv active:

    python evals/build_evals.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from recon_datagen.generator import DataGenerator
from recon_datagen.models import GenerationConfig, GenerationStats
from recon_datagen.scenarios import SCENARIO_REGISTRY, get_scenario
from recon_datagen.writer import ExcelWriter


@dataclass
class EvalSpec:
    scenario: str
    rows: int
    match_pct: float
    potential_pct: float
    one_to_n_ratio: float
    amount_variance: float
    date_variance_days: int
    complexity: str  # human-readable label
    notes: str
    num_mapping_keys: int = 2  # declared non-monetary mapping keys (1-3)


# Each scenario gets a distinct shape so the eval folder exercises a
# spread of sizes and difficulty levels. The num_mapping_keys field also
# varies (1/2/3) to mirror the get_table_keys_suggestion distribution.
EVAL_SPECS: List[EvalSpec] = [
    EvalSpec("bank-recon",        rows=50,   match_pct=0.80, potential_pct=0.10, one_to_n_ratio=0.20, amount_variance=0.02, date_variance_days=2, complexity="Low",       notes="Small, mostly clean 1:1 matches", num_mapping_keys=2),
    EvalSpec("vendor-recon",      rows=100,  match_pct=0.70, potential_pct=0.20, one_to_n_ratio=0.30, amount_variance=0.03, date_variance_days=3, complexity="Low-Med",   notes="Partial invoice payments mixed in", num_mapping_keys=1),
    EvalSpec("customer-recon",    rows=150,  match_pct=0.65, potential_pct=0.25, one_to_n_ratio=0.30, amount_variance=0.04, date_variance_days=3, complexity="Medium",    notes="Customer payment timing variances", num_mapping_keys=2),
    EvalSpec("intercompany",      rows=200,  match_pct=0.60, potential_pct=0.30, one_to_n_ratio=0.40, amount_variance=0.05, date_variance_days=4, complexity="Medium",    notes="FX/timing differences between entities", num_mapping_keys=3),
    EvalSpec("gl-subledger",      rows=300,  match_pct=0.55, potential_pct=0.35, one_to_n_ratio=0.50, amount_variance=0.03, date_variance_days=2, complexity="Med-High",  notes="GL summary aggregates many subledger rows", num_mapping_keys=2),
    EvalSpec("inventory-recon",   rows=250,  match_pct=0.60, potential_pct=0.30, one_to_n_ratio=0.35, amount_variance=0.06, date_variance_days=0, complexity="Medium",    notes="Quantity & unit cost variances per location", num_mapping_keys=1),
    EvalSpec("fixed-asset-recon", rows=120,  match_pct=0.75, potential_pct=0.15, one_to_n_ratio=0.25, amount_variance=0.04, date_variance_days=5, complexity="Low-Med",   notes="Depreciation timing differences", num_mapping_keys=2),
    EvalSpec("payroll-recon",     rows=180,  match_pct=0.70, potential_pct=0.20, one_to_n_ratio=0.40, amount_variance=0.02, date_variance_days=2, complexity="Medium",    notes="Payroll runs split across GL journals", num_mapping_keys=3),
    EvalSpec("tax-recon",         rows=80,   match_pct=0.80, potential_pct=0.15, one_to_n_ratio=0.20, amount_variance=0.05, date_variance_days=0, complexity="Low",       notes="Quarterly filings, low volume", num_mapping_keys=1),
    EvalSpec("expense-recon",     rows=400,  match_pct=0.50, potential_pct=0.40, one_to_n_ratio=0.45, amount_variance=0.08, date_variance_days=4, complexity="High",      notes="High noise: tips, FX, merchant name drift", num_mapping_keys=2),
]


def build_one(spec: EvalSpec, evals_root: Path) -> tuple[Path, GenerationStats]:
    scenario = get_scenario(spec.scenario)
    output_dir = evals_root / spec.scenario
    config = GenerationConfig(
        scenario=spec.scenario,
        total_source_rows=spec.rows,
        match_percent=spec.match_pct,
        potential_percent=spec.potential_pct,
        one_to_n_ratio=spec.one_to_n_ratio,
        amount_variance_percent=spec.amount_variance,
        date_variance_days=spec.date_variance_days,
        num_mapping_keys=spec.num_mapping_keys,
        output_path=str(output_dir / f"{spec.scenario}.xlsx"),
        seed=42,
    )
    errors = config.validate()
    if errors:
        raise ValueError(f"Invalid config for {spec.scenario}: {errors}")

    generator = DataGenerator(scenario, config)
    writer = ExcelWriter(str(output_dir), scenario)
    for source_chunk, target_chunk in generator.generate():
        writer.write_chunk(source_chunk, target_chunk)
    writer.finalize(generator.stats)
    writer.close()
    return output_dir, generator.stats


def write_readme(evals_root: Path, rows: list[dict]) -> Path:
    headers = [
        "Scenario", "Dataset 1", "Dataset 2",
        "Rows (src/tgt)", "Match%", "Potential%", "Unmatched%",
        "1:N Ratio", "Amt Var", "Date Var (d)",
        "Complexity", "# Keys", "Keys (D1)", "Keys (D2)", "Notes", "Output",
    ]
    lines = ["# Reconciliation Eval Datasets", ""]
    lines.append(
        "One example per scenario, generated by `python evals/build_evals.py`. "
        "Each row uses a different combination of record count, match "
        "distribution, 1:N aggregation, and variance to exercise a spread of "
        "difficulty levels. Every scenario declares a single monetary key plus "
        "a configurable number of non-monetary mapping keys (1-3, see the "
        "**# Keys** column), mirroring the get_table_keys_suggestion "
        "distribution."
    )
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    lines.append("")

    readme = evals_root / "README.md"
    readme.write_text("\n".join(lines), encoding="utf-8")
    return readme


def main() -> None:
    evals_root = Path(__file__).resolve().parent
    evals_root.mkdir(exist_ok=True)

    rows: list[dict] = []
    for spec in EVAL_SPECS:
        if spec.scenario not in SCENARIO_REGISTRY:
            raise ValueError(f"Unknown scenario in EVAL_SPECS: {spec.scenario}")

        output_dir, stats = build_one(spec, evals_root)
        scenario = get_scenario(spec.scenario)
        scenario.num_mapping_keys = spec.num_mapping_keys
        rel = output_dir.relative_to(evals_root).as_posix()
        unmatched_pct = max(0.0, 1.0 - spec.match_pct - spec.potential_pct)
        rows.append({
            "Scenario": spec.scenario,
            "Dataset 1": scenario.dataset1_name,
            "Dataset 2": scenario.dataset2_name,
            "Rows (src/tgt)": f"{stats.source_rows}/{stats.target_rows}",
            "Match%": f"{spec.match_pct:.0%}",
            "Potential%": f"{spec.potential_pct:.0%}",
            "Unmatched%": f"{unmatched_pct:.0%}",
            "1:N Ratio": f"{spec.one_to_n_ratio:.0%}",
            "Amt Var": f"±{spec.amount_variance:.0%}",
            "Date Var (d)": spec.date_variance_days,
            "Complexity": spec.complexity,
            "# Keys": spec.num_mapping_keys,
            "Keys (D1)": ", ".join(scenario.active_mapping_keys1),
            "Keys (D2)": ", ".join(scenario.active_mapping_keys2),
            "Notes": spec.notes,
            "Output": f"[`{rel}/`]({rel}/)",
        })
        print(f"  generated {spec.scenario}: {stats.source_rows} src / {stats.target_rows} tgt -> {rel}")

    readme = write_readme(evals_root, rows)
    print(f"\nwrote {readme.relative_to(evals_root.parent).as_posix()}")


if __name__ == "__main__":
    main()
