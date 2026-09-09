"""
Ad-hoc analytical routines: covers analysis, bar revenue statistics,
and day-of-week difference-in-means testing.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy import stats

from .summaries import report_table


# ---------------------------------------------------------------------------
# Covers analysis
# ---------------------------------------------------------------------------

def build_covers(
    orders: pd.DataFrame,
    covers_csv: str | Path = "covers.csv",
) -> pd.DataFrame:
    """Combine external covers CSV with tasting guest counts.

    Returns a DataFrame with columns ``Date, Covers, Tasting Covers, ALC Covers``.
    """
    tasting = (
        orders.loc[orders["Experience Category"] == "Tasting", ["Date", "# of Guests"]]
        .groupby("Date")
        .sum()
        .reset_index()
    )

    covers = pd.read_csv(covers_csv, header=None)
    covers = covers.loc[covers[0].str.len() == 10]
    covers["Date"] = pd.to_datetime(covers[0], format="%Y-%m-%d")
    covers["Covers"] = covers[1]
    covers = covers[["Date", "Covers"]]

    tasting["Date"] = pd.to_datetime(tasting["Date"])
    merged = pd.merge(covers, tasting, on="Date", how="outer")
    merged = merged.rename(columns={"# of Guests": "Tasting Covers"}).fillna(0)
    merged["ALC Covers"] = merged["Covers"] - merged["Tasting Covers"]
    return merged


# ---------------------------------------------------------------------------
# Bar revenue box-plots
# ---------------------------------------------------------------------------

def bar_revenue_boxplot(
    df: pd.DataFrame,
    column: str = "Total",
    title: str = "Bar Revenue",
) -> None:
    """Display a day-of-week box plot for *column* with trimmed-mean markers."""
    grouped = df.groupby("DOW")[column]
    labels = ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    colors = ["#E49EDD"] * 3 + ["#B5E6A2"] * 2 + ["#E49EDD"]

    t_mean = (
        df.groupby("DOW")[column]
        .apply(lambda x: stats.trim_mean(x, 0.05))
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(8, 6))
    bp = ax.boxplot(
        [group.values for _, group in grouped],
        labels=labels,
    )

    whiskers = [
        [bp["whiskers"][2 * i], bp["whiskers"][2 * i + 1]]
        for i in range(len(bp["whiskers"]) // 2)
    ]
    caps = [
        [bp["caps"][2 * i], bp["caps"][2 * i + 1]]
        for i in range(len(bp["caps"]) // 2)
    ]
    for box, median, wh, cp, color in zip(
        bp["boxes"], bp["medians"], whiskers, caps, colors
    ):
        box.set_color(color)
        median.set_color(color)
        for d in (0, 1):
            wh[d].set_color(color)
            cp[d].set_color(color)

    ax.set_xlabel("Day of Week")
    ax.set_ylabel(f"{title} ($)")
    ax.set_title(f"{title} vs Day of Week")
    ax.scatter(t_mean["DOW"], t_mean[column], color="red", marker="+", s=20, zorder=3)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color="#E49EDD"),
        plt.Rectangle((0, 0), 1, 1, color="#B5E6A2"),
        Line2D([0], [0], marker="+", color="red", linestyle="None",
               markersize=5, markeredgewidth=1.4),
    ]
    ax.legend(legend_handles, ["Weekday", "Weekend", "Trimmed Mean (5%)"])
    plt.tight_layout()
    plt.show()


def bar_revenue_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute trimmed-mean and std-dev table for bar revenue by weeknight vs. Fri/Sat."""
    results = []
    for col in ("Total", "Total Food", "Total Bev"):
        stat = (
            pd.DataFrame({
                f"P{int(100 * q)}": df.groupby("FriSat")[col].quantile(q)
                for q in (0.05, 0.25, 0.5, 0.75, 0.95)
            })
            .assign(
                tm=df.groupby("FriSat")[col].apply(
                    lambda x: stats.trim_mean(x, 0.05)
                ),
                sd=df.groupby("FriSat")[col].apply(
                    lambda x: stats.mstats.trimmed_std(x, limits=(0.05, 0.05))
                ),
            )
            .reset_index()
        )
        stat["Var"] = col
        results.append(stat)

    combined = pd.concat(results)
    combined["Day Category"] = np.select(
        [combined["FriSat"] == 0, combined["FriSat"] == 1],
        ["Weeknight", "Friday or Saturday"],
        default="Other",
    )
    combined["5%-Trimmed Mean +/- (SD)"] = [
        f"${round(t, 2)} +/- ${round(s, 2)}"
        for t, s in zip(combined["tm"], combined["sd"])
    ]
    return combined[["Day Category", "Var", "5%-Trimmed Mean +/- (SD)"]].pivot(
        index="Day Category", columns="Var", values="5%-Trimmed Mean +/- (SD)"
    )


