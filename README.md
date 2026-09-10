# Restaurant

A data pipeline for a restaurant that merges two point-of-sale systems (Toast and Tock), produces daily and bi-weekly revenue summaries, and exports formatted Excel reports. Built to automate the weekly reporting workflow that was previously done by hand.

## What it does

- **Extracts** monthly Toast sales CSVs, quarterly Toast order CSVs, Tock reservation exports, and manually entered cover counts
- **Transforms** the data to allow for ease of analysis
- **Uploads** raw and processed data to Google BigQuery for cloud storage and querying
- **Summarises** revenue by day, breaking it down by source (Toast vs Tock), category (food, beverage, retail, service charge), and dining area
- **Generates** bi-weekly Excel reports with week-over-week and year-over-year comparisons
- **Produces** weekly kitchen prep estimates (Kitchen Pars) using OLS regression of item order counts against total daily revenue

## Project structure

```
restaurant/
├── config_template.py   # Example configuration (copy to config.py and fill in)
├── config.py            # Real configuration (gitignored)
├── utils.py             # Date helpers, reverse-lookup utilities
├── data_loaders.py      # CSV readers for Toast and Tock
├── data_pipeline.py     # Merge, clean, and classify all data
├── summaries.py         # Daily revenue breakdowns by source and category
├── reports.py           # Bi-weekly report generation and Excel formatting
├── weekly_orders.py     # Kitchen Pars regression and Excel export
├── analysis.py          # Ad-hoc analytics: covers, day-of-week stats
├── upload_raw.py        # BigQuery upload for raw and processed data
└── main.py              # CLI entry point
```

## Setup

### Prerequisites

- Python 3.12+
- A Toast POS account with CSV export access
- A Tock reservation export (if applicable)
- A Google Cloud project with BigQuery enabled (optional, for cloud storage)

### Installation

```bash
git clone https://github.com/JacobSpear/restaurant.git
cd restaurant
pip install -e .
```

### Configuration

Copy the template and fill in your restaurant's real values:

```bash
cp config_template.py config.py
```

`config.py` contains menu item sets, experience category mappings, table lists, and file path references specific to your restaurant. See `config_template.py` for the expected structure and types.

### Data directory

Place your CSV files in a single directory:

```
sales_data/
├── restaurant/   # this package
├── toast_01_2023.csv          # monthly Toast sales
├── toast_02_2023.csv
├── ...
├── ToastOrdersQ1_2023.csv     # quarterly Toast orders
├── ...
├── tock_daily_details.csv     # Tock reservation export
└── covers.csv                 # manual cover counts (date, guest_count)
```

## Usage

### Full pipeline

Load all data, export unified CSVs, compute summaries, and generate the bi-weekly report:

```bash
python -m restaurant.main --data-dir ./sales_data --biweekly-start 2026-07-06 --summary-end 2026-07-20
```

### Full pipeline + BigQuery upload

```bash
python -m restaurant.main --data-dir ./sales_data --biweekly-start 2026-07-06 --upload
```

### Reports only

Skip the data rebuild and generate reports from existing `sales.csv` and `orders.csv`:

```bash
python -m restaurant.main --data-dir ./sales_data --biweekly-start 2026-07-06 --report-only
```

### Upload raw data to BigQuery

```bash
python upload_raw.py --data-dir ./sales_data --all
```

### Output

Reports are written to a dated folder:

```
Weekly_Reports/
  2026-07-24/
    BiWeeklySummary_19JUL2026.xlsx
    KitchenPars06JUL2026-13JUL2026.xlsx
    KitchenPars14JUL2026-21JUL2026.xlsx
```

## Pipeline overview

```
Toast CSVs ──→ data_loaders.py ──→ data_pipeline.py ──→ main.py ──→ summaries.py ──→ reports.py
Tock CSV   ──→ data_loaders.py ──↗                         │
Covers CSV ────────────────────────────────────────────────↗│
                                                            ↓
                                                      sales.csv    ──→ BigQuery
                                                      orders.csv   ──→ BigQuery
                                                      summary.csv  ──→ BigQuery
                                                      Excel reports
```

## Technical notes

- **Date handling:** The pipeline stores dates as `datetime.date` objects internally. Modules that need string dates (e.g., `weekly_orders.py` for `.str.contains()` filtering) convert explicitly at their entry points.
- **Discount allocation:** Tock comps are distributed across line items within an order using a sequential allocation algorithm. The sort order of items within an order affects which specific items absorb the discount, though order-level totals are unaffected.
- **Kitchen Pars:** Item-level weekly prep estimates are computed by regressing historical order counts against total daily revenue (OLS), then applying the model at typical Friday/Saturday and weeknight revenue levels.
- **BigQuery integration:** Raw source data is archived in partitioned BigQuery tables. Processed output tables are replaced on each pipeline run. Partition-safe uploads allow re-uploading the current month/quarter without affecting closed periods.

## Dependencies

- pandas, numpy
- openpyxl (Excel export)
- statsmodels (OLS regression)
- matplotlib, seaborn, scipy (charts and statistics)
- scikit-learn (mixed-effects models)
- google-cloud-bigquery, pandas-gbq, pyarrow (BigQuery integration)

## License

Private — not licensed for redistribution.
