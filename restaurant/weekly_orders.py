#!/usr/bin/env python3
"""
Weekly Orders Report Script

This script generates a weekly orders report by:
1. Reading sales, orders, and summary CSV files
2. Normalizing menu items via item2() mapping
3. Building regression models (orders ~ total revenue) per item
4. Computing adjusted weekly estimates for Fri/Sat vs Weeknight
5. Comparing with recent week actual orders
6. Exporting a formatted Excel report
"""

import pandas as pd
import numpy as np
import math
import datetime
import argparse
from datetime import date, timedelta
import statsmodels.api as sm
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, NamedStyle, Alignment


def menu(oval, ival):
    """Classify menu items into categories."""
    if oval == oval:  # Check if not NaN
        return oval
    elif ival in ['Cassava Cake', 'Kalabasa Cheesecake',
                  'Kalabasa Cheese Cake', 'Bellychon', 'Pancit Canton', 'Turon Sundae']:
        return 'A La Carte Menu'
    elif ('caesar' in ival.lower()) or ('cesar' in ival.lower()) or ('ceasar' in ival.lower()):
        return 'A La Carte Menu'
    else:
        return float('nan')


def item2(item):
    """Normalize menu item names."""
    if item in ['Pritong Isda', 'Pritong Isda - Fried Tile Fish', 'Pritong Isda - Halibut', 'Pritong Isda - Blk Drum',
                'Fried Fish', 'Pritong- Crusted Dorade', 'Fresh Catch', 'Pinipig Crusted Fish', 'Pinipig Fish']:
        return 'Pritong Isda'
    elif item in ['Whole Fried Fish', 'Crispy Fried Fish', 'Whole Fried Sea Trout 0.9', 'Whole Fried Sea Trout 1.0']:
        return 'Whole Fried Fish'
    elif item in ['Kinilaw', 'Coconut Kinilaw', 'Tile Kinilaw', 'Tuna Coconut Kinilaw', 'Madai Kinilaw', 'Kinilaw Hipon', 'Kinilaw Isda', 'HH Kinilaw', 'Kinilaw w Chips']:
        return 'Kinilaw'
    elif 'kaldereta' in item.lower():
        return "Kaldereta"
    elif 'binago' in item.lower():
        return "Binagoongan"
    elif 'laing' in item.lower():
        return "Laing"
    elif 'bicol' in item.lower():
        return "Bicol Express"
    elif "swaki" in item.lower():
        return "Wacky+Toast"
    elif (("uni" in item.lower()) and not ('kini' in item.lower())) or ('900' in item.lower()) or ('toast' in item.lower()):
        return "Wacky+Toast"
    elif 'munggo' in item.lower():
        return "pork munngo"
    elif item == 'Turón Sundae':
        return "Turon Sundae"
    elif 'bringhe' in item.lower():
        return "Bringhe"
    elif 'sisig' in item.lower():
        return "Sisig"
    elif 'sariwa' in item.lower():
        return "Sariwa"
    elif ('bicho' in item.lower()) or ('bitso' in item.lower()):
        return "Bitso-Bitso"
    elif ('caesar' in item.lower()) or ('cesar' in item.lower()) or ('ceasar' in item.lower()):
        return "Caesar Salad"
    elif 'cheesecake' in item.lower():
        return "Cheesecake"
    elif 'donut' in item.lower():
        return "Donuts"
    else:
        return item


def get_day_of_week(date_str):
    """Get day of week from date string."""
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.weekday()
    except ValueError:
        return "Invalid date format. Please use 'YYYY-MM-DD'."


def get_month(date_str):
    """Get month from date string."""
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.month
    except ValueError:
        return "Invalid date format. Please use 'YYYY-MM-DD'."


def perform_regression(group):
    """Perform linear regression for each group."""
    X = group.dropna()['Total']
    y = group.dropna()['# of Orders']
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()
    return model.params


def perform_regression2(group):
    """Get residuals from regression for each group."""
    X = group.dropna()['Total']
    y = group.dropna()['# of Orders']
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()
    return model.resid


