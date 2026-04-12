"""
CE/CZ4123/SC4023 Big Data Management - Semester Group Project
Column-Store Program for HDB Resale Flat Query

Matriculation Number: U2221398J
Query Parameters:
    - Target Year: 2018
    - Commencing Month: 9 (September)
    - Towns: BUKIT PANJANG, CLEMENTI, CHOA CHU KANG, WOODLANDS, YISHUN
    - x range: 1 to 8 (months)
    - y range: 80 to 150 (square meters)
    - Valid threshold: min price/sqm <= 4725
"""

import csv
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION (derived from matric U2221398J)
# ─────────────────────────────────────────────

MATRIC_NUM      = "U2221398J"
INPUT_FILE      = "ResalePricesSingapore.csv"
OUTPUT_FILE     = f"ScanResult_{MATRIC_NUM}.csv"

TARGET_YEAR     = 2018
START_MONTH     = 9          # September
TOWNS           = {"BUKIT PANJANG", "CLEMENTI", "CHOA CHU KANG", "WOODLANDS", "YISHUN"}
X_RANGE         = range(1, 9)    # 1 to 8 inclusive
Y_RANGE         = range(80, 151) # 80 to 150 inclusive
PRICE_THRESHOLD = 4725

# Month abbreviation -> integer mapping (handles "Jan-15" style dates)
MONTH_MAP = {
    "Jan": 1,  "Feb": 2,  "Mar": 3,  "Apr": 4,
    "May": 5,  "Jun": 6,  "Jul": 7,  "Aug": 8,
    "Sep": 9,  "Oct": 10, "Nov": 11, "Dec": 12
}


# ─────────────────────────────────────────────
# STEP 1: LOAD DATA INTO COLUMN STORE
# ─────────────────────────────────────────────
def parse_date(date_str):
    date_str = date_str.strip()
    parts = date_str.split("-")
    if parts[0] in MONTH_MAP:
        month = MONTH_MAP[parts[0]]
        year  = 2000 + int(parts[1])
        return year, month
    else:
        return int(parts[0]), int(parts[1])


def load_column_store(filepath):
    """
    Reads the CSV file and stores each attribute as a separate list (column).
    This is the column-oriented (column-store) approach:
    data is organised by attribute rather than by row.
    Returns a dictionary mapping column name -> list of values.
    """
    col_year           = []
    col_month          = []
    col_town           = []
    col_block          = []
    col_floor_area     = []
    col_flat_model     = []
    col_lease_commence = []
    col_resale_price   = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            year, month = parse_date(row["month"])

            col_year.append(year)
            col_month.append(month)
            col_town.append(row["town"].strip().upper())
            col_block.append(row["block"].strip())
            col_floor_area.append(float(row["floor_area_sqm"].strip()))
            col_flat_model.append(row["flat_model"].strip())
            col_lease_commence.append(row["lease_commence_date"].strip())
            col_resale_price.append(float(row["resale_price"].strip()))

    column_store = {
        "year"           : col_year,
        "month"          : col_month,
        "town"           : col_town,
        "block"          : col_block,
        "floor_area"     : col_floor_area,
        "flat_model"     : col_flat_model,
        "lease_commence" : col_lease_commence,
        "resale_price"   : col_resale_price,
    }

    print(f"Loaded {len(col_year)} records into column store.")
    return column_store


# ─────────────────────────────────────────────
# STEP 2: COMPUTE MONTH RANGE GIVEN x
# ─────────────────────────────────────────────

def get_month_range(x):
    """
    Given x (number of months), returns a set of (year, month) tuples
    starting from START_MONTH of TARGET_YEAR for x consecutive months.
    Example: x=3, start=Sep 2018 -> {(2018,9), (2018,10), (2018,11)}
    """
    months = set()
    year  = TARGET_YEAR
    month = START_MONTH
    for _ in range(x):
        months.add((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


# ─────────────────────────────────────────────
# STEP 3: SCAN COLUMN STORE FOR A GIVEN (x, y)
# ─────────────────────────────────────────────

def scan(column_store, valid_months_set, y):
    """
    Scans all columns to find rows matching:
      - (year, month) in valid_months_set
      - town in TOWNS
      - floor_area >= y

    Returns the index of the row with the minimum price/sqm,
    and the minimum price/sqm value. Returns (None, None) if no match.
    """
    col_year         = column_store["year"]
    col_month        = column_store["month"]
    col_town         = column_store["town"]
    col_floor_area   = column_store["floor_area"]
    col_resale_price = column_store["resale_price"]

    n = len(col_year)

    best_idx       = None
    best_price_sqm = None

    for i in range(n):
        # Filter 1: time range
        if (col_year[i], col_month[i]) not in valid_months_set:
            continue
        # Filter 2: town
        if col_town[i] not in TOWNS:
            continue
        # Filter 3: floor area
        if col_floor_area[i] < y:
            continue

        # Compute price per square meter
        price_sqm = col_resale_price[i] / col_floor_area[i]

        # Track minimum
        if best_price_sqm is None or price_sqm < best_price_sqm:
            best_price_sqm = price_sqm
            best_idx = i

    return best_idx, best_price_sqm


# ─────────────────────────────────────────────
# STEP 4: MAIN QUERY LOOP
# ─────────────────────────────────────────────

def run_queries(column_store):
    """
    Iterates over all (x, y) pairs in the required order:
    increasing x, then increasing y within the same x.
    Runs scan for each, collects valid results (min price/sqm <= PRICE_THRESHOLD).
    """
    results = []

    for x in X_RANGE:
        valid_months_set = get_month_range(x)

        for y in Y_RANGE:
            best_idx, best_price_sqm = scan(column_store, valid_months_set, y)

            # Skip if no qualifying record found
            if best_idx is None:
                continue

            # Skip if above price threshold
            if best_price_sqm > PRICE_THRESHOLD:
                continue

            # Round price per sqm to nearest integer
            rounded_price_sqm = round(best_price_sqm)

            results.append({
                "xy"         : f"({x}, {y})",
                "year"       : f"{column_store['year'][best_idx]:04d}",
                "month"      : f"{column_store['month'][best_idx]:02d}",
                "town"       : column_store["town"][best_idx],
                "block"      : column_store["block"][best_idx],
                "floor_area" : int(column_store["floor_area"][best_idx]),
                "flat_model" : column_store["flat_model"][best_idx],
                "lease"      : column_store["lease_commence"][best_idx],
                "price_sqm"  : rounded_price_sqm,
            })

    return results


# ─────────────────────────────────────────────
# STEP 5: WRITE OUTPUT CSV
# ─────────────────────────────────────────────

def write_output(results, filepath):
    """
    Writes the query results to the output CSV file.
    """
    with open(filepath, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "(x, y)", "Year", "Month", "Town", "Block",
            "Floor_Area", "Flat_Model", "Lease_Commence_Date",
            "Price_Per_Square_Meter"
        ])
        for r in results:
            writer.writerow([
                r["xy"], r["year"], r["month"], r["town"], r["block"],
                r["floor_area"], r["flat_model"], r["lease"], r["price_sqm"]
            ])

    print(f"Output written to {filepath} ({len(results)} valid (x,y) pairs found).")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Big Data Management - Column Store Query ===")
    print(f"Matric     : {MATRIC_NUM}")
    print(f"Target Year: {TARGET_YEAR}")
    print(f"Start Month: {START_MONTH:02d}")
    print(f"Towns      : {', '.join(sorted(TOWNS))}")
    print()

    column_store = load_column_store(INPUT_FILE)
    results      = run_queries(column_store)
    write_output(results, OUTPUT_FILE)

    print("Done.")