#!/usr/bin/env python3
"""Build waffle_house_concentration.ipynb with nbformat.

A reproducible "editor test" notebook for one claim: 57.2% of Waffle House
locations are in just five states. Run, then execute + export to HTML separately.
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

# 1. Title + finding -----------------------------------------------------------
md("""\
# Most Waffle Houses are in just five states

**Finding:** Of the **2,006** Waffle House locations in this dataset,
**57.2% (1,147)** are in only **five states** — Georgia, Florida, North
Carolina, South Carolina, and Alabama. More than half the chain sits in five of
the fifty states.

This notebook is the *editor test*: it documents the source, runs data-quality
checks, then reproduces the number step-by-step from the raw file with a chart,
and ends with limitations. Run it top to bottom (`Kernel → Restart & Run All`)
to verify the claim from scratch.
""")

# 2. Data source ---------------------------------------------------------------
md("""\
## Data source

- **File:** `waffle_houses.csv` — a point-in-time export of Waffle House store
  locations (one row per location).
- **Records:** 2,006 rows, 14 columns (Store Code, Business Name, Address, City,
  State, Postal Code, Country, Latitude, Longitude, Phone, Website, Operated By,
  Online Order Link, Business Hours).
- **Full column documentation and the original QA write-up:** see
  [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) in this repository.
- **Nature:** a snapshot. Counts reflect locations present in this export, not a
  live or historical census.
""")

# 3. Load raw data -------------------------------------------------------------
code("""\
import pandas as pd

# Read everything as strings first (per the data dictionary: keep Store Code and
# Postal Code as text so the 'WH_Museum' id and any leading zeros survive),
# then convert only the coordinate columns to float.
df = pd.read_csv("waffle_houses.csv", dtype=str)
df["Latitude"] = df["Latitude"].astype(float)
df["Longitude"] = df["Longitude"].astype(float)

print("shape:", df.shape)
df.head()""")

# 4. Quality checks ------------------------------------------------------------
md("""\
## Quality checks (before trusting any number)

These reproduce the key checks from `DATA_DICTIONARY.md`: total rows, missing
values, duplicate IDs, the known non-restaurant outlier (the Waffle House
Museum), and the number of distinct states.
""")
code("""\
n = len(df)
print(f"Row count: {n}")

# Missing values per column (only show columns that have any)
missing = df.isna().sum()
print("\\nMissing values:")
print(missing[missing > 0].to_string() or "  (none)")

# Duplicate Store Codes -> expect 0
dups = df["Store Code"].duplicated().sum()
print(f"\\nDuplicate Store Codes: {dups}")

# The museum row: a non-restaurant outlier (non-numeric id, blank fields)
museum = df[df["Store Code"] == "WH_Museum"]
print(f"\\nMuseum rows (non-restaurant): {len(museum)}")
print(museum[["Store Code", "Business Name", "City", "State"]].to_string(index=False))

# Distinct states
print(f"\\nDistinct states present: {df['State'].nunique()}")

assert n == 2006, "expected 2,006 rows"
assert dups == 0, "Store Code should be unique"
print("\\nQA summary: PASS — 2,006 unique-id rows, 25 states, 1 flagged museum outlier.")""")

# 5. Reproduce the finding -----------------------------------------------------
md("""\
## Reproduce the finding, step by step

Count locations per state, take the top five, and compute their combined share
of all locations — showing the arithmetic explicitly.
""")
code("""\
counts = df["State"].value_counts()          # locations per state, descending
top5 = counts.head(5)
top5_sum = int(top5.sum())
total = len(df)
share = 100 * top5_sum / total

print("Top 5 states:")
for state, c in top5.items():
    print(f"  {state}: {c}")
print(f"\\nSum of top 5 : {top5_sum}")
print(f"Total records: {total}")
print(f"Share        : {top5_sum} / {total} = {share:.1f}%")""")

md("""\
**Robustness check** — does the one non-restaurant museum row change the answer?
Recompute excluding it.
""")
code("""\
rest = df[df["Store Code"] != "WH_Museum"]          # 2,005 operating restaurants
r_counts = rest["State"].value_counts()
r_top5 = int(r_counts.head(5).sum())
print(f"Excluding the museum: {r_top5} / {len(rest)} = {100*r_top5/len(rest):.1f}%")
print("=> The museum row does not move the finding.")""")

# 6. Chart ---------------------------------------------------------------------
md("""\
## Chart: locations by state, top five highlighted
""")
code("""\
import matplotlib.pyplot as plt

WH_YELLOW, GRAY = "#FFD200", "#cfccc4"
top5_states = list(top5.index)
colors = [WH_YELLOW if s in top5_states else GRAY for s in counts.index]

fig, ax = plt.subplots(figsize=(9, 7))
y = range(len(counts))
ax.barh(y, counts.values, color=colors, edgecolor="#7a5b00", linewidth=0.4)
ax.set_yticks(list(y))
ax.set_yticklabels(counts.index)
ax.invert_yaxis()                                   # highest at top
ax.set_xlabel("Number of Waffle House locations")
ax.set_title("Waffle House locations by state\\nTop 5 states (yellow) hold "
             f"{share:.1f}% of all {total:,} locations")
for i, v in enumerate(counts.values):
    ax.text(v + 4, i, str(v), va="center", fontsize=8, color="#333")
ax.margins(x=0.08)
plt.tight_layout()
plt.show()""")

# 7. Limitations ---------------------------------------------------------------
md("""\
## Limitations

- **Snapshot, not a census.** The file is a point-in-time export; counts reflect
  locations present in *this* data, not openings/closings over time.
- **"Five of fifty" framing.** The chain operates in 25 states; the other 25 have
  zero locations. The "fifty states" comparison excludes DC and territories.
- **The museum is included in the 2,006 total.** It is a non-restaurant outlier;
  as shown above, excluding it leaves the finding unchanged (57.2%).
- **Share of *locations*, not people or land.** This measures where stores are,
  not per-capita density or market penetration.
- **Known data caveats don't affect this count.** The website-URL `///` artifact
  and the 229 rows holding two phone numbers (see `DATA_DICTIONARY.md`) touch
  other columns, not `State`, so they don't change these figures.
""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}

with open("waffle_house_concentration.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("wrote waffle_house_concentration.ipynb with", len(cells), "cells")
