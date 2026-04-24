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
from collections import defaultdict

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
    month_town_index   = defaultdict(list)

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            month_raw = row["month"].strip()
            year, month = parse_date(month_raw)
            town = row["town"].strip().upper()
            row_idx = len(col_year)

            col_month_raw.append(month_raw)
            col_town.append(town)
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
            month_town_index[(year, month, town)].append(row_idx)

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
        "month_town_index": month_town_index,
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


def get_candidate_indices(month_town_index, valid_months_set):
    """
    Uses the month/town index to gather only the row indices that can match
    a given x-month query window.
    """
    candidate_indices = []
    for year, month in sorted(valid_months_set):
        for town in sorted(TOWNS):
            candidate_indices.extend(month_town_index.get((year, month, town), []))
    return candidate_indices


def build_result(column_store, x, y, best_idx, rounded_price_sqm):
    """
    Formats one output row using the matched record index.
    """
    return {
        "xy"         : f"({x}, {y})",
        "year"       : f"{column_store['year'][best_idx]:04d}",
        "month"      : f"{column_store['month'][best_idx]:02d}",
        "town"       : column_store["town"][best_idx],
        "block"      : column_store["block"][best_idx],
        "floor_area" : int(column_store["floor_area"][best_idx]),
        "flat_model" : column_store["flat_model"][best_idx],
        "lease"      : column_store["lease_commence"][best_idx],
        "price_sqm"  : rounded_price_sqm,
    }


def run_queries_for_x(column_store, x, candidate_indices):
    """
    Reuses the same candidate set across all y values for one x.
    Candidates are ordered by descending floor area so that, while y moves
    from 150 down to 80, newly eligible rows are added only once.
    """
    col_floor_area   = column_store["floor_area"]
    col_resale_price = column_store["resale_price"]
    sorted_candidates = sorted(
        candidate_indices,
        key=lambda idx: (-col_floor_area[idx], idx),
    )

    best_idx = None
    best_key = None
    next_candidate = 0
    results_by_y = {}

    for y in reversed(Y_RANGE):
        while (
            next_candidate < len(sorted_candidates)
            and col_floor_area[sorted_candidates[next_candidate]] >= y
        ):
            idx = sorted_candidates[next_candidate]
            price_sqm = col_resale_price[idx] / col_floor_area[idx]
            candidate_key = (price_sqm, idx)

            # Tie-break by original row index to preserve the old output.
            if best_key is None or candidate_key < best_key:
                best_key = candidate_key
                best_idx = idx

            next_candidate += 1

        if best_idx is None:
            continue
        if best_key[0] > PRICE_THRESHOLD:
            continue

        results_by_y[y] = build_result(
            column_store,
            x,
            y,
            best_idx,
            round(best_key[0]),
        )

    return [results_by_y[y] for y in Y_RANGE if y in results_by_y]


def run_queries(column_store):
    """
    Iterates over all (x, y) pairs in the required order:
    increasing x, then increasing y within the same x.
    For each x, it first gathers candidate rows via the month/town index,
    then reuses that candidate set across all y values.
    """
    results = []
    month_town_index = column_store["month_town_index"]

    for x in X_RANGE:
        valid_months_set = get_month_range(x)
        candidate_indices = get_candidate_indices(month_town_index, valid_months_set)
        results.extend(run_queries_for_x(column_store, x, candidate_indices))

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
