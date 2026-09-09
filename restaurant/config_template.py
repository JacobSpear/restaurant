"""
Configuration constants for the restaurant data pipeline.

Copy this file to ``config.py`` and replace the placeholder values
with your restaurant's actual menu items, experience names, and
file references.

    cp config_template.py config.py
"""

# ---------------------------------------------------------------------------
# Tock experience categories
# ---------------------------------------------------------------------------

ALC_EXPERIENCES = {
    "A La Carte",
    "Bar Reservation",
    "Patio Lounge",
}

TASTING_EXPERIENCES = {
    "Chef's Tasting Menu",
    "Weekend Set Menu",
    "Holiday Dinner",
    "Wine Pairing Dinner",
    "Guest Chef Collaboration",
}

TASTING_PRECISE_EXPERIENCES = {
    "Chef's Tasting Menu",
    "Weekend Set Menu",
    "Holiday Dinner",
    "Wine Pairing Dinner",
    "Guest Chef Collaboration",
}

# ---------------------------------------------------------------------------
# Tock menu-item sets
# ---------------------------------------------------------------------------

TOGO_BOTTLES = {"Tock Bottle of House Spirit", "Tock Sommelier Wine Pack"}
MERCH = {"Tock Tote Bag", "Tock Gift Card"}
TASTING_BOTTLES = {"Tock Wine Bottle Upgrade"}
TASTING_PAIRINGS = {"Tock Wine Pairing", "Tock Spirit Pairing", "Tock NA Pairing"}
DESSERT_CAKE = {"Tock Birthday Cake Add-On", "Tock Dessert Upgrade"}
PACKAGED_FOOD = {"Tock Take-Home Item"}
RICE = {"Tock Extra Rice"}
OTHER_TOCK_FOOD = {"Tock Appetizer Add-On", "Tock Entree Add-On"}
EVENT_UPGRADE = {"Tock Special Event Upgrade"}

# ---------------------------------------------------------------------------
# Toast item-classification lookups
# ---------------------------------------------------------------------------

WINE_ITEMS = {"House Red BTG", "House White BTG", "Reserve Bottle", "Sparkling BTG", "Rose BTL"}
LIQUOR_ITEMS = {"House Cocktail", "Premium Spirit", "Digestif"}
BEER_ITEMS = {"Draft Lager", "Draft IPA", "Bottled Import"}
FOOD_ITEMS = {"Side Salad", "Extra Bread", "Kids Meal"}
NA_BEV_ITEMS = {"Sparkling Water", "Fresh Juice", "Mocktail"}
RETAIL_ITEMS = {"Branded Tote", "Hot Sauce Bottle", "Cookbook"}

# ---------------------------------------------------------------------------
# Menu and sales category dictionaries
# ---------------------------------------------------------------------------

MENU_DICT = {
    "Appetizers": {"Tock Appetizer Add-On"},
    "Entrees": {"Tock Entree Add-On"},
    "Drinks": {"Tock Wine Pairing", "Tock Spirit Pairing"},
}

SALES_CATEGORY_DICT = {
    "Food": {"Tock Appetizer Add-On", "Tock Entree Add-On"},
    "Beverage": {"Tock Wine Pairing"},
}

# ---------------------------------------------------------------------------
# Dining area and table configuration
# ---------------------------------------------------------------------------

PATIO_TABLES = {"P1", "P2", "P3", "P4", "P5"}

# ---------------------------------------------------------------------------
# Report row ordering
# ---------------------------------------------------------------------------

REPORT_ROWS = [
    "Tock Sales", "Tock Sales-Discounts", "Tock Food", "Tock Bev",
    "Tock Discounts", "Tock Service Charge",
    "Toast Net", "Toast Bev", "Toast NA", "Toast Liquor",
    "Toast Beer", "Toast Wine", "Toast Bar",
    "Toast Dining Room", "Toast No Dining Area",
    "Toast Service Charge", "Toast Retail",
    "Toast Tasting", "Toast Tasting Food", "Toast Food/Walk-In",
    "Total Tasting", "Total ALC", "Total Food", "Total Bev",
    "Total Service", "Total",
]

REPORT_ROW_ORDER = {row: i for i, row in enumerate(REPORT_ROWS)}

# ---------------------------------------------------------------------------
# File references
# ---------------------------------------------------------------------------

TOCK_FILE = "tock-daily-details.csv"
TOAST_MONTHS_START = "01_2023"
TOAST_MONTHS_COUNT = 43
TOAST_QUARTER_LIST = [
    "Q1_2023", "Q2_2023", "Q3_2023", "Q4_2023",
    "Q1_2024", "Q2_2024", "Q3_2024", "Q4_2024",
    "Q1_2025", "Q2_2025", "Q3_2025", "Q4_2025",
    "Q1_2026", "Q2_2026", "Q3_2026",
]

# ---------------------------------------------------------------------------
# BigQuery configuration
# ---------------------------------------------------------------------------

BQ_PROJECT = "your-gcloud-project-id"
BQ_DATASET = "your_dataset"
