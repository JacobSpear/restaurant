from __future__ import annotations

import datetime

import pandas as pd

from . import config as cfg
from .utils import daterange

pd.options.mode.chained_assignment = None


# ---------------------------------------------------------------------------
# Per-day summary builders
# ---------------------------------------------------------------------------

def _filter_by_area(
    orders: pd.DataFrame,
    sales: pd.DataFrame,
    area: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (orders, sales) filtered to the specified dining area.

    area: 0=all, 1=Dining Room, 2=Bar, 3=Outdoor.
    """
    if area == 0:
        return orders, sales
    if area == 1:
        return (
            orders.loc[orders["Dining Area"] == cfg.DINING_AREA_MAIN],
            sales.loc[sales["Dining Area"] == cfg.DINING_AREA_MAIN],
        )
    if area == 2:
        return (
            orders.loc[orders["Dining Area"] == cfg.DINING_AREA_BAR],
            sales.loc[sales["Dining Area"] == cfg.DINING_AREA_BAR],
        )
    if area == 3:
        patio_areas = cfg.PATIO_AREA_NAMES
        patio_tbl = cfg.PATIO_TABLES
        o_mask = (
            orders["Dining Area"].isin(patio_areas)
            | (orders["Dining Area"].isna() & orders["Table"].isin(patio_tbl))
        )
        s_mask = (
            sales["Dining Area"].isin(patio_areas)
            | (sales["Dining Area"].isna() & sales["Table"].isin(patio_tbl))
        )
        return orders.loc[o_mask], sales.loc[s_mask]
    return orders, sales


def toast_summary(
    date_str: str,
    orders: pd.DataFrame,
    sales: pd.DataFrame,
    area: int = 0,
) -> dict[str, float]:
    """Compute a single-day Toast revenue breakdown."""
    orders0, sales0 = _filter_by_area(orders, sales, area)
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    o1 = orders0.loc[(orders0["source"] == "toast") & (orders0["Date"] == dt)]
    s1 = sales0.loc[(sales0["source"] == "toast") & (sales0["Date"] == dt)].copy()
    s1["Sales Category"] = s1["Sales Category"].fillna("No Sales Category")

    mgd = pd.merge(
        o1[["Order Id", "Toast Taste Flag"]], s1,
        on="Order Id", how="left",
    )

    d: dict[str, float] = {}
    d["Food/Walk-In"] = s1.loc[s1["Sales Category"] == "Food", "Net Receivable"].sum()
    d["Tasting"] = mgd.loc[mgd["Toast Taste Flag"] == True, "Net Receivable"].sum()
    d["Tasting Food"] = mgd.loc[
        (mgd["Sales Category"] != "Wine")
        & (mgd["Sales Category"] != "NA Beverage")
        & (mgd["Toast Taste Flag"] == True)
        & (mgd["Menu"].isin(cfg.TASTING_VS_ALC_MENUS)),
        "Net Receivable",
    ].sum()
    d["NA"] = s1.loc[s1["Sales Category"] == "NA Beverage", "Net Receivable"].sum()
    d["Beer"] = s1.loc[
        s1["Sales Category"].isin({"Beer", "Bottled Beer", "Draft Beer"}),
        "Net Receivable",
    ].sum()
    d["Wine"] = s1.loc[s1["Sales Category"] == "Wine", "Net Receivable"].sum()
    d["Liquor"] = s1.loc[s1["Sales Category"] == "Liquor", "Net Receivable"].sum()
    d["No Sales Category"] = s1.loc[
        s1["Sales Category"] == "No Sales Category", "Net Receivable"
    ].sum()
    d["Service Charge"] = o1["Service Charge"].sum()
    d["Bev"] = d["NA"] + d["Beer"] + d["Wine"] + d["Liquor"]
    d["Retail"] = s1.loc[s1["Sales Category"] == "Retail", "Net Receivable"].sum()

    # Location breakdown
    patio_areas = cfg.PATIO_AREA_NAMES
    d["Bar"] = o1.loc[o1["Dining Area"] == cfg.DINING_AREA_BAR, "Amount"].sum()
    d[cfg.OUTDOOR_AREA_LABEL] = o1.loc[
        o1["Dining Area"].isin(patio_areas)
        | (o1["Dining Area"].isna() & o1["Table"].isin(cfg.PATIO_TABLES)),
        "Amount",
    ].sum()
    d["Dining Room"] = o1.loc[o1["Dining Area"] == cfg.DINING_AREA_MAIN, "Amount"].sum()
    d["No Dining Area"] = o1.loc[
        o1["Dining Area"].isna() & ~o1["Table"].isin(cfg.PATIO_TABLES),
        "Amount",
    ].sum()

    d["Card Tips"] = o1["Tip"].sum()
    d["Gift Card"] = o1["Gift Card Total"].sum()
    d["Net"] = (
        d["Food/Walk-In"] + d["Bev"] + d["Service Charge"]
        + d["No Sales Category"] + d["Retail"]
    )
    return {k: round(v, 2) for k, v in d.items()}


def tock_summary(
    date_str: str,
    orders: pd.DataFrame,
    sales: pd.DataFrame,
    area: int = 0,
) -> dict[str, float]:
    """Compute a single-day Tock revenue breakdown."""
    if area == 0:
        o0, s0 = orders, sales
    elif area == 1:
        o0 = orders.loc[orders["Dining Area"] == cfg.DINING_AREA_MAIN]
        s0 = sales.loc[sales["Dining Area"] == cfg.DINING_AREA_MAIN]
    else:
        # Bar / Outdoor have no Tock orders in practice
        o0 = orders.loc[orders["Dining Area"] == "XXX"]
        s0 = sales.loc[sales["Dining Area"] == "NA"]

    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    o1 = o0.loc[(o0["source"] == "tock") & (o0["Voided"] != True)]
    s1 = s0.loc[(s0["source"] == "tock") & (s0["Voided"] != True)]

    ds = o1.loc[o1["Date"] == dt]
    st = s1.loc[s1["Date"] == dt]

    d: dict[str, float] = {}
    d["Service Charge"] = ds["Service Charge"].sum()
    d["Discounts"] = ds["Discount Amount"].sum() * -1

    for grp in set(st["Menu Group"]) - {""}:
        d[grp] = st.loc[st["Menu Group"] == grp, "Net Price"].sum()

    d_temp = dict(d)
    d_temp["Discounts"] *= -1
    d["Sales"] = sum(d_temp.values())
    d["Sales-Discounts"] = d["Sales"] + d["Discounts"]
    d["Food"] = st.loc[st["Sales Category"] == "Food", "Net Price"].sum()
    d["Bev"] = st.loc[
        st["Sales Category"].isin({"Wine", "Liquor", "NA Beverage"}),
        "Net Price",
    ].sum()
    return d


# ---------------------------------------------------------------------------
# Row-ordering helper
# ---------------------------------------------------------------------------

def _get_row_order(label: str) -> list[int]:
    """Return a ``[primary, secondary, tertiary]`` sort key for a row label."""
    order = [0, 0, 0]
    if "Tock" in label:
        order[0] = 0
        tock_map = {
            "Tock Sales": (0, 0), "Tock Sales-Discounts": (0, 1),
            "Tock Food": (0, 2), "Tock Bev": (0, 3),
            "Tock Discounts": (2, 1), "Tock Service Charge": (2, 0),
        }
        if label in tock_map:
            order[1], order[2] = tock_map[label]
        else:
            order[1] = 1
    elif "Toast" in label:
        order[0] = 1
        toast_map = {
            "Toast Net": (0, 1), "Toast Bev": (1, 0), "Toast NA": (1, 1),
            "Toast Liquor": (1, 2), "Toast Beer": (1, 3), "Toast Wine": (1, 4),
            "Toast Bar": (2, 1), f"Toast {cfg.OUTDOOR_AREA_LABEL}": (2, 2),
            "Toast Dining Room": (2, 3), "Toast No Dining Area": (2, 3),
            "Toast Service Charge": (3, 1), "Toast Retail": (4, 1),
            "Toast Card Tips": (3, 2), "Toast Gift Card": (3, 3),
        }
        if label in toast_map:
            order[1], order[2] = toast_map[label]
    else:
        order[0] = 3
    return order


# ---------------------------------------------------------------------------
# Multi-day reports
# ---------------------------------------------------------------------------

def daily_summary(
    start_date: str,
    end_date: str,
    orders: pd.DataFrame,
    sales: pd.DataFrame,
    area: int = 0,
) -> pd.DataFrame:
    """Produce a table with one column per date and one row per revenue category."""
    sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    # First pass: discover all row labels
    all_rows: set[str] = set()
    for single_date in daterange(sd, ed):
        ds = single_date.strftime("%Y-%m-%d")
        ts = {"Toast " + k: v for k, v in toast_summary(ds, orders, sales, area).items()}
        tk = {"Tock " + k: v for k, v in tock_summary(ds, orders, sales, area).items()}
        all_rows |= set(ts.keys()) | set(tk.keys())

    # Second pass: fill values
    results: dict[str, list] = {}
    for single_date in daterange(sd, ed):
        ds = single_date.strftime("%Y-%m-%d")
        ts = {"Toast " + k: v for k, v in toast_summary(ds, orders, sales, area).items()}
        tk = {"Tock " + k: v for k, v in tock_summary(ds, orders, sales, area).items()}
        results.setdefault("Date", []).append(ds)
        for item in all_rows:
            val = tk.get(item, ts.get(item, 0.0))
            results.setdefault(item, []).append(val)

    # Derived totals
    n = len(results["Date"])
    _z = [0] * n
    results["Wine+Pairings"] = [
        a + b + c for a, b, c in zip(
            results.get("Tock Tasting Bottles", _z),
            results.get("Tock Tasting Pairings", _z),
            results["Toast Wine"],
        )
    ]
    results["Total Tasting"] = [a + b for a, b in zip(results["Tock Food"], results["Toast Tasting"])]
    results["Total ALC"] = [a - b for a, b in zip(results["Toast Food/Walk-In"], results["Toast Tasting Food"])]
    results["Total Bev"] = [a + b for a, b in zip(results["Tock Bev"], results["Toast Bev"])]
    results["Total Food"] = [a + b for a, b in zip(results["Tock Food"], results["Toast Food/Walk-In"])]
    results["Total Service"] = [a + b for a, b in zip(results["Tock Service Charge"], results["Toast Service Charge"])]
    results["Total"] = [a + b for a, b in zip(results["Tock Sales-Discounts"], results["Toast Net"])]

    return pd.DataFrame(results)


def report_table(
    start_date: str,
    end_date: str,
    orders: pd.DataFrame,
    sales: pd.DataFrame,
    area: int = 0,
) -> pd.DataFrame:
    """Sorted daily-summary with a ``Total`` column, ready for output."""
    df = daily_summary(start_date, end_date, orders, sales, area)
    df = df.set_index("Date").transpose().reset_index()

    sort_keys = pd.DataFrame(
        {x[0]: _get_row_order(x[0]) for x in df[["index"]].values}
    ).T.rename(columns={0: "k0", 1: "k1", 2: "k2"}).reset_index()
    merged = pd.merge(df, sort_keys, on="index")
    merged = merged.sort_values(by=["k0", "k1", "k2"]).drop(
        columns=["k0", "k1", "k2"]
    ).reset_index(drop=True)
    non_index_cols = [c for c in merged.columns if c != "index"]
    merged["Total"] = merged[non_index_cols].sum(axis=1)
    return merged