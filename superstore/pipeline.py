"""Pipeline: cleaned Parquet -> data quality gate -> DuckDB marts -> statistics -> charts.

Run: python -m superstore.pipeline [--step all|validate|marts|stats|charts]

The raw -> Parquet step (python -m superstore.etl.load_and_clean) is separate, because the cleaned
Parquet is committed: everything here runs straight after `git clone`. Each step is idempotent, so the
Airflow DAG calls the same steps one by one.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from superstore import config, warehouse
from superstore.analysis import charts, stats_models
from superstore.etl.data_quality import print_report, run_checks

log = logging.getLogger(__name__)

STEPS = ("validate", "marts", "stats", "charts")


def validate(parquet: Path) -> None:
    report = run_checks(pd.read_parquet(parquet))
    print_report(report)
    if not report.passed:
        raise SystemExit(f"Data quality checks failed: {', '.join(report.failures)}")


def export(tables: dict[str, pd.DataFrame], outputs_dir: Path) -> None:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(outputs_dir / f"{name}.csv", index=False, lineterminator="\n")
    log.info("Wrote %d CSVs -> %s", len(tables), outputs_dir)


def read_marts(outputs_dir: Path) -> dict[str, pd.DataFrame]:
    return {model: pd.read_csv(outputs_dir / f"{model}.csv") for model in warehouse.MARTS}


def run(
    steps: tuple[str, ...] = STEPS,
    parquet: Path = config.PARQUET,
    outputs_dir: Path = config.OUTPUTS_DIR,
    figures_dir: Path = config.FIGURES_DIR,
    database: Path = config.DUCKDB_PATH,
) -> None:
    if "validate" in steps:
        validate(parquet)
    if "marts" in steps:
        export(warehouse.build_warehouse_file(database, parquet), outputs_dir)
    if "stats" in steps:
        con = warehouse.connect(parquet)
        try:
            export(stats_models.run(con.table("stg_orders").df(), figures_dir), outputs_dir)
        finally:
            con.close()
    if "charts" in steps:
        paths = charts.render_all(read_marts(outputs_dir), figures_dir)
        log.info("Wrote %d charts -> %s", len(paths), figures_dir)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--step", choices=("all", *STEPS), default="all")
    parser.add_argument("--parquet", type=Path, default=config.PARQUET)
    parser.add_argument("--outputs-dir", type=Path, default=config.OUTPUTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=config.FIGURES_DIR)
    parser.add_argument("--database", type=Path, default=config.DUCKDB_PATH)
    args = parser.parse_args(argv)
    steps = STEPS if args.step == "all" else (args.step,)
    run(steps, args.parquet, args.outputs_dir, args.figures_dir, args.database)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