def export_to_excel(df, output_filepath):
    """Export dataframe to formatted Excel file."""
    dataframes = [df]
    sheet_titles = ['Kitchen Pars - Weekly Report']

    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        for i, df in enumerate(dataframes):
            sheet_name = sheet_titles[i]
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Load workbook to apply formatting
    wb = load_workbook(output_filepath)
    pink_fill = PatternFill(start_color="E49EDD", end_color="E49EDD", fill_type="solid")
    green_fill = PatternFill(start_color="B5E6A2", end_color="B5E6A2", fill_type="solid")

    # Define currency format style
    if "currency" not in wb.named_styles:
        currency_format = NamedStyle(name="currency")
        currency_format.number_format = "$#,##0.00"
        wb.add_named_style(currency_format)
    if "percent" not in wb.named_styles:
        percentage_format = NamedStyle(name="percent")
        percentage_format.number_format = "##0.00%"
        wb.add_named_style(percentage_format)

    for i, df in enumerate(dataframes):
        sheet = wb[sheet_titles[i]]

        # Insert title row
        sheet.insert_rows(1)
        sheet["A1"] = "Weekly Orders by Item (Kitchen)"
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=df.shape[1])
        sheet["A1"].font = Font(bold=True, size=14)
        sheet["A1"].alignment = Alignment(horizontal="center", vertical="center")

        # Enable text wrapping for all cells in row 2
        for cell in sheet[2]:
            cell.alignment = Alignment(wrap_text=True)

        # Adjust existing formatting
        header_row = sheet[2]

        column_indices = {}
        for col_idx, cell in enumerate(header_row, start=1):
            if "Adjusted Weekly Estimate" in cell.value:
                column_indices[col_idx] = green_fill
            elif "Recent Week: Total Orders" in cell.value:
                column_indices[col_idx] = pink_fill

        for col_idx, fill in column_indices.items():
            for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    cell.fill = fill

        # Auto-adjust column widths
        for col in sheet.columns:
            max_length = 0
            col_letter = col[0].column
            if isinstance(col_letter, int):
                col_letter = sheet.cell(row=1, column=col_letter).coordinate[:1]
            for cell in col:
                try:
                    if cell.value and not cell.merged_cell:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    max_length = 15
            if col_letter:
                sheet.column_dimensions[col_letter].width = max_length + 2
        wb.save(output_filepath)




