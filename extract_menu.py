#!/usr/bin/env python3
"""Extract the nutrition tables from Menu-Nutritionals-2026-05-05.pdf into a
clean CSV.

The PDF is text-based (no ruled tables), so we parse extracted text lines.
A data row is: <item name> <10 numeric values> <optional allergens>, where the
10 values are Calories, Fat, SatFat, TransFat, Chol, Sodium, Carbs, Fiber,
Sugars, Protein. Values may be decimals. Item names may themselves contain
numbers, so we anchor on the *trailing* contiguous numeric run.

Dependency: pdfplumber (pip install pdfplumber).
"""
import csv, re
import pdfplumber

PDF = "Menu-Nutritionals-2026-05-05.pdf"
OUT = "menu_nutritionals.csv"

NUMTOK = re.compile(r"^\d+(?:\.\d+)?$")
FOOTER = re.compile(r"^Updated \d\d/\d\d/\d\d \d+$")
COLHDR = re.compile(r"^Name\s+Cal\b")
WRAP   = re.compile(r"^\(g\)\s+\(mg\)\s+\(g\)$")          # wrapped 2nd header line
VALUE_FIELDS = ["Calories", "Fat_g", "SatFat_g", "TransFat_g", "Chol_mg",
                "Sodium_mg", "Carbs_g", "Fiber_g", "Sugars_g", "Protein_g"]

ROLE_PREFIXES = [
    ("Includes:", "includes"),
    ("Plus your choice of:", "choice"),
    ("Add-ons:", "add-on"),
]

def trailing_numeric_run(tokens):
    """Return (start_index, count) of the trailing run of numeric tokens,
    i.e. the last maximal run that is not followed by any later numeric token.
    Allergen text has no digits, so the value block is the last numeric run."""
    last_num = -1
    for i, t in enumerate(tokens):
        if NUMTOK.match(t):
            last_num = i
    if last_num == -1:
        return None
    # walk left from last_num while contiguous numerics
    start = last_num
    while start - 1 >= 0 and NUMTOK.match(tokens[start - 1]):
        start -= 1
    return start, last_num - start + 1

def clean_item(name):
    """Strip role prefixes and known rotated-label artifacts; return (item, role)."""
    role = "main"
    name = name.strip()
    for prefix, r in ROLE_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
            role = r
            break
    # Rotated "Toppings:" label got split across rows -> "ToppingsChocolate..." and ": ..."
    name = re.sub(r"^Toppings(?=[A-Z])", "", name)   # leading glued "Toppings"
    name = re.sub(r"^:\s*", "", name)                # leading stray colon
    return name.strip(), role

def is_section(line, next_line):
    """A line is a section/sub-section header if it's ALL-CAPS, or if the next
    line is the column header (e.g. the mixed-case 'Waffles' sub-section)."""
    if not re.search(r"[A-Za-z]", line):
        return False
    if line.upper() == line:                         # all caps (ignoring digits/symbols)
        return True
    if next_line is not None and COLHDR.match(next_line):
        return True
    return False

def norm_section(s):
    s = s.replace("™", "").replace("©", "").strip()  # drop ™ / ©
    s = re.sub(r"\s+CONTINUED$", "", s, flags=re.I)   # merge "... CONTINUED"
    return s

# ---- read all pages, drop only footers, keep order -------------------------
# Column-header lines are kept: a section header is the line immediately before
# a "Name Cal ..." column header, which is the reliable structural delimiter.
lines = []   # (page, text)
with pdfplumber.open(PDF) as pdf:
    for pi, page in enumerate(pdf.pages, 1):
        for raw in (page.extract_text() or "").split("\n"):
            t = raw.strip()
            if not t or FOOTER.match(t):
                continue
            lines.append((pi, t))

# ---- stateful pass with pending-name merge for split combo rows ------------
rows = []
warnings = []
skipped_desc = []
section = ""
pending_name = None          # combo title whose 10 numbers are on the next line

for idx, (page, line) in enumerate(lines):
    if COLHDR.match(line) or WRAP.match(line):       # table column headers
        continue
    nxt = lines[idx + 1][1] if idx + 1 < len(lines) else None
    toks = line.split()
    run = trailing_numeric_run(toks)

    # Section header = a non-data line immediately followed by the column header
    # (covers both ALL-CAPS main headers and mixed-case sub-sections like "Waffles").
    if (run is None or run[1] < 10) and nxt is not None and COLHDR.match(nxt):
        section = norm_section(line)
        pending_name = None
        continue

    if run is not None and run[1] >= 10:
        start, count = run
        # value block = last 10 of the trailing run; any extra leading numerics
        # belong to the name (defensive; not expected in this PDF)
        val_start = start + (count - 10)
        values = toks[val_start:val_start + 10]
        name_tokens = toks[:val_start]
        allergens = " ".join(toks[val_start + 10:]).strip()

        if name_tokens:
            raw_name = " ".join(name_tokens)
        elif pending_name:
            raw_name = pending_name           # numbers-first line -> use held combo title
        else:
            warnings.append((page, "values with no name", line))
            continue
        pending_name = None

        item, role = clean_item(raw_name)
        rows.append({
            "Page": page, "Section": section, "Role": role, "Item": item,
            **{f: values[i] for i, f in enumerate(VALUE_FIELDS)},
            "Allergens": allergens,
        })
        continue

    # No 10-run and not a section: either a combo title (numbers next line) or
    # a description/noise line.
    if nxt is not None:
        nxt_run = trailing_numeric_run(nxt.split())
        # numbers-first next line => this is the combo title
        if nxt_run and nxt_run[0] == 0 and nxt_run[1] >= 10:
            pending_name = line
            continue
    skipped_desc.append((page, line))

# ---- write CSV --------------------------------------------------------------
cols = ["Page", "Section", "Role", "Item"] + VALUE_FIELDS + ["Allergens"]
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

# ---- report -----------------------------------------------------------------
from collections import Counter
print(f"Extracted {len(rows)} data rows -> {OUT}")
print(f"Sections ({len(set(r['Section'] for r in rows))}):")
for s, c in Counter(r["Section"] for r in rows).items():
    print(f"  {c:4}  {s}")
print(f"\nRoles: {dict(Counter(r['Role'] for r in rows))}")

# decimal proof + range sanity
dec = sum(1 for r in rows for f in VALUE_FIELDS if "." in r[f])
cals = [float(r["Calories"]) for r in rows]
print(f"\nDecimal-valued cells preserved: {dec}")
print(f"Calories range: {min(cals)} .. {max(cals)}")
print(f"All rows have 10 numeric values: {all(all(NUMTOK.match(r[f]) for f in VALUE_FIELDS) for r in rows)}")

print(f"\nParse warnings (real-data misses): {len(warnings)}")
for p, why, l in warnings:
    print(f"  p{p} [{why}]: {l}")
print(f"Skipped non-data lines (descriptions/labels): {len(skipped_desc)}")
for p, l in skipped_desc:
    print(f"  p{p}: {l}")
