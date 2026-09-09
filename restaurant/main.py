#!/usr/bin/env python3
"""
Entry-point script for the restaurant weekly pipeline.

Usage examples::

    # Full pipeline: load data, export CSVs, summary, and bi-weekly report
    python -m restaurant.main --data-dir . --biweekly-start 2026-07-06

    # Full pipeline + upload processed data to BigQuery
    python -m restaurant.main --data-dir . --biweekly-start 2026-07-06 --upload

    # Reports only: skip data rebuild, generate bi-weekly + kitchen pars
    python -m restaurant.main --data-dir . --biweekly-start 2026-07-06 --report-only

    # Just rebuild data and summary, no bi-weekly report
    python -m restaurant.main --data-dir . --summary-end 2026-07-20
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from . import config as cfg
from .reports import generate_biweekly_report
from .summaries import report_table


def _derive_dates(biweekly_start: str) -> dict:
    """Derive all report dates from the biweekly start Monday."""
    start = datetime.strptime(biweekly_start, "%Y-%m-%d")
    end_of_period = start + timedelta(days=13)
    release_date = end_of_period + timedelta(days=5)

    w1_label_start = start.strftime("%d%b%Y").upper()
    w1_label_end = (start + timedelta(days=7)).strftime("%d%b%Y").upper()
    w2_start = start + timedelta(days=8)
    w2_label_start = w2_start.strftime("%d%b%Y").upper()
    w2_label_end = (w2_start + timedelta(days=7)).strftime("%d%b%Y").upper()

    return {
        "start": start,
        "end": end_of_period,
        "release_dir": release_date.strftime("%Y-%m-%d"),
        "biweekly_label": end_of_period.strftime("%d%b%Y").upper(),
        "w1_checkdt_ref": (start - timedelta(days=1)).strftime("%Y-%m-%d"),
        "w1_label": f"{w1_label_start}-{w1_label_end}",
        "w2_checkdt_ref": (start + timedelta(days=6)).strftime("%Y-%m-%d"),
        "w2_label": f"{w2_label_start}-{w2_label_end}",
        "summary_end": end_of_period.strftime("%Y-%m-%d"),
    }


def upload_to_bigquery(
    sales: pd.DataFrame,
    orders: pd.DataFrame,
    summary: pd.DataFrame | None = None,
    project: str = cfg.BQ_PROJECT,
    dataset: str = cfg.BQ_DATASET,
) -> None:
    """Push processed DataFrames to BigQuery (full replace).

    Parameters
    ----------
    sales : DataFrame
        The merged, categorised line-item sales data.
    orders : DataFrame
        The merged, categorised order-level data.
    summary : DataFrame or None
        The all-time daily summary. Skipped if None.
    project : str
        Google Cloud project ID.
    dataset : str
        BigQuery dataset name.
    """
    tables = [("sales", sales), ("orders", orders)]
    if summary is not None:
        tables.append(("summary", summary))

    for name, df in tables:
        destination = f"{project}.{dataset}.{name}"
        df.to_gbq(destination, project_id=project, if_exists="replace")
        print(f"  Uploaded {name} ({len(df):,} rows) to {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaurant weekly sales pipeline")
    parser.add_argument("--data-dir", default=".", help="Directory containing CSV data files")
    parser.add_argument("--tock-file", default=cfg.TOCK_FILE, help="Tock daily-details CSV filename")
    parser.add_argument("--biweekly-start", default=None, help="Monday start date (YYYY-MM-DD)")
    parser.add_argument("--output-dir", default="../Weekly_Reports", help="Root for report output")
    parser.add_argument("--summary-start", default="2023-01-01", help="All-time summary start")
    parser.add_argument("--summary-end", default=None,
                        help="All-time summary end (default: derived from biweekly period)")
    parser.add_argument(
        "--report-only", action="store_true",
        help="Skip data rebuild; read existing sales.csv and orders.csv, then generate reports",
    )
    parser.add_argument(
        "--upload", action="store_true",
        help="Upload processed sales/orders/summary to BigQuery after pipeline runs",
    )
    args = parser.parse_args()

    os.chdir(args.data_dir)

    if args.report_only and not args.biweekly_start:
        print("Error: --report-only requires --biweekly-start")
        sys.exit(1)

    # -------------------------------------------------------------------
    # Step 1: Load data
    # -------------------------------------------------------------------
    full_summary = None

    if args.report_only:
        print("Reading existing sales.csv and orders.csv...")
        sales = pd.read_csv("sales.csv", low_memory=False)
        orders = pd.read_csv("orders.csv", low_memory=False)

        # Parse Date columns back to datetime.date (CSV round-trip loses the type)
        from datetime import datetime as _dt
        for df in (sales, orders):
            if "Date" in df.columns and df["Date"].dtype == object:
                df["Date"] = df["Date"].apply(
                    lambda x: _dt.strptime(str(x), "%Y-%m-%d").date()
                    if pd.notna(x) else x
                )
    else:
        from .data_pipeline import build_datasets

        print("Loading and merging data...")
        orders, sales = build_datasets(tock_file=args.tock_file, data_dir=".")

        sales.to_csv("sales.csv", index=False)
        orders.to_csv("orders.csv", index=False)
        print("Exported sales.csv and orders.csv")

        # All-time summary
        summary_end = args.summary_end
        if summary_end is None and args.biweekly_start:
            summary_end = _derive_dates(args.biweekly_start)["summary_end"]
        elif summary_end is None:
            summary_end = "2026-07-20"

        print("Computing all-time summary...")
        full_summary = report_table(args.summary_start, summary_end, orders, sales)
        full_summary.set_index("index").to_csv("summary.csv")
        full_summary.set_index("index").T.to_csv("summary_transposed.csv")
        print("Exported summary.csv and summary_transposed.csv")

    # -------------------------------------------------------------------
    # Step 2: Upload to BigQuery
    # -------------------------------------------------------------------
    if args.upload:
        print("Uploading to BigQuery...")
        upload_to_bigquery(sales, orders, full_summary)

    # -------------------------------------------------------------------
    # Step 3: Bi-weekly report + Kitchen Pars
    # -------------------------------------------------------------------
    if args.biweekly_start:
        dates = _derive_dates(args.biweekly_start)
        report_dir = Path(args.output_dir) / dates["release_dir"]
        report_dir.mkdir(parents=True, exist_ok=True)

        # Bi-weekly summary
        print(f"Generating bi-weekly report for {args.biweekly_start}...")
        generate_biweekly_report(
            args.biweekly_start, orders, sales,
            output_dir=args.output_dir,
        )

        # Kitchen Pars for each week
        try:
            from .weekly_orders import generate_kitchen_pars

            for week_label, checkdt_ref in [
                (dates["w1_label"], dates["w1_checkdt_ref"]),
                (dates["w2_label"], dates["w2_checkdt_ref"]),
            ]:
                out_path = report_dir / f"KitchenPars{week_label}.xlsx"
                print(f"Generating {out_path.name}...")
                generate_kitchen_pars(
                    sales_df=sales,
                    orders_df=orders,
                    summary_csv="summary_transposed.csv",
                    recent_week_ref_date=checkdt_ref,
                    output_path=str(out_path),
                )
        except ImportError:
            print("Skipping KitchenPars (weekly_orders.py not found in restaurant/)")
        except Exception as e:
            print(f"KitchenPars failed: {e}")
            print("You can still run weekly_orders.py standalone.")

    print("Done.")


if __name__ == "__main__":
    main()
