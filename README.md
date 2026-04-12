# CE/CZ4123/SC4023 Big Data Management — Semester Group Project

## Overview
This program implements a **column-store** data management system to query HDB resale flat transaction records in Singapore (2015–2025). It finds all valid `(x, y)` pairs where the minimum price per square meter of qualifying flats does not exceed **4725 SGD/m²**.

---

## Query Parameters (Matriculation Number: U2221398J)

| Parameter | Value |
|---|---|
| Target Year | 2018 |
| Commencing Month | September (09) |
| Towns | BUKIT PANJANG, CLEMENTI, CHOA CHU KANG, WOODLANDS, YISHUN |
| x range | 1 to 8 (months) |
| y range | 80 to 150 (square meters) |
| Price threshold | ≤ 4725 SGD/m² |

---

## Requirements

- Python 3.x (no external libraries required)
- Input file: `ResalePricesSingapore.csv`

---

## File Structure

```
project/
├── source/
│   └── column_store.py        # Main program
├── ScanResult_U2221398J.csv   # Output file (generated after running)
├── Report.pdf                 # Project report
└── README.md                  # This file
```

---

## How to Run

**Step 1:** Place both files in the same folder:
```
your_folder/
├── column_store.py
└── ResalePricesSingapore.csv
```

**Step 2:** Open a terminal and navigate to the folder:
```bash
# Windows
cd C:\Users\YourName\your_folder

# Mac/Linux
cd /Users/YourName/your_folder
```

**Step 3:** Run the program:
```bash
python3 column_store.py
```

**Step 4:** The output file `ScanResult_U2221398J.csv` will be generated in the same folder.

---

## Expected Output

```
=== Big Data Management - Column Store Query ===
Matric     : U2221398J
Target Year: 2018
Start Month: 09
Towns      : BUKIT PANJANG, CHOA CHU KANG, CLEMENTI, WOODLANDS, YISHUN

Loaded 259237 records into column store.
Output written to ScanResult_U2221398J.csv (568 valid (x,y) pairs found).
Done.
```

---

## Output Format

The output CSV `ScanResult_U2221398J.csv` contains the following columns:

| Column | Description |
|---|---|
| (x, y) | The query pair; ordered by increasing x, then increasing y |
| Year | Year of the matched record (YYYY) |
| Month | Month of the matched record (MM) |
| Town | Town of the matched HDB flat |
| Block | Block number of the matched HDB flat |
| Floor_Area | Floor area in square meters |
| Flat_Model | Flat model (e.g. Standard, Improved, Apartment) |
| Lease_Commence_Date | Year the flat lease commenced |
| Price_Per_Square_Meter | Minimum price per sqm, rounded to nearest integer |

---

## How It Works

1. **Column Store Loading:** All records from the CSV are loaded into a Python dictionary where each key is a column name and each value is a list of all entries in that column. No external libraries (e.g. pandas) are used.

2. **Date Parsing:** The input date format `Mon-YY` (e.g. `Sep-18`) is parsed into separate integer `year` and `month` values using a custom parser.

3. **Query Execution:** For each `(x, y)` pair, the program:
   - Computes the valid `(year, month)` set for the given `x`
   - Scans all records applying three filters: time range, town, and floor area ≥ y
   - Tracks the record with the minimum `resale_price / floor_area`
   - Outputs the record only if the minimum price/sqm ≤ 4725

4. **Output Writing:** Results are written to CSV in the required format using Python's built-in `csv.writer`.
