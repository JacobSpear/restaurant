"""
Merge Toast + Tock data and apply experience/dining-area flags.
"""

from __future__ import annotations

import pandas as pd

from . import config as cfg
from .data_loaders import (
    compute_service_charge,
    load_tock,
    load_toast_orders,
    load_toast_sales,
)
from .utils import assign_lookup

pd.options.mode.chained_assignment = None


def _classify_experience(row: pd.Series) -> str:
    """Classify an order as Redundant / Tasting / A La Carte / Other."""
    if (
        not row["Walk-In Tasting"]
        and (
            row["Toast Taste Flag"]
            or (row["source"] == "tock" and row["Total"] == 0)
        )
    ):
        return "Redundant"
    if row["Walk-In Tasting"] or (
        row["source"] == "tock"
        and row.get("Experience") in cfg.TASTING_PRECISE_EXPERIENCES
    ):
        return "Tasting"
    if row["source"] == "toast":
        return "A La Carte"
    return "Other"


def build_datasets(
    tock_file: str = cfg.TOCK_FILE,
    data_dir: str = ".",
    toast_start: str = cfg.TOAST_MONTHS_START,
    toast_month_count: int = cfg.TOAST_MONTHS_COUNT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the full ingest pipeline and return ``(orders, sales)``.

    Both DataFrames include a ``source`` column (``"toast"`` or ``"tock"``).
    """
    # 1. Load raw data
    toast_sales = load_toast_sales(toast_start, toast_month_count, data_dir)
    toast_orders = load_toast_orders(data_dir)
    sc = compute_service_charge(toast_sales, toast_orders)
    toast_orders = pd.merge(toast_orders, sc, how="left", on="Order Id")

    tock_orders, tock_sales, all_addon_items, event_experiences = load_tock(tock_file, data_dir)

    # 2. Check for uncategorised Tock items
    known = (
        cfg.TOGO_BOTTLES | cfg.MERCH | cfg.TASTING_BOTTLES
        | cfg.TASTING_PAIRINGS | cfg.DESSERT_CAKE | cfg.PACKAGED_FOOD
        | cfg.RICE | cfg.OTHER_TOCK_FOOD | cfg.EVENT_UPGRADE
    )
    uncategorised = all_addon_items - known
    if uncategorised:
        print("WARNING – Tock items to be categorised:", uncategorised)
    else:
        print("No Tock items uncategorised.")

    # 3. Concatenate sources
    sales = (
        pd.concat([toast_sales, tock_sales], keys=["toast", "tock"])
        .reset_index(level=1, drop=True)
        .reset_index()
        .rename(columns={"index": "source"})
    )
    orders = (
        pd.concat([toast_orders, tock_orders], keys=["toast", "tock"])
        .reset_index(level=1, drop=True)
        .reset_index()
        .rename(columns={"index": "source"})
    )

    # 4. Gift-card adjustment
    gc = (
        sales.loc[
            (sales["Menu Item"] == "Gift Card") & (sales["source"] == "toast"),
            ["Order Id", "Net Receivable"],
        ]
        .groupby("Order Id")
        .sum()
        .reset_index()
        .rename(columns={"Net Receivable": "Gift Card Total"})
    )
    orders = pd.merge(orders, gc, how="left", on="Order Id")

    # 5. Remove service charge from Tock order amounts
    orders["Amount_NSC"] = [
        amt if src == "tock" else amt - sc_val
        for src, amt, sc_val in zip(
            orders["source"], orders["Amount"], orders["Service Charge"]
        )
    ]
    orders = orders.drop("Amount", axis=1).rename(columns={"Amount_NSC": "Amount"})

    # 6. Toast tasting flag
    toast_s = sales.loc[sales["source"] == "toast"]
    toast_o = orders.loc[orders["source"] == "toast"]
    toast = pd.merge(toast_o, toast_s, on="Order Id")

    taste_cond = toast["Menu Item"].str.contains("taste", case=False, na=False)
    for kw in cfg.TASTING_MENU_KEYWORDS:
        taste_cond = taste_cond | toast["Menu"].str.contains(kw, case=False, na=False)
    taste_order_ids = toast.loc[taste_cond, "Order Id"].unique()

    bev_only_ids = toast[
        toast.groupby("Order Id")["Sales Category"].transform(
            lambda x: x.isin(
                cfg.BEV_CATEGORIES
            ).all()
        )
    ]["Order Id"].unique()
    indoor_ids = toast_o.loc[
        toast_o["Dining Area"].isin({cfg.DINING_AREA_MAIN, cfg.DINING_AREA_BAR})
    ]["Order Id"].unique()
    bev_indoor_ids = list(set(bev_only_ids) & set(indoor_ids))

    walkin_ids = toast_s[
        (toast_s["Menu Item"].isin(cfg.WALKIN_TASTING_ITEMS))
        & (toast_s["Net Receivable"] > 0)
    ]["Order Id"].unique()

    unique_taste_ids = set(taste_order_ids) | set(bev_indoor_ids)
    orders["Toast Taste Flag"] = orders["Order Id"].isin(unique_taste_ids)
    orders["Walk-In Tasting"] = orders["Order Id"].isin(walkin_ids)

    # 7. Experience category
    orders["Experience Category"] = orders.apply(_classify_experience, axis=1)

    # 8. Fill dining area for Tock
    dining_area_dict = {
        "Dining Room": list(cfg.TASTING_EXPERIENCES),
        "Other": list(cfg.ALC_EXPERIENCES) + list(event_experiences),
    }
    assign_lookup(orders, "Experience", "Tock Dining Area", dining_area_dict)
    orders["Dining Area"] = orders["Dining Area"].fillna(orders["Tock Dining Area"])

    # 9. Merge dining area into sales
    sales = pd.merge(
        sales,
        orders[["Order Id", "Dining Area", "Table"]],
        on="Order Id",
    )

    return orders, sales
