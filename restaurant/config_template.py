
# --- Dining area configuration ---

DINING_AREA_MAIN = "Main Dining"
DINING_AREA_BAR = "Bar"
DINING_AREA_NAMES = ["Whole Restaurant", "Main Dining", "Bar", "Patio"]
PATIO_AREA_NAMES = {"Patio", "Garden", "Terrace"}
OUTDOOR_AREA_LABEL = "Patio/Garden/Terrace"

# --- Tasting menu detection ---

TASTING_MENU_KEYWORDS = ["Tasting", "Chef"]
WALKIN_TASTING_ITEMS = {"Chef Tasting Menu", "Weekend Tasting Special"}
TASTING_VS_ALC_MENUS = ["Chef Tasting Menu", "A La Carte Menu"]
BEV_CATEGORIES = [
    "Bottled Beer", "Draft Beer", "Beer", "Liquor", "NA Beverage", "Wine",
]

# --- Kitchen pars item normalization ---

ITEM_NORMALIZATION = {
    "Grilled Fish": ["Grilled Fish", "Pan-Seared Fish", "Catch of the Day"],
    "House Salad": ["House Salad", "Garden Salad", "Side Salad"],
}

ITEM_NORMALIZATION_SUBSTRING = {
    "Burger": "burger",
    "Pasta": "pasta",
    "Steak": "steak",
}

WACKY_TOAST_SUBSTRINGS = ["special", "chef"]
WACKY_TOAST_EXCLUDE = ["salad"]
