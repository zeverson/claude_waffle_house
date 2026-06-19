# Data Dictionary — `waffle_houses.csv`

**Source file:** `waffle_houses.csv`
**Rows:** 2,006 location records (plus 1 header row)
**Columns:** 14
**Generated:** 2026-06-19
**Scope:** All records have `Country = US`, spanning 25 states. Coordinates fall within the continental US.

> ⚠️ This dictionary documents the data *as it actually is in the file*, including its quirks. Read the **Quality Checks** section before trusting any column for analysis.

---

## Column reference

| # | Column | Type | Description | Example | Notes / caveats |
|---|--------|------|-------------|---------|-----------------|
| 1 | **Store Code** | Integer (mostly) | Unique location identifier | `100` | Unique across all rows. **1 non-numeric value:** `WH_Museum` (the Waffle House Museum). Numeric codes range 4–3442; not contiguous. |
| 2 | **Business Name** | Text | Display name of the location | `Waffle House #100` | Unique. Pattern `Waffle House #<StoreCode>`; museum row is `Waffle House Museum #WH_Museum`. |
| 3 | **Address** | Text | Street address | `2842 PANOLA RD` | Mostly uppercase; museum row uses mixed case (`2719 East College Avenue`). |
| 4 | **City** | Text | City name | `LITHONIA` | 2,005 of 2,006 are ALL-CAPS; 1 mixed-case (`Decatur`, the museum). |
| 5 | **State** | Text (2-letter) | USPS state abbreviation | `GA` | 25 distinct values. No blanks. All valid US state codes. |
| 6 | **Postal Code** | Text (5-digit) | ZIP code | `30058` | All exactly 5 digits. **Keep as text** — leading zeros would be lost if parsed as a number. |
| 7 | **Country** | Text | Country code | `US` | Constant — every row is `US`. No analytic value. |
| 8 | **Latitude** | Float | Decimal latitude | `33.704706` | Range 25.10 → 41.78. All valid floats, all within plausible US bounds. |
| 9 | **Longitude** | Float | Decimal longitude | `-84.169849` | Range -112.34 → -75.34. All valid floats, all within plausible US bounds. |
| 10 | **Phone Number** | Text | Contact phone | `(770) 981-1914` | **Mixed formats** — see quality checks. 1,777 use `(NNN) NNN-NNNN`; 229 hold two numbers separated by `; `; museum uses `770-326-7086`. |
| 11 | **Website URL** | Text (URL) | Location page link | `https://locations.wafflehouse.com///lithonia-ga-100` | **All 2,006 contain a triple slash `///`** — a source formatting artifact, not a typo in this file. |
| 12 | **Operated By** | Text (categorical) | Operating entity | `WAFFLE HOUSE, INC` | 15 distinct values + 1 blank. Encodes operator type (see below). |
| 13 | **Online Order Link** | Text (URL) | Online ordering link | `https://order.wafflehouse.com/menu/waffle-house-100` | 2,003 follow the standard pattern; **3 blank**. |
| 14 | **Formatted Business Hours** | Text | Operating hours | `Monday - Sunday\| 24 hours` | 1,998 are 24-hour. Pipe-delimited `days\|hours`. **5 non-24h, 2 blank** (see below). |

---

## `Operated By` — operator type breakdown

The field combines the operating company with an implicit **operator type**, which is the most useful angle for analysis:

| Operator type | How to identify | Locations |
|---|---|---|
| **Corporate** | `WAFFLE HOUSE, INC` | 1,251 |
| **Subsidiary** | starts with `FULLY OWNED SUBSIDIARY:` (4 companies) | 627 |
| **Franchise** | starts with `FRANCHISE :` (10 companies) | 127 |
| **Unknown** | blank | 1 |

*Subsidiaries:* East Coast Waffles (212), Mid South Waffles (169), Midwest Waffles (143), Ozark Waffles (103).
*Franchises:* Rocky Top (37), Lookout (23), J. Thomas & Co. (19), Choo-Choo (18), Yogi Hill (12), M&M (6), Hilltop (5), Amarillo (4), Lehigh Valley (2), D. Love's (1).

> Note the inconsistent spacing: `FULLY OWNED SUBSIDIARY:` (no space before colon) vs. `FRANCHISE :` (space before colon). Match on prefix, not exact punctuation.

---

## Quality checks

### ✅ Missing values
| Column | Blank rows |
|---|---|
| Operated By | 1 |
| Online Order Link | 3 |
| Formatted Business Hours | 2 |
| *all other 11 columns* | 0 |

The blanks cluster on the **Waffle House Museum** row (`WH_Museum`), which is missing Operated By, Online Order Link, and Business Hours — it's a non-standard record (a museum, not an operating restaurant).

### ✅ Duplicates
- **Store Code:** no duplicates (all unique).
- **Business Name:** no duplicates.
- **Coordinate pairs:** no two locations share the same lat/long.
- **Fully identical rows:** none.

### ⚠️ Type / format problems
| Issue | Detail | Impact |
|---|---|---|
| **Non-numeric Store Code** | 1 row uses `WH_Museum` instead of an integer | Casting Store Code to int will fail on this row. Treat as text, or exclude the museum. |
| **Postal Code as number** | All 5-digit, but parsing as integer drops leading zeros | Keep as **string**. |
| **Phone format mixed** | 229 rows carry **two phone numbers** in one field (`... ; ...`); museum uses dashes not parens | Any phone parsing must handle multi-number and alternate formats. |

### ⚠️ Inconsistencies that could affect analysis
1. **City/Address casing:** the museum row is mixed-case while every other row is ALL-CAPS. Normalize case (e.g., upper or title) before grouping by City, or counts could split.
2. **Website URLs all contain `///`** — harmless for display but will break naive URL parsing/validation.
3. **`Country` is constant (`US`)** — carries no information; safe to ignore in analysis.
4. **The museum row (`WH_Museum`) is an outlier on multiple axes** (non-numeric ID, mixed case, blank operator/hours/order link, not a 24-hour restaurant). **Recommendation: exclude it from "operating restaurant" counts**, which leaves 2,005 restaurants.
5. **Business hours are nearly uniform** (1,998 = 24 hours). The 8 exceptions: 3 are `7:00am–9:00pm`, 2 are `Closed`, 1 is `7:00am–2:00pm`, 2 are blank. Worth a manual look before claiming "all Waffle Houses are 24/7."

---

## Recommended analysis-ready conventions
- **IDs as text:** Treat `Store Code` and `Postal Code` as strings, not numbers.
- **Restaurant count:** Use 2,005 (exclude the museum) for "how many Waffle Houses," 2,006 for "how many records."
- **Operator type:** Derive a clean `operator_type` ∈ {Corporate, Subsidiary, Franchise, Unknown} from the `Operated By` prefix.
- **City grouping:** Uppercase-normalize `City` first.
- **Phone:** Expect multi-value and alternate formats; split on `; ` if you need individual numbers.
