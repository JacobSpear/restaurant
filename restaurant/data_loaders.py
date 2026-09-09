"""
Data loaders for Toast and Tock CSV files.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as cfg
from .utils import (
    assign_lookup,
    get_after_first_word,
    next_month,
    unique_values,
)

pd.options.mode.chained_assignment = None


# ---------------------------------------------------------------------------
# Toast helpers
# ---------------------------------------------------------------------------

def _classify_sales_category(row: pd.Series) -> str | None:
    """Assign a sales category to an uncategorised Toast line item."""
    cat = row["Sales Category"]
    if cat == cat:  # not NaN
        return cat
    menu = row["Menu"]
    item = row["Menu Item"]
    if menu in ("Beer", "Liquor", "Wine"):
        return menu
    if menu == "Cocktails" or item in cfg.LIQUOR_ITEMS:
        return "Liquor"
    if item in cfg.FOOD_ITEMS:
        return "Food"
    if item in cfg.BEER_ITEMS:
        return "Beer"
    if item in cfg.WINE_ITEMS:
        return "Wine"
    if item in cfg.NA_BEV_ITEMS:
        return "NA Beverage"
    if menu == "NA Beverages":
        return "NA Beverage"
    if item in cfg.RETAIL_ITEMS:
        return "Retail"
    if menu in ("A La Carte Menu", "BDAY PARTY FOOD"):
        return "Food"
    return None


def read_toast_month(month_str: str, data_dir: str = ".") -> pd.DataFrame:
    """Read a single month's Toast sales CSV (``toast_MM_YYYY.csv``)."""
    path = Path(data_dir) / f"toast_{month_str}.csv"
    return pd.read_csv(path, encoding="ISO-8859-1")


def load_toast_sales(
    start: str = cfg.TOAST_MONTHS_START,
    count: int = cfg.TOAST_MONTHS_COUNT,
    data_dir: str = ".",
) -> pd.DataFrame:
    """Concatenate monthly Toast sales CSVs and clean/categorise them."""
    month = start
    frames: list[pd.DataFrame] = []
    for _ in range(count):
        frames.append(read_toast_month(month, data_dir))
        month = next_month(month)

    df = pd.concat(frames).reset_index(drop=True)
    df["Date"] = [
        datetime.datetime.strptime(x, "%m/%d/%y %H:%M %p").date()
        for x in df["Order Date"]
    ]
    df["Net Receivable"] = np.where(df["Void?"], 0, df["Net Price"])
    df.loc[df["Deferred"] == True, "Sales Category"] = "Gift Card"
    df["Sales Category"] = df.apply(_classify_sales_category, axis=1)

    keep_cols = [
        "Order Id", "Date", "Order Date", "Dining Option", "Master Id",
        "Menu Item", "Menu", "Menu Group", "Sales Category", "Gross Price",
        "Discount", "Net Price", "Net Receivable", "Qty", "Tax", "Void?",
        "Deferred", "Tax Exempt", "Tax Inclusion Option", "Tab Name",
    ]
    return df[keep_cols]


def load_toast_orders(data_dir: str = ".") -> pd.DataFrame:
    """Concatenate quarterly Toast order CSVs."""
    frames: list[pd.DataFrame] = []
    for quarter in cfg.TOAST_QUARTER_LIST:
        path = Path(data_dir) / f"ToastOrders{quarter}.csv"
        frames.append(pd.read_csv(path, encoding="ISO-8859-1"))

    df = pd.concat(frames).reset_index(drop=True)
    df["Date"] = [
        datetime.datetime.strptime(x, "%m/%d/%y %H:%M %p").date()
        for x in df["Opened"]
    ]
    keep_cols = [
        "Order Id", "Opened", "Date", "# of Guests", "Tab Names", "Server",
        "Table", "Revenue Center", "Dining Area", "Service",
        "Discount Amount", "Amount", "Tax", "Tip", "Total", "Voided",
    ]
    return df[keep_cols]