def generate_kitchen_pars(
    sales_df: pd.DataFrame = None,
    orders_df: pd.DataFrame = None,
    summary_csv: str = "summary_transposed.csv",
    recent_week_ref_date: str = None,
    output_path: str = "KitchenPars.xlsx",
    data_dir: str = ".",
):
    """Generate a Kitchen Pars report, callable from main.py or standalone.

    Parameters
    ----------
    sales_df : DataFrame or None
        Pre-loaded sales data. If None, reads from data_dir.
    orders_df : DataFrame or None
        Pre-loaded orders data (unused directly, kept for interface consistency).
    summary_csv : str
        Path to the transposed summary CSV.
    recent_week_ref_date : str
        Reference date for checkdt (YYYY-MM-DD). The "recent week" is the
        7 days after this date.
    output_path : str
        Where to write the Excel output.
    data_dir : str
        Directory for CSV files (used only if sales_df is None).
    """
    import os

    pd.options.mode.chained_assignment = None

    # Load data if not provided
    if sales_df is None:
        sales = pd.read_csv(os.path.join(data_dir, "sales.csv"), low_memory=False)
    else:
        sales = sales_df.copy()

    summ = pd.read_csv(os.path.join(data_dir, summary_csv) if not os.path.isabs(summary_csv) else summary_csv)
    temp2 = list(summ.columns.copy())
    temp2[0] = "Date"
    summ.columns = temp2
    summ["Date"] = summ["Date"].astype(str)
    total = summ[["Date", "Total"]]

    # Ensure Date is string (the pipeline stores datetime.date objects)
    sales["Date"] = sales["Date"].astype(str)
    total["Date"] = total["Date"].astype(str)

    # Build checkdt for this week
    ref_date = datetime.datetime.strptime(recent_week_ref_date, "%Y-%m-%d")

    def checkdt(date1):
        d = datetime.datetime.strptime(date1, "%Y-%m-%d")
        diff = (d - ref_date).days
        return 0 < diff <= 7

    # Process sales
    sales["Menu2"] = [menu(x, y) for x, y in zip(sales["Menu"], sales["Menu Item"])]
    sales["Menu Item2"] = [item2(x).lower() for x in sales["Menu Item"]]

    filtered_sales = sales.loc[
        ((sales["Menu2"] == "Magical Dining") | (sales["Menu2"] == "A La Carte Menu"))
        & ((sales["Date"].str.contains("2025")) | (sales["Date"].str.contains("2026")))
    ]
    unique_menu_items = filtered_sales["Menu Item2"].unique()
    filtered_sales_in_set = sales[sales["Menu Item2"].isin(unique_menu_items)]

    date_counts = (
        filtered_sales_in_set.groupby("Menu Item2")["Date"]
        .nunique()
        .reindex(unique_menu_items, fill_value=0)
    )
    mySet = {x for x, y in date_counts.to_dict().items() if y > 5}

    filtered_sales_in_set2 = filtered_sales_in_set.loc[
        (filtered_sales_in_set["Menu Item2"].isin(mySet))
        & (filtered_sales_in_set["Menu2"].isin(["A La Carte Menu", "Magical Dining"]))
    ]
    dates_available = filtered_sales_in_set2.groupby(["Menu Item2", "Date"])["Qty"].sum()
    da = pd.DataFrame(dates_available).reset_index().rename(columns={"Qty": "# of Orders"})
    gb = total.merge(da, how="right", on="Date").groupby("Menu Item2")

    regression_results = gb.apply(perform_regression)
    resid = gb.apply(perform_regression2)
    rs = resid.groupby("Menu Item2").var()

    total2 = total.loc[
        (total["Total"] > 0)
        & (total["Date"].str.contains("2024") | total["Date"].str.contains("2025"))
    ].copy()
    total2["DOW"] = [get_day_of_week(x) for x in total2["Date"]]
    total2["DayCat"] = ["FS" if x in [4, 5] else "WK" for x in total2["DOW"]]
    gb3 = total2[["DayCat", "Total"]].groupby(["DayCat"])
    df3 = pd.DataFrame(gb3.mean())
    fs_avg = float(df3.transpose()["FS"].iloc[0])
    wk_avg = float(df3.transpose()["WK"].iloc[0])

    est0 = pd.DataFrame(regression_results).reset_index()
    est0["FS"] = [b + m * fs_avg for m, b in zip(est0["Total"], est0["const"])]
    est0["WK"] = [b + m * wk_avg for m, b in zip(est0["Total"], est0["const"])]
    est1 = est0.merge(pd.DataFrame(rs), on="Menu Item2")

    x = da.groupby("Menu Item2").mean("# of Orders").reset_index().rename(columns={"# of Orders": "Mean"}).merge(
        est1[["Menu Item2", "FS", "WK"]], on="Menu Item2"
    )
    x = da.groupby("Menu Item2").median("# of Orders").reset_index().rename(columns={"# of Orders": "Median"}).merge(
        x, on="Menu Item2"
    )
    x2 = x.rename(columns={
        "Median": "Long-Term Median",
        "Mean": "Long-Term Average",
        "FS": "Long-Term Adjusted Average: Friday/Saturday",
        "WK": "Long-Term Adjusted Average: Weeknight",
    })
    x2["Adjusted Weekly Estimate"] = 2 * x2["Long-Term Adjusted Average: Friday/Saturday"] + 4 * x2["Long-Term Adjusted Average: Weeknight"]
    out = x2.round(1)

    # Recent week
    fs_wk = filtered_sales_in_set.loc[
        (filtered_sales_in_set["Menu Item2"].isin(mySet))
        & (filtered_sales_in_set["Menu2"].isin(["A La Carte Menu", "Magical Dining"]))
        & (filtered_sales_in_set["Date"].apply(checkdt))
    ]
    gb_wk = fs_wk.groupby(["Menu Item2", "Date"]).size()
    this_week = pd.DataFrame(gb_wk).reset_index().rename(columns={0: "# of Orders"})
    this_week["DOW"] = [get_day_of_week(x) for x in this_week["Date"]]
    this_week["DayCat"] = ["FS" if x in [4, 5] else "WK" for x in this_week["DOW"]]

    this_week2 = (
        this_week[["Menu Item2", "DayCat", "# of Orders"]]
        .groupby(["Menu Item2", "DayCat"])
        .mean()
        .unstack("DayCat")
        .reset_index()
    )
    this_week2.columns = ["Menu Item2", "Recent Week: Fri/Sat Average", "Recent Week: Weeknight Average"]

    twtot = (
        this_week[["Menu Item2", "# of Orders"]]
        .groupby("Menu Item2")
        .sum()
        .reset_index()
        .rename(columns={"# of Orders": "Recent Week: Total Orders"})
    )
    out2 = out.merge(this_week2, on="Menu Item2").merge(twtot, on="Menu Item2").rename(
        columns={"Menu Item2": "Menu Item"}
    ).round(1)

    export_to_excel(out2, output_path)
    print(f"  Kitchen Pars report: {output_path}")


