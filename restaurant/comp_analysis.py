#!/usr/bin/env python3
"""
Comp & Discount Trend Analysis

Tracks comp/discount rates over time from sales.csv.
Outputs monthly and quarterly summaries + charts.

Usage:
    python comp_analysis.py --data-dir .
    python comp_analysis.py --data-dir . --output-dir ../charts
"""

import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load_sales(data_dir: str) -> pd.DataFrame:
    sales = pd.read_csv(Path(data_dir) / "sales.csv", low_memory=False)
    sales["Date"] = pd.to_datetime(sales["Date"])
    sales["Month"] = sales["Date"].dt.to_period("M")
    sales["Quarter"] = sales["Date"].dt.to_period("Q")
    return sales


def monthly_comp_summary(sales: pd.DataFrame) -> pd.DataFrame:
    """Monthly gross revenue, total discounts/comps, and comp rate."""
    monthly = sales.groupby("Month").agg(
        gross_revenue=("Gross Price", "sum"),
        total_discount=("Discount", "sum"),
        net_revenue=("Net Price", "sum"),
        num_orders=("Order Id", "nunique"),
        num_items=("Gross Price", "count"),
    ).reset_index()

    monthly["comp_rate_pct"] = 100 * monthly["total_discount"] / monthly["gross_revenue"]
    monthly["discount_per_order"] = monthly["total_discount"] / monthly["num_orders"]
    monthly["month_dt"] = monthly["Month"].dt.to_timestamp()
    return monthly


def quarterly_comp_summary(sales: pd.DataFrame) -> pd.DataFrame:
    """Same metrics rolled up quarterly."""
    quarterly = sales.groupby("Quarter").agg(
        gross_revenue=("Gross Price", "sum"),
        total_discount=("Discount", "sum"),
        net_revenue=("Net Price", "sum"),
        num_orders=("Order Id", "nunique"),
    ).reset_index()

    quarterly["comp_rate_pct"] = 100 * quarterly["total_discount"] / quarterly["gross_revenue"]
    quarterly["qtr_dt"] = quarterly["Quarter"].dt.to_timestamp()
    return quarterly


def comp_by_source(sales: pd.DataFrame) -> pd.DataFrame:
    """Monthly comp rate split by source (toast vs tock)."""
    by_source = sales.groupby(["Month", "source"]).agg(
        gross_revenue=("Gross Price", "sum"),
        total_discount=("Discount", "sum"),
    ).reset_index()

    by_source["comp_rate_pct"] = 100 * by_source["total_discount"] / by_source["gross_revenue"]
    by_source["month_dt"] = by_source["Month"].dt.to_timestamp()
    return by_source


def plot_comp_trends(monthly: pd.DataFrame, quarterly: pd.DataFrame,
                     by_source: pd.DataFrame, output_dir: str):
    """Generate comp trend charts."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 14))

    # --- Chart 1: Monthly comp rate ---
    ax1 = axes[0]
    ax1.bar(monthly["month_dt"], monthly["comp_rate_pct"],
            width=25, alpha=0.6, color="#5B7BA5", label="Monthly")
    ax1.plot(monthly["month_dt"], monthly["comp_rate_pct"].rolling(3, min_periods=1).mean(),
             color="#D4564F", linewidth=2, label="3-month avg")
    ax1.set_ylabel("Comp Rate (%)")
    ax1.set_title("Monthly Comp/Discount Rate (Discount / Gross Revenue)")
    ax1.legend()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.tick_params(axis="x", rotation=45)

    # --- Chart 2: Quarterly comp rate ---
    ax2 = axes[1]
    ax2.bar(quarterly["qtr_dt"], quarterly["comp_rate_pct"],
            width=60, alpha=0.7, color="#5B7BA5")
    for i, row in quarterly.iterrows():
        ax2.text(row["qtr_dt"], row["comp_rate_pct"] + 0.1,
                 f'{row["comp_rate_pct"]:.1f}%', ha="center", fontsize=8)
    ax2.set_ylabel("Comp Rate (%)")
    ax2.set_title("Quarterly Comp/Discount Rate")
    ax2.set_xticks(quarterly["qtr_dt"])
    ax2.set_xticklabels([str(q) for q in quarterly["Quarter"]], rotation=45)

    # --- Chart 3: By source ---
    ax3 = axes[2]
    for source, grp in by_source.groupby("source"):
        ax3.plot(grp["month_dt"], grp["comp_rate_pct"],
                 marker="o", markersize=3, linewidth=1.5, label=source.title())
    ax3.set_ylabel("Comp Rate (%)")
    ax3.set_title("Monthly Comp Rate by Source (Toast vs Tock)")
    ax3.legend()
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax3.tick_params(axis="x", rotation=45)

    plt.tight_layout()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path / "comp_trends.pdf", bbox_inches="tight")
    fig.savefig(out_path / "comp_trends.png", dpi=150, bbox_inches="tight")
    print(f"Charts saved to {out_path}/")
    plt.show()


def print_summary(monthly: pd.DataFrame, quarterly: pd.DataFrame):
    """Print key stats to console."""
    print("\n=== COMP/DISCOUNT SUMMARY ===\n")

    latest_q = quarterly.iloc[-1]
    prev_q = quarterly.iloc[-2] if len(quarterly) > 1 else None
    print(f"Latest quarter ({latest_q['Quarter']}):")
    print(f"  Gross Revenue:  ${latest_q['gross_revenue']:,.0f}")
    print(f"  Total Comps:    ${latest_q['total_discount']:,.0f}")
    print(f"  Comp Rate:      {latest_q['comp_rate_pct']:.2f}%")
    if prev_q is not None:
        delta = latest_q["comp_rate_pct"] - prev_q["comp_rate_pct"]
        print(f"  vs Prior Qtr:   {delta:+.2f} pp")

    print(f"\nAll-time comp rate: {100 * monthly['total_discount'].sum() / monthly['gross_revenue'].sum():.2f}%")

    best = monthly.loc[monthly["comp_rate_pct"].idxmin()]
    worst = monthly.loc[monthly["comp_rate_pct"].idxmax()]
    print(f"Lowest comp month: {best['Month']} ({best['comp_rate_pct']:.2f}%)")
    print(f"Highest comp month: {worst['Month']} ({worst['comp_rate_pct']:.2f}%)")


def main():
    parser = argparse.ArgumentParser(description="Comp & Discount Trend Analysis")
    parser.add_argument("--data-dir", default=".", help="Directory containing sales.csv")
    parser.add_argument("--output-dir", default=".", help="Save charts to this directory")
    args = parser.parse_args()

    sales = load_sales(args.data_dir)

    monthly = monthly_comp_summary(sales)
    quarterly = quarterly_comp_summary(sales)
    by_source = comp_by_source(sales)

    print_summary(monthly, quarterly)
    plot_comp_trends(monthly, quarterly, by_source, args.output_dir)

    # Export CSVs
    monthly.drop(columns=["month_dt"]).to_csv("comp_monthly.csv", index=False)
    quarterly.drop(columns=["qtr_dt"]).to_csv("comp_quarterly.csv", index=False)
    print("\nExported comp_monthly.csv and comp_quarterly.csv")


if __name__ == "__main__":
    main()
