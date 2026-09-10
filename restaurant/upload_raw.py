#!/usr/bin/env python3
"""
Upload raw source data to BigQuery.

Handles partition-safe uploads for Toast data (replace current month/quarter
without touching closed periods) and full-replace for Tock and covers.

Usage:
    # First-time: upload everything
    python upload_raw.py --data-dir . --all

    # Regular run: just the current period
    python upload_raw.py --data-dir . --toast-sales --month 08_2026 \
                                      --toast-orders --quarter Q3_2026 \
                                      --covers

    # One-time Tock upload
    python upload_raw.py --data-dir . --tock
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

try:
    from . import config as cfg
except ImportError:
    import config as cfg

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_ID = cfg.BQ_PROJECT
DATASET = cfg.BQ_DATASET
FULL_DATASET = f"{PROJECT_ID}.{DATASET}"

# Default file patterns — adjust if yours differ
TOAST_SALES_PATTERN = "toast_{month}.csv"       # e.g. toast_01_2023.csv
TOAST_ORDERS_PATTERN = "ToastOrders{quarter}.csv"  # e.g. ToastOrdersQ1_2023.csv
TOCK_FILE = cfg.TOCK_FILE
COVERS_FILE = "covers.csv"


def _get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _table_ref(table_name: str) -> str:
    return f"{FULL_DATASET}.{table_name}"


def _delete_partition(client: bigquery.Client, table: str, column: str, value: str):
    """Delete all rows where partition column == value."""
    query = f"DELETE FROM `{_table_ref(table)}` WHERE `{column}` = @val"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("val", "STRING", value)]
    )
    try:
        client.query(query, job_config=job_config).result()
    except Exception as e:
        # Table might not exist yet — that's fine
        if "Not found" in str(e):
            pass
        else:
            raise


def _sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make column names BigQuery-safe: letters, numbers, underscores only."""
    df = df.copy()
    df.columns = [
        re.sub(r"[^a-zA-Z0-9_]", "_", col).rstrip("_")
        for col in df.columns
    ]
    return df


def _upload_df(client: bigquery.Client, df: pd.DataFrame, table: str,
               if_exists: str = "append", all_strings: bool = False):
    """Upload a DataFrame to BigQuery."""
    df = _sanitize_columns(df)
    if all_strings:
        df = df.astype(str).replace("nan", None)
    destination = _table_ref(table)
    write_disp = (
        bigquery.WriteDisposition.WRITE_TRUNCATE if if_exists == "replace"
        else bigquery.WriteDisposition.WRITE_APPEND
    )
    job_config = bigquery.LoadJobConfig(write_disposition=write_disp)
    if if_exists != "replace":
        job_config.schema_update_options = [
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
        ]
    job = client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()  # wait for completion
    print(f"  Uploaded {len(df):,} rows to {destination}")


# ── Toast Sales ──────────────────────────────────────────────────────────────

def _discover_toast_sales_files(data_dir: Path) -> dict[str, Path]:
    """Find all toast_MM_YYYY.csv files. Returns {month_str: path}."""
    files = {}
    for f in sorted(data_dir.glob("toast_*.csv")):
        match = re.match(r"toast_(\d{2}_\d{4})\.csv", f.name)
        if match:
            files[match.group(1)] = f
    return files


def upload_toast_sales(data_dir: Path, month: str | None = None):
    """Upload Toast monthly sales CSVs.

    If month is specified (e.g. "08_2026"), uploads only that month
    and replaces any existing data for it. Otherwise uploads all months.
    """
    client = _get_client()
    all_files = _discover_toast_sales_files(data_dir)

    if month:
        if month not in all_files:
            print(f"  File not found for month {month}")
            return
        files = {month: all_files[month]}
    else:
        files = all_files

    print(f"Uploading Toast sales ({len(files)} file(s))...")

    for month_str, path in sorted(files.items()):
        df = pd.read_csv(path, encoding="ISO-8859-1", low_memory=False)
        df["upload_partition"] = month_str

        # Replace this month's partition
        _delete_partition(client, "raw_toast_sales", "upload_partition", month_str)
        _upload_df(client, df, "raw_toast_sales", if_exists="append", all_strings=True)