def main():
    """Main function to generate weekly orders report."""
    parser = argparse.ArgumentParser(description='Generate Weekly Orders Report')
    parser.add_argument('--data-dir', required=True, help='Directory containing CSV files')
    parser.add_argument('--sales-file', default='sales_20JUL2026.csv', help='Sales CSV filename')
    parser.add_argument('--orders-file', default='orders_20JUL2026.csv', help='Orders CSV filename')
    parser.add_argument('--summary-file', default='summary2_20JUL2026.csv', help='Summary CSV filename')
    parser.add_argument('--recent-week-end', required=True, help='Recent week end date (YYYY-MM-DD)')
    parser.add_argument('--output-path', required=True, help='Output Excel file path')

    args = parser.parse_args()

    # Set pandas options
    pd.options.mode.chained_assignment = None
    pd.set_option('display.max_columns', None)

    # Read data files
    sales_path = f"{args.data_dir}/{args.sales_file}"
    orders_path = f"{args.data_dir}/{args.orders_file}"
    summary_path = f"{args.data_dir}/{args.summary_file}"

    sales = pd.read_csv(sales_path, low_memory=False)
    sales['Date'] = sales['Date'].astype(str)
    orders = pd.read_csv(orders_path)
    summ = pd.read_csv(summary_path)

    # Clean up summary columns
    temp = summ.columns.copy()
    temp2 = list(temp).copy()
    temp2[0] = 'Date'
    summ.columns = temp2
    total = summ[['Date', 'Total']]

    # Process sales data
    sales['Menu2'] = [menu(x, y) for x, y in zip(sales['Menu'], sales['Menu Item'])]
    sales['Menu Item2'] = [item2(x).lower() for x in sales['Menu Item']]

    # Filter sales data
    filtered_sales = sales.loc[((sales['Menu2'] == 'Magical Dining') | (sales['Menu2'] == 'A La Carte Menu')) & 
                              ((sales['Date'].str.contains('2025')) | (sales['Date'].str.contains('2026')))]

    unique_menu_items = filtered_sales['Menu Item2'].unique()
    filtered_sales_in_set = sales[sales['Menu Item2'].isin(unique_menu_items)]

    # Group by menu item and count unique dates
    date_counts = (
        filtered_sales_in_set.groupby('Menu Item2')['Date']
        .nunique()
        .reindex(unique_menu_items, fill_value=0)
    )
    mydict = date_counts.to_dict()

    # Filter items with more than 5 unique dates
    mySet = {x for x, y in mydict.items() if y > 5}

    # Further filter sales data
    filtered_sales_in_set2 = filtered_sales_in_set.loc[
        (filtered_sales_in_set['Menu Item2'].isin(mySet)) & 
        (filtered_sales_in_set['Menu2'].isin(['A La Carte Menu', 'Magical Dining']))
    ]

    dates_available = (
        filtered_sales_in_set2.groupby(['Menu Item2', 'Date'])['Qty'].sum()
    )

    da = pd.DataFrame(dates_available).reset_index().rename(columns={'Qty': '# of Orders'})
    gb = total.merge(da, how='right', on='Date').groupby('Menu Item2')

    # Perform regression analysis
    regression_results = gb.apply(perform_regression)
    resid = gb.apply(perform_regression2)
    rs = resid.groupby('Menu Item2').var()

    # Calculate day categories and averages
    total2 = total.loc[(total['Total'] > 0) & (total['Date'].str.contains('2024') | total['Date'].str.contains('2025'))].copy()
    total2['DOW'] = [get_day_of_week(x) for x in total2['Date']]
    total2['MON'] = [get_month(x) for x in total2['Date']]
    total2['DayCat'] = ['FS' if x in [4, 5] else 'WK' for x in total2['DOW']]

    gb3 = total2[['DayCat', 'Total']].groupby(['DayCat'])
    df3 = pd.DataFrame(gb3.mean())
    fs = float(df3.transpose()['FS'].iloc[0])
    wk = float(df3.transpose()['WK'].iloc[0])

    # Calculate estimates
    est0 = pd.DataFrame(regression_results).reset_index()
    est0['FS'] = [b + m * fs for m, b in zip(est0['Total'], est0['const'])]
    est0['WK'] = [b + m * wk for m, b in zip(est0['Total'], est0['const'])]
    est1 = est0.merge(pd.DataFrame(rs), on='Menu Item2')

    # Merge with averages and medians
    x = da.groupby('Menu Item2').mean('# of Orders').reset_index().rename(columns={'# of Orders': 'Mean'}).merge(est1[['Menu Item2', 'FS', 'WK']], on='Menu Item2')
    x = da.groupby('Menu Item2').median('# of Orders').reset_index().rename(columns={'# of Orders': 'Median'}).merge(x, on='Menu Item2')

    x2 = x.rename(columns={
        'Median': 'Long-Term Median',
        'Mean': 'Long-Term Average',
        'FS': 'Long-Term Adjusted Average: Friday/Saturday',
        'WK': 'Long-Term Adjusted Average: Weeknight'
    })
    x2['Adjusted Weekly Estimate'] = 2 * x2['Long-Term Adjusted Average: Friday/Saturday'] + 4 * x2['Long-Term Adjusted Average: Weeknight']
    out = x2.round(1)

    # Define checkdt function with parameterized date
    def checkdt(date1):
        date1 = datetime.datetime.strptime(date1, '%Y-%m-%d')
        date2 = datetime.datetime.strptime(args.recent_week_end, '%Y-%m-%d')
        difference = (date1 - date2).days
        return 0 < difference <= 7

    # Process recent week data
    fs_wk = filtered_sales_in_set.loc[
        (filtered_sales_in_set['Menu Item2'].isin(mySet)) & 
        (filtered_sales_in_set['Menu2'].isin(['A La Carte Menu', 'Magical Dining'])) &
        (filtered_sales_in_set['Date'].apply(checkdt))
    ]

    gb_wk = fs_wk.groupby(['Menu Item2', 'Date']).size()
    this_week = pd.DataFrame(gb_wk).reset_index().rename(columns={0: '# of Orders'})

    this_week['DOW'] = [get_day_of_week(x) for x in this_week['Date']]
    this_week['DayCat'] = ['FS' if x in [4, 5] else 'WK' for x in this_week['DOW']]

    this_week2 = this_week[['Menu Item2', 'DayCat', '# of Orders']].groupby(['Menu Item2', 'DayCat']).mean().unstack('DayCat').reset_index()
    this_week2.columns = ['Menu Item2', 'Recent Week: Fri/Sat Average', 'Recent Week: Weeknight Average']

    twtot = this_week[['Menu Item2', '# of Orders']].groupby('Menu Item2').sum().reset_index().rename(columns={'# of Orders': 'Recent Week: Total Orders'})
    out2 = out.merge(this_week2, on='Menu Item2').merge(twtot, on='Menu Item2').rename(columns={"Menu Item2": "Menu Item"}).round(1)

    # Export to Excel
    export_to_excel(out2, args.output_path)
    print(f"Report generated successfully: {args.output_path}")


if __name__ == "__main__":
    main()