def compute_service_charge(
    sales: pd.DataFrame,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Compute per-order service charge as ``Amount - sum(Net Receivable)``.

    Returns a DataFrame with columns ``[Order Id, Service Charge, Tax on Service]``.
    """
    totals = sales.groupby("Order Id")["Net Receivable"].sum().to_frame()
    order_amounts = orders[["Order Id", "Amount"]].set_index("Order Id")
    merged = pd.merge(totals, order_amounts, how="outer",
                       left_index=True, right_index=True).reset_index()

    sc = []
    for i in range(len(merged)):
        nr = merged["Net Receivable"].iloc[i]
        if nr != 0 and not np.isnan(nr):
            sc.append(round(merged["Amount"].iloc[i] - nr, 2))
        else:
            sc.append(float("nan"))
    merged["Service Charge"] = sc
    merged["Tax on Service"] = [round(0.065 * x, 2) for x in merged["Service Charge"]]
    return merged[["Order Id", "Service Charge", "Tax on Service"]]


# ---------------------------------------------------------------------------
# Tock helpers
# ---------------------------------------------------------------------------

def _item_to_tuple(item: str) -> list:
    """Parse a Tock add-on string into ``[qty, item_name, price]``."""
    qty_str = item.split()[0]
    item_name = "Tock " + get_after_first_word(item.split("(")[0])
    price_str = item.split()[-1]
    return [
        int(qty_str.replace(",", "")),
        item_name,
        float(price_str.replace(")", "").replace("(", "")),
    ]


def _split_addons(addons) -> list[str]:
    """Split a comma-separated add-on string; return ``[]`` for NaN."""
    if addons == addons:  # not NaN
        return addons.split(",")
    return []


def _fix_addon_text(text) -> str:
    """Replace problematic comma usage inside item names."""
    if text == text:
        return text.replace("frozen, fry", "frozen: fry")
    return text


def load_tock(
    tock_file: str = cfg.TOCK_FILE,
    data_dir: str = ".",
) -> tuple[pd.DataFrame, pd.DataFrame, set[str], set[str]]:
    """Read and process Tock daily-details CSV.

    Returns ``(tock_orders, tock_sales, all_addon_items, event_experiences)``.
    """
    path = Path(data_dir) / tock_file
    tock = pd.read_csv(path)
    tock["Add-ons"] = tock["Add-ons"].apply(_fix_addon_text)

    # Determine event experiences from the data
    all_experiences = unique_values(tock, "Experience")
    event_experiences = all_experiences - cfg.ALC_EXPERIENCES - cfg.TASTING_EXPERIENCES

    # Build runtime dicts that include events
    menu_dict = dict(cfg.MENU_DICT)
    menu_dict["Events"] = event_experiences | cfg.EVENT_UPGRADE
    menu_group_dict = dict(cfg.MENU_GROUP_DICT)
    menu_group_dict["Events"] = event_experiences | cfg.EVENT_UPGRADE

    # --- Build tock_orders ---
    order_id = [x + 3_000_000_000_000_000 for x in tock["Reservation ID"]]
    discount_amount = tock[["Comps", "Outstanding payments"]].max(axis=1)
    tock["Comps"] = discount_amount.copy()
    service_charge_raw = tock["Service charge"]
    refunds = tock["Outstanding payments"]

    amount_flag = np.where(
        (tock["Gross receivable.1"] == 0) & (tock["Gross subtotal"] > 0)
        & (tock["Status"] != "Cancelled"),
        0, 1,
    )
    service_charge = [a * b for a, b in zip(service_charge_raw, amount_flag)]
    amount = [
        t - f * (tx + tip + sc + ref)
        for t, tx, tip, sc, ref, f in zip(
            tock["Gross receivable.1"], tock["Taxes"], tock["Gratuities"],
            service_charge, refunds, amount_flag,
        )
    ]
    discount_tot = [max(x, y) for x, y in zip(discount_amount, refunds)]
    voided = [
        (tock["Status"].iloc[i] == "Cancelled") and (tock["Credit card refunds"].iloc[i] > 0)
        for i in range(len(tock))
    ]

    tock_orders = pd.DataFrame({
        "Order Id": order_id,
        "Opened": tock["Reservation date"],
        "# of Guests": tock["Party size"],
        "Tab Names": [
            f"{fn} {ln}"
            for fn, ln in zip(tock["First name"].fillna(""), tock["Last name"].fillna(""))
        ],
        "Status": tock["Status"],
        "Discount Amount": discount_tot,
        "Amount": amount,
        "Tax": tock["Taxes"],
        "Tax on Service": [round(0.065 * x, 2) for x in service_charge],
        "Tip": tock["Gratuities"],
        "Service Charge": service_charge,
        "Total": tock["Gross receivable.1"],
        "Voided": voided,
        "Experience": tock["Experience"],
    })
    tock_orders["Date"] = [
        datetime.datetime.strptime(x, "%Y-%m-%d").date()
        for x in tock_orders["Opened"]
    ]

    # --- Build tock_sales (explode add-ons) ---
    addon_lists = [_split_addons(x) for x in tock["Add-ons"]]
    all_addon_items: set[str] = set()
    rows: list[pd.Series] = []

    for i, addons in enumerate(addon_lists):
        if not addons:
            rows.append(tock.iloc[i])
        else:
            base_row = tock.iloc[i]
            for addon_str in addons:
                parsed = _item_to_tuple(addon_str)
                row = base_row.copy()
                row["Item Qty"] = parsed[0]
                row["Item Name"] = parsed[1]
                row["Item Gross Price"] = parsed[2]
                row["Add-On?"] = True
                rows.append(row)
                all_addon_items.add(parsed[1])

    df = pd.DataFrame(rows)
    df.dropna(subset=["Item Name"], inplace=True)

    # Experience-level rows
    df_exp = tock.loc[tock["Extended price for party"] > 0].copy()
    df_exp["Item Qty"] = df_exp["Party size"]
    df_exp["Item Name"] = df_exp["Experience"]
    df_exp["Item Gross Price"] = df_exp["Extended price for party"]
    df_exp["Add-On?"] = False

    df_all = pd.concat([df, df_exp])

    # Build line-level sales frame
    sales_order_id = [x + 3_000_000_000_000_000 for x in df_all["Reservation ID"]]
    df2 = pd.DataFrame({
        "Order Id": sales_order_id,
        "Menu Item": df_all["Item Name"].values,
        "Gross Price": df_all["Item Gross Price"].values,
        "Qty": df_all["Item Qty"].values,
        "Discount Flag": (df_all["Comps"].values > 0)
                         & (df_all["Add-ons"].values == df_all["Add-ons"].values)
                         & (df_all["Comps"].values > df_all["Extended price for party"].values),
        "Add-On?": df_all["Add-On?"].values,
        "Comps": df_all["Comps"].values,
    })

    # Compute per-item discounts
    df2 = df2.sort_values(
        by=["Order Id", "Add-On?", "Comps"],
        ascending=[True, True, True],
    )
    discounts: list[float] = []
    prev_order = None
    av_disc = 0.0
    for i in range(len(df2)):
        row = df2.iloc[i]
        if row["Order Id"] != prev_order:
            av_disc = row["Comps"]
            prev_order = row["Order Id"]

        if row["Discount Flag"] and row["Add-On?"]:
            disc = row["Gross Price"]
            av_disc -= disc
        elif not row["Add-On?"]:
            disc = min(av_disc, row["Gross Price"])
            av_disc = 0
        else:
            disc = 0
        discounts.append(disc)

    df2["Discount"] = discounts
    df2["Net Price"] = df2["Gross Price"] - df2["Discount"]
    df2["Tax"] = [round(0.065 * x, 2) for x in df2["Net Price"]]

    tock_sales = pd.merge(
        df2,
        tock_orders[["Order Id", "Date", "Voided"]],
        on="Order Id",
    )
    assign_lookup(tock_sales, "Menu Item", "Menu", menu_dict)
    assign_lookup(tock_sales, "Menu Item", "Menu Group", menu_group_dict)
    assign_lookup(tock_sales, "Menu Item", "Sales Category", cfg.SALES_CATEGORY_DICT)

    return tock_orders, tock_sales, all_addon_items, event_experiences