# ── Toast Orders ─────────────────────────────────────────────────────────────

def _discover_toast_orders_files(data_dir: Path) -> dict[str, Path]:
    """Find all ToastOrdersQN_YYYY.csv files. Returns {quarter_str: path}."""
    files = {}
    for f in sorted(data_dir.glob("ToastOrders*.csv")):
        match = re.match(r"ToastOrders(Q\d_\d{4})\.csv", f.name)
        if match:
            files[match.group(1)] = f
    return files


def upload_toast_orders(data_dir: Path, quarter: str | None = None):
    """Upload Toast quarterly order CSVs.

    If quarter is specified (e.g. "Q3_2026"), uploads only that quarter
    and replaces any existing data for it. Otherwise uploads all quarters.
    """
    client = _get_client()
    all_files = _discover_toast_orders_files(data_dir)

    if quarter:
        if quarter not in all_files:
            print(f"  File not found for quarter {quarter}")
            return
        files = {quarter: all_files[quarter]}
    else:
        files = all_files

    print(f"Uploading Toast orders ({len(files)} file(s))...")

    for qtr_str, path in sorted(files.items()):
        df = pd.read_csv(path, encoding="ISO-8859-1", low_memory=False)
        df["upload_partition"] = qtr_str

        _delete_partition(client, "raw_toast_orders", "upload_partition", qtr_str)
        _upload_df(client, df, "raw_toast_orders", if_exists="append", all_strings=True)


# ── Tock ─────────────────────────────────────────────────────────────────────

def upload_tock(data_dir: Path, tock_file: str = TOCK_FILE):
    """Upload the Tock daily details CSV (full replace)."""
    print("Uploading Tock data...")
    client = _get_client()
    path = data_dir / tock_file
    df = pd.read_csv(path, low_memory=False)
    _upload_df(client, df, "raw_tock", if_exists="replace", all_strings=True)


# ── Covers ───────────────────────────────────────────────────────────────────

def upload_covers(data_dir: Path, covers_file: str = COVERS_FILE):
    """Upload the covers CSV (full replace)."""
    print("Uploading covers data...")
    client = _get_client()
    path = data_dir / covers_file
    df = pd.read_csv(path, header=None, names=["date", "guests"])
    _upload_df(client, df, "raw_covers", if_exists="replace", all_strings=True)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload raw restaurant source data to BigQuery"
    )
    parser.add_argument("--data-dir", default=".", help="Directory with CSV files")
    parser.add_argument("--all", action="store_true", help="Upload everything")
    parser.add_argument("--toast-sales", action="store_true", help="Upload Toast sales")
    parser.add_argument("--toast-orders", action="store_true", help="Upload Toast orders")
    parser.add_argument("--tock", action="store_true", help="Upload Tock data")
    parser.add_argument("--covers", action="store_true", help="Upload covers")
    parser.add_argument("--month", default=None,
                        help="Specific month to upload (MM_YYYY, e.g. 08_2026)")
    parser.add_argument("--quarter", default=None,
                        help="Specific quarter to upload (e.g. Q3_2026)")
    parser.add_argument("--tock-file", default=TOCK_FILE,
                        help="Tock CSV filename")

    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    upload_all = getattr(args, "all")

    if not any([upload_all, args.toast_sales, args.toast_orders, args.tock, args.covers]):
        parser.print_help()
        return

    if upload_all or args.toast_sales:
        upload_toast_sales(data_dir, month=args.month)

    if upload_all or args.toast_orders:
        upload_toast_orders(data_dir, quarter=args.quarter)

    if upload_all or args.tock:
        upload_tock(data_dir, tock_file=args.tock_file)

    if upload_all or args.covers:
        upload_covers(data_dir)

    print("Done.")


if __name__ == "__main__":
    main()
