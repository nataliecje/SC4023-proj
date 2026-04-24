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

# ─────────────────────────────────────────────
# CONFIGURATION (derived from matric U2221398J)
# ─────────────────────────────────────────────

MATRIC_NUM      = "U2221398J"
INPUT_FILE      = "ResalePricesSingapore.csv"
X_RANGE         = range(1, 9)      # 1 to 8 inclusive
Y_RANGE         = range(80, 151)   # 80 to 150 inclusive
PRICE_THRESHOLD = 4725

# Month abbreviation -> integer mapping (handles "Jan-15" style dates)
MONTH_MAP = {
    "Jan": 1,  "Feb": 2,  "Mar": 3,  "Apr": 4,
    "May": 5,  "Jun": 6,  "Jul": 7,  "Aug": 8,
    "Sep": 9,  "Oct": 10, "Nov": 11, "Dec": 12
}

DIGIT_TO_TOWN = {
    "0": "BEDOK",
    "1": "BUKIT PANJANG",
    "2": "CLEMENTI",
    "3": "CHOA CHU KANG",
    "4": "HOUGANG",
    "5": "JURONG WEST",
    "6": "PASIR RIS",
    "7": "TAMPINES",
    "8": "WOODLANDS",
    "9": "YISHUN",
}


def derive_query_config(matric_num):
    """
    Derives the target year, commencing month, and town list directly from
    the chosen matriculation number.
    """
    digits = [ch for ch in matric_num if ch.isdigit()]
    if len(digits) < 2:
        raise ValueError("Matriculation number must contain at least two digits.")

    last_digit = int(digits[-1])
    target_year = 2020 + last_digit if last_digit <= 4 else 2010 + last_digit

    month_digit = digits[-2]
    start_month = 10 if month_digit == "0" else int(month_digit)
    if not 1 <= start_month <= 10:
        raise ValueError("Commencing month derived from matriculation number is invalid.")

    towns = {DIGIT_TO_TOWN[d] for d in digits}
    return target_year, start_month, towns


TARGET_YEAR, START_MONTH, TOWNS = derive_query_config(MATRIC_NUM)
OUTPUT_FILE = f"ScanResult_{MATRIC_NUM}.csv"


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
    Reads the CSV file and stores the entire input table as separate lists.
    This keeps the original columns available while still allowing the scan
    logic to touch only the columns needed for filtering and output.
    Returns a dictionary mapping column name -> list of values.
    """
    col_month_raw      = []
    col_town           = []
    col_flat_type      = []
    col_block          = []
    col_street_name    = []
    col_storey_range   = []
    col_floor_area     = []
    col_flat_model     = []
    col_lease_commence = []
    col_resale_price   = []
    col_year           = []
    col_month          = []

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            month_raw = row["month"].strip()
            year, month = parse_date(month_raw)

            col_month_raw.append(month_raw)
            col_town.append(row["town"].strip().upper())
            col_flat_type.append(row["flat_type"].strip())
            col_block.append(row["block"].strip())
            col_street_name.append(row["street_name"].strip())
            col_storey_range.append(row["storey_range"].strip())
            col_floor_area.append(float(row["floor_area_sqm"].strip()))
            col_flat_model.append(row["flat_model"].strip())
            col_lease_commence.append(row["lease_commence_date"].strip())
            col_resale_price.append(float(row["resale_price"].strip()))
            col_year.append(year)
            col_month.append(month)

    column_store = {
        "month_raw"      : col_month_raw,
        "town"           : col_town,
        "flat_type"      : col_flat_type,
        "block"          : col_block,
        "street_name"    : col_street_name,
        "storey_range"   : col_storey_range,
        "floor_area"     : col_floor_area,
        "flat_model"     : col_flat_model,
        "lease_commence" : col_lease_commence,
        "resale_price"   : col_resale_price,
        "year"           : col_year,
        "month"          : col_month,
    }

    print(f"Loaded {len(col_year)} records into column store.")
    return column_store


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
