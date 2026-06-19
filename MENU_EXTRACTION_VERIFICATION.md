# Menu nutrition extraction — verification

**Source:** `Menu-Nutritionals-2026-05-05.pdf` (10 pages)  
**Output:** `menu_nutritionals.csv`  
**Parser:** `extract_menu.py` (pdfplumber text parse)

> An extracted table is a *claim, not a fact, until checked against the source.* Below, 5 parsed rows are shown next to the exact raw PDF text they came from.

## 5 rows: raw PDF line → parsed CSV fields

### Plain item with allergens
**Raw PDF (p1):** `Regular Hashbrowns 190 7 3 0 0 240 29 3 0 3 Soy.`
**Parsed:** Section=*BREAKFAST ALL-STAR SPECIAL* · Role=*main* · **Item=`Regular Hashbrowns`**
  - Values: Calories=190 · Fat g=7 · SatFat g=3 · TransFat g=0 · Chol mg=0 · Sodium mg=240 · Carbs g=29 · Fiber g=3 · Sugars g=0 · Protein g=3
  - Allergens: `Soy.`

### Name contains numbers (must NOT be read as values)
**Raw PDF (p1):** `White Toast - 2 Slices 130 2 0 0 0 260 25 1 3 4 Milk, Soy, Wheat.`
**Parsed:** Section=*BREAKFAST ALL-STAR SPECIAL* · Role=*main* · **Item=`White Toast - 2 Slices`**
  - Values: Calories=130 · Fat g=2 · SatFat g=0 · TransFat g=0 · Chol mg=0 · Sodium mg=260 · Carbs g=25 · Fiber g=1 · Sugars g=3 · Protein g=4
  - Allergens: `Milk, Soy, Wheat.`

### Decimal values + role prefix
**Raw PDF (p4):** `Add-ons: American Cheese - 1 slice 50 5 2.5 0 12.5 250 1 0 1 2.5 Milk, Soy.`
**Parsed:** Section=*Grilled Biscuits* · Role=*add-on* · **Item=`American Cheese - 1 slice`**
  - Values: Calories=50 · Fat g=5 · SatFat g=2.5 · TransFat g=0 · Chol mg=12.5 · Sodium mg=250 · Carbs g=1 · Fiber g=0 · Sugars g=1 · Protein g=2.5
  - Allergens: `Milk, Soy.`

### Combo total split across TWO lines (name + numbers)
**Raw PDF (p3):** `Meat Lover's Chicken & Eggs: 2 Pieces of Grilled Chicken and 2 Eggs - Scrambled`
**Raw PDF (next line):** `440 16 4 1 498 2036 6 0 2 70 Egg, Soy.`
**Parsed:** Section=*EGG BREAKFASTS* · Role=*main* · **Item=`Meat Lover's Chicken & Eggs: 2 Pieces of Grilled Chicken and 2 Eggs - Scrambled`**
  - Values: Calories=440 · Fat g=16 · SatFat g=4 · TransFat g=1 · Chol mg=498 · Sodium mg=2036 · Carbs g=6 · Fiber g=0 · Sugars g=2 · Protein g=70
  - Allergens: `Egg, Soy.`

### Row with no allergens
**Raw PDF (p1):** `Sliced Tomatoes 10 0 0 0 0 0 2 0 2 0`
**Parsed:** Section=*BREAKFAST ALL-STAR SPECIAL* · Role=*main* · **Item=`Sliced Tomatoes`**
  - Values: Calories=10 · Fat g=0 · SatFat g=0 · TransFat g=0 · Chol mg=0 · Sodium mg=0 · Carbs g=2 · Fiber g=0 · Sugars g=2 · Protein g=0
  - Allergens: `(none)`

## Automated checks

- **Rows extracted:** 381
- **Sections:** 19 (e.g. BREAKFAST ALL-STAR SPECIAL, BREAKFAST HASHBROWN BOWLS, EGG BREAKFASTS, Waffles, Hashbrowns and Toppings, …)
- **Every row has exactly 10 numeric values:** True
- **Decimal values preserved (proof integer-only parsing would corrupt):** 3 cells (e.g. the American Cheese add-on: 2.5 / 12.5 / 2.5)
- **Calories range:** 0–920 (plausible for menu items)
- **Parse warnings (value-bearing lines that failed to parse):** 0

## What could have gone wrong (and how it was handled)

- **Integer-only assumption — REAL risk, caught.** Some values are decimals (`2.5`, `12.5`). The parser accepts `\d+(\.\d+)?`; an integer cast would have silently mangled these rows.
- **Numbers inside item names.** Names like *White Toast - 2 Slices* and *Chicken Filet ( 1)* contain digits. The parser anchors on the **trailing** run of 10 numeric tokens, so name-digits are never mistaken for nutrition values.
- **Combo totals split across two lines.** Combo titles (e.g. *Meat Lover's Chicken & Eggs: …*) sit on one line with their 10 numbers on the next. The parser holds the title and attaches it to the following numbers-first line.
- **Wrapped column headers.** The header wraps to a second line `(g) (mg) (g)`; both header lines are skipped.
- **Section vs. sub-section.** Every table header is immediately followed by the `Name Cal …` column header — used as the reliable delimiter, so mixed-case sub-sections (*Waffles*, *Beverages*, *Pies*) are captured, not absorbed.
- **`™` / `©` / `CONTINUED`.** Stripped/merged so `EGG BREAKFASTS` and `EGG BREAKFASTS CONTINUED` are one section.

### Known imperfections (documented, no nutrition data lost)

- **Rotated 'Toppings:' label** was split by the PDF across adjacent rows (`ToppingsChocolate Chips`, `: Blueberry Nougat`); the parser strips the glued fragment, but this is a PDF-rendering artifact worth knowing about.
- **A few component rows show Role=`main` instead of `choice`/`add-on`.** In a handful of spots the rotated *Plus your choice of:* / *Add-Ons:* label wrapped onto its own line, so the prefix wasn't attached to the next item. **Values are intact**; only the role tag is affected.
- **Combo *group* titles without their own nutrition** (e.g. *Chicken Dinner*, *T-Bone Dinner*) are not emitted as rows (they have no values) and not stored as a grouping column. Their component items are still captured under the parent section.
- **Combos and their components coexist.** Totals rows (e.g. a Hashbrown Bowl) sit alongside their `Includes:` components, so **summing a column double-counts combos.** Use the `Role` column to separate totals from components before aggregating.