# ---------------------------------------------------------------------------
# Day-of-week adjusted comparison
# ---------------------------------------------------------------------------

def day_of_week_comparison(
    df: pd.DataFrame,
    value_col: str,
    date_col: str,
    threshold: float,
    period1: tuple[str, str] = ("2025-06-01", "2025-06-30"),
    period2: tuple[str, str] = ("2026-06-01", "2026-06-30"),
) -> None:
    """Run an OLS regression comparing two periods, controlling for weekday/weekend.

    Prints descriptive statistics, unadjusted means, and regression output.
    """
    import statsmodels.formula.api as smf

    data = df[[value_col, date_col]].rename(
        columns={value_col: "value", date_col: "date"}
    ).copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data[data["value"] >= threshold]
    data["is_weekend"] = data["date"].dt.dayofweek.isin([4, 5, 6]).astype(int)

    data["period"] = np.select(
        [
            (data["date"] >= period1[0]) & (data["date"] <= period1[1]),
            (data["date"] >= period2[0]) & (data["date"] <= period2[1]),
        ],
        ["Period1", "Period2"],
        default="Exclude",
    )
    data = data[data["period"] != "Exclude"]

    # Descriptive
    grouped = (
        data.groupby(["period", "is_weekend"])["value"]
        .agg(["mean", "median", "std", "count"])
        .rename(index={0: "Weekday (Tue-Thu)", 1: "Weekend (Fri-Sun)"})
    )
    print("\nUnadjusted comparison:")
    print(grouped)

    pivot_m = grouped["mean"].unstack()
    print("\nMean by period and weekday/weekend:")
    print(pivot_m)

    # OLS
    model = smf.ols("value ~ C(period) + is_weekend", data=data).fit()
    print(model.summary())

    coef = model.params["C(period)[T.Period2]"]
    ci_lo, ci_hi = model.conf_int().loc["C(period)[T.Period2]"]
    print(f"\nAdjusted mean difference (P2-P1): {coef:.3f}")
    print(f"95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")


# ---------------------------------------------------------------------------
# CSV comparison utility
# ---------------------------------------------------------------------------

def compare_csvs(file1: str | Path, file2: str | Path) -> None:
    """Compare two summary CSVs cell-by-cell (ignoring Toast Bar)."""
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    if df1.shape != df2.shape:
        print(f"Different shapes: {df1.shape} vs {df2.shape}")
        return

    cols = [c for c in df1.columns if c not in ("Unnamed: 0",) and "Toast" not in c]
    for idx in range(1, len(df1)):
        for col in cols:
            try:
                a, b = float(df1.iloc[idx][col]), float(df2.iloc[idx][col])
                if abs(a - b) > 0.001:
                    date_val = df1.iloc[idx].get("Unnamed: 0", "?")
                    print(f"Mismatch at {date_val}, {col}: {a} vs {b}")
                    return
            except (ValueError, TypeError):
                date_val = df1.iloc[idx].get("Unnamed: 0", "?")
                print(f"Parse issue at {date_val}, {col}")
                return
    print("No mismatches found.")
