#!/usr/bin/env python3
"""
RAYEN QTO / BOQ engine.

Reads a JSON take-off file and writes a traceable BOQ workbook (.xlsx) with:
  - BOQ sheet with live Excel formulas (net -> waste -> total -> amount)
  - Sheet nesting (cutting plan summary) for panel materials
  - Steel weights computed from section designation
  - Assumptions / conflicts register
  - BOM sheet (Bill of Materials): what to BUY, grouped by material + spec,
    with stock bars from 1D cutting (first-fit-decreasing), sheets from nesting,
    purchase weight, utilisation, supplier / part no. / lead time
  - An independent Python re-computation printed to stdout for cross-checking

Usage:
  python3 qto.py takeoff.json -o BOQ.xlsx
  python3 qto.py --example > takeoff.json      # write a starter input file

Units supported per item ("unit"):
  m    -> length x count                       (profiles, trims, LED strip)
  m2   -> length x width x count               (cladding, vinyl, paint)
  nos  -> count                                (fixings, PSUs, modules)
  kg   -> length x count x kg/m                (steel sections; kg/m from "section")
  sheet-> pieces nested on stock sheets        (acrylic, ACP, MDF, aluminum sheet)

Optional BOM fields per item:
  bar_length_m  stock bar length for kg/m items (kg defaults to 6.0 m; m items
                are bought by the metre unless this is given)
  saw_kerf_mm   saw cut allowance for bar cutting (default 3)
  part_no, supplier, lead_time   procurement info shown on the BOM sheet
"""
import argparse
import json
import math
import re
import sys
from datetime import date

STEEL_DENSITY = 7850.0  # kg/m3
ALU_DENSITY = 2700.0

EXAMPLE = {
    "project": {
        "name": "Example — Pylon Sign P-01",
        "client": "Client name",
        "ref": "NT-QTO-0001",
        "revision": "R0",
        "prepared_by": "RAYEN / Abdelgadir Abdalla",
        "currency": "SAR",
        "sources": ["DWG A-101 R0 (pylon elevation)", "Spec section 10 14 00"]
    },
    "items": [
        {"id": "1.1", "description": "Main frame posts", "material": "Steel", "section": "SHS 100x100x4",
         "unit": "kg", "length_m": 4.2, "count": 4, "waste_pct": 5, "rate": 6.5,
         "source": "A-101 elevation, H=4200", "status": "VERIFIED"},
        {"id": "1.2", "description": "Horizontal rails", "material": "Steel", "section": "RHS 60x40x3",
         "unit": "kg", "length_m": 1.6, "count": 10, "waste_pct": 5, "rate": 6.5,
         "source": "A-101, 5 levels x 2 faces", "status": "CALCULATED"},
        {"id": "1.3", "description": "Base plate", "material": "Steel", "section": "PL 400x400x20",
         "unit": "kg", "length_m": 0.4, "count": 2, "waste_pct": 5, "rate": 7.0,
         "source": "TO BE CONFIRMED by structural engineer", "status": "ASSUMED"},
        {"id": "2.1", "description": "ACP cladding 4mm (two faces + sides)", "material": "ACP 4mm",
         "unit": "sheet", "stock": [1220, 2440], "kerf_mm": 4, "allow_rotation": True,
         "pieces": [{"w": 1200, "h": 2100, "n": 4}, {"w": 300, "h": 2100, "n": 4}, {"w": 1200, "h": 2100, "n": 2}],
         "waste_pct": 0, "rate": 240, "source": "A-101 cladding panels", "status": "CALCULATED"},
        {"id": "2.2", "description": "Acrylic face 5mm opal (logo box)", "material": "Acrylic 5mm",
         "unit": "sheet", "stock": [1220, 2440], "kerf_mm": 3, "allow_rotation": True,
         "pieces": [{"w": 1100, "h": 900, "n": 2}], "waste_pct": 0, "rate": 520,
         "source": "A-102 logo box", "status": "CALCULATED"},
        {"id": "3.1", "description": "Aluminum angle trim 25x25x2", "material": "Aluminum",
         "unit": "m", "length_m": 4.2, "count": 8, "waste_pct": 7, "rate": 18, "bar_length_m": 6.0,
         "source": "A-101 corner trims", "status": "CALCULATED"},
        {"id": "3.2", "description": "Vinyl graphics (printed, laminated)", "material": "Vinyl",
         "unit": "m2", "length_m": 1.1, "width_m": 0.9, "count": 2, "waste_pct": 10, "rate": 85,
         "source": "A-102", "status": "CALCULATED"},
        {"id": "4.1", "description": "LED module 12V 1.2W", "material": "Electrical",
         "unit": "nos", "count": 160, "waste_pct": 5, "rate": 3.2,
         "source": "Spacing 80mm ASSUMED — confirm with supplier", "status": "ASSUMED"},
        {"id": "4.2", "description": "Anchor bolt M20 chemical (HIT-RE or equal)", "material": "Fixings",
         "unit": "nos", "count": 8, "waste_pct": 0, "rate": 55,
         "source": "TO BE CONFIRMED — structural design", "status": "TO BE CONFIRMED"}
    ],
    "conflicts": [
        {"id": "C-01", "element": "Pylon height", "source_a": "A-101: 4200 mm", "source_b": "BOQ item 1: 4000 mm",
         "impact": "Steel and cladding quantities +5%", "resolution": "Issue RFI-001; quantities use A-101", "severity": "MEDIUM"}
    ],
    "assumptions": [
        "Waste allowances are Newtech defaults until factory data replaces them.",
        "Rates are budgetary estimates, not supplier quotations."
    ]
}


# ---------------------------------------------------------------- sections
def steel_kg_per_m(section: str, density=STEEL_DENSITY) -> float:
    """kg/m from a section designation (mm). Corner radii ignored (conservative +~1-3%)."""
    s = section.upper().replace("×", "X").replace(" ", "")
    nums = [float(x) for x in re.findall(r"[\d.]+", s)]
    if s.startswith(("SHS", "RHS")) and len(nums) >= 3:
        b, h, t = nums[0], nums[1], nums[2]
        area = 2 * t * (b + h - 2 * t)
    elif s.startswith("CHS") and len(nums) >= 2:
        d, t = nums[0], nums[1]
        area = math.pi * t * (d - t)
    elif s.startswith(("L", "ANG")) and len(nums) >= 3:
        a, b, t = nums[0], nums[1], nums[2]
        area = t * (a + b - t)
    elif s.startswith(("PL", "FLAT", "FB")) and len(nums) >= 3:
        # PL widthxlengthxthk -> per metre along "length" axis uses width x thk
        w, _l, t = nums[0], nums[1], nums[2]
        area = w * t
    elif s.startswith(("PL", "FLAT", "FB")) and len(nums) == 2:
        w, t = nums
        area = w * t
    else:
        raise ValueError(f"Unknown section format: {section!r} (use SHS/RHS bxhxt, CHS dxt, L axbxt, PL wxlxt)")
    return area * 1e-6 * density


# ---------------------------------------------------------------- nesting
def nest_sheets(pieces, stock, kerf=3, allow_rotation=True):
    """Shelf (guillotine-friendly) first-fit-decreasing nesting.
    Returns (sheet_count, utilisation_pct, layout) — layout is a list of sheets of placed pieces."""
    W, H = max(stock), min(stock)  # shelves run along the long side of the sheet
    items = []
    for p in pieces:
        for _ in range(int(p["n"])):
            items.append((p["w"], p["h"]))

    def orients(w, h):
        opts = [(w, h)] + ([(h, w)] if allow_rotation and w != h else [])
        return [o for o in opts if o[0] <= W and o[1] <= H]

    for w, h in items:
        if not orients(w, h):
            raise ValueError(f"Piece {w}x{h} does not fit stock {W}x{H} (rotation={allow_rotation})")
    items.sort(key=lambda x: (max(x), min(x)), reverse=True)

    sheets = []  # each: {"shelves":[{"y":, "h":, "x":}], "placed":[...]}
    for w0, h0 in items:
        cands = orients(w0, h0)
        placed = False
        for sh in sheets:
            # 1) existing shelf: any orientation that fits remaining width and shelf height
            for shelf in sh["shelves"]:
                for w, h in sorted(cands, key=lambda o: o[0]):
                    if h <= shelf["h"] and shelf["x"] + w <= W:
                        sh["placed"].append((shelf["x"], shelf["y"], w, h))
                        shelf["x"] += w + kerf
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
            # 2) new shelf on this sheet: lowest height orientation that fits
            used_h = sum(s["h"] + kerf for s in sh["shelves"])
            for w, h in sorted(cands, key=lambda o: o[1]):
                if used_h + h <= H:
                    sh["shelves"].append({"y": used_h, "h": h, "x": w + kerf})
                    sh["placed"].append((0, used_h, w, h))
                    placed = True
                    break
            if placed:
                break
        if not placed:
            w, h = sorted(cands, key=lambda o: o[1])[0]
            sheets.append({"shelves": [{"y": 0, "h": h, "x": w + kerf}], "placed": [(0, 0, w, h)]})
    net = sum(w * h for w, h in items)
    util = 100.0 * net / (len(sheets) * W * H) if sheets else 0.0
    return len(sheets), util, sheets, net


# ---------------------------------------------------------------- 1D bar cutting
DEFAULT_BAR_M = 6.0
STATUS_RANK = ["VERIFIED", "CALCULATED", "PROPOSED", "ASSUMED", "TO BE CONFIRMED", "NOT VERIFIED", "CONFLICT"]


def cut_bars(lengths_m, bar_m, kerf_m=0.003):
    """First-fit-decreasing 1D cutting. Pieces longer than a bar are split into
    full bars + remainder and reported as needing a splice.
    Returns (bars, net_m, overlong_pieces)."""
    remaining = []
    overlong = []
    queue = []
    for L in lengths_m:
        if L > bar_m + 1e-9:
            overlong.append(L)
            full = int(L // bar_m)
            remaining.extend([0.0] * full)  # full bars, no usable offcut
            rest = L - full * bar_m
            if rest > 1e-9:
                queue.append(rest)
        else:
            queue.append(L)
    for L in sorted(queue, reverse=True):
        for i, rem in enumerate(remaining):
            if L <= rem + 1e-9:
                remaining[i] = rem - L - kerf_m
                break
        else:
            remaining.append(bar_m - L - kerf_m)
    return len(remaining), sum(lengths_m), overlong


def build_bom(rows, nesting):
    """Group BOQ rows into purchase lines (what to buy)."""
    nest_by_id = {ns["id"]: ns for ns in nesting}
    groups = {}
    for it in rows:
        u = it["unit"]
        mat = it.get("material", "")
        bar_given = it.get("bar_length_m")
        is_plate = u == "kg" and it["section"].upper().replace(" ", "").startswith(("PL", "FLAT", "FB"))
        if is_plate and not bar_given:
            bar = None  # plates are cut from plate stock: buy by weight
            key = (mat, it["section"], "kg", None)
            spec, punit = it["section"], "kg"
        elif u == "kg":
            bar = float(bar_given or DEFAULT_BAR_M)
            key = (mat, it["section"], "bar", bar)
            spec, punit = it["section"], "bar"
        elif u == "m" and bar_given:
            bar = float(bar_given)
            key = (mat, it["description"], "bar", bar)
            spec, punit = it["description"], "bar"
        elif u == "sheet":
            bar = None
            spec = f"{it['stock'][0]}×{it['stock'][1]} mm sheet"
            key = (mat, spec, "sheet", None)
            punit = "sheet"
        else:
            bar = None
            spec = it["description"]
            key = (mat, spec, u, None)
            punit = u
        g = groups.setdefault(key, {
            "material": mat, "spec": spec, "punit": punit, "bar_m": bar, "unit": u,
            "kgpm": it.get("_kgpm"), "lengths": [], "kerf_m": float(it.get("saw_kerf_mm", 3)) / 1000,
            "net": 0.0, "qty": 0.0, "net_eq": 0.0, "items": [], "rates": [], "statuses": [],
            "part_no": "", "supplier": "", "lead_time": "", "notes": []})
        g["items"].append(it["id"])
        g["statuses"].append(it.get("status", "ASSUMED").upper())
        if it.get("rate") is not None:
            g["rates"].append(float(it["rate"]))
        for k in ("part_no", "supplier", "lead_time"):
            if it.get(k) and not g[k]:
                g[k] = str(it[k])
        g["net"] += it["_net"]
        if punit == "bar":
            g["lengths"].extend([float(it["length_m"])] * int(it.get("count", 0)))
        elif punit == "sheet":
            g["qty"] += nest_by_id[it["id"]]["sheets"]
            g["net_eq"] += nest_by_id[it["id"]]["net_eq"]
        elif punit in ("nos", "kg"):
            g["qty"] += it["_proc"]
        else:  # m / m2 bought by measure incl. waste
            g["qty"] += it["_total"]

    bom = []
    for i, g in enumerate(groups.values(), 1):
        g["no"] = f"M-{i:02d}"
        g["util"] = None
        if g["punit"] == "bar":
            bars, net_len, over = cut_bars(g["lengths"], g["bar_m"], g["kerf_m"])
            g["qty"] = bars
            g["net_len"] = net_len
            g["util"] = 100.0 * net_len / (bars * g["bar_m"]) if bars else 0.0
            g["notes"].append(f"1D FFD cutting, kerf {g['kerf_m'] * 1000:.0f} mm — planning estimate")
            for L in over:
                g["notes"].append(f"Piece {L:.3f} m > {g['bar_m']} m bar: SPLICE required (TO BE CONFIRMED)")
        elif g["punit"] == "sheet":
            g["util"] = 100.0 * g["net_eq"] / g["qty"] if g["qty"] else 0.0
        if len(set(g["rates"])) > 1:
            g["notes"].append("Rates differ between BOQ items: " + ", ".join(f"{r:g}" for r in g["rates"]) + " — first rate used")
        g["rate"] = g["rates"][0] if g["rates"] else None
        g["status"] = max(g["statuses"], key=lambda s: STATUS_RANK.index(s) if s in STATUS_RANK else 3)
        # independent purchase amount for the stdout cross-check
        if g["rate"] is None:
            g["amount"] = None
        elif g["punit"] == "bar" and g["unit"] == "kg":
            g["amount"] = g["qty"] * g["bar_m"] * g["kgpm"] * g["rate"]
        elif g["punit"] == "bar":
            g["amount"] = g["qty"] * g["bar_m"] * g["rate"]
        else:
            g["amount"] = g["qty"] * g["rate"]
        bom.append(g)
    return bom


# ---------------------------------------------------------------- compute
def compute(data):
    rows = []
    nesting = []
    for it in data["items"]:
        u = it["unit"]
        L = float(it.get("length_m", 0) or 0)
        Wd = float(it.get("width_m", 0) or 0)
        n = float(it.get("count", 0) or 0)
        waste = float(it.get("waste_pct", 0) or 0)
        kgpm = None
        if u == "m":
            net = L * n
        elif u == "m2":
            net = L * Wd * n
        elif u == "nos":
            net = n
        elif u == "kg":
            kgpm = steel_kg_per_m(it["section"], ALU_DENSITY if "alu" in it.get("material", "").lower() else STEEL_DENSITY)
            net = L * n * kgpm
        elif u == "sheet":
            cnt, util, layout, net_mm2 = nest_sheets(it["pieces"], it["stock"], it.get("kerf_mm", 3), it.get("allow_rotation", True))
            net = net_mm2 / (it["stock"][0] * it["stock"][1])  # net sheet-equivalents
            nesting.append({"id": it["id"], "description": it["description"], "stock": it["stock"],
                            "pieces": it["pieces"], "sheets": cnt, "util": util, "net_eq": net, "layout": layout})
            it["_sheets"] = cnt
        else:
            raise ValueError(f"Unsupported unit {u!r} in item {it['id']}")
        total = net * (1 + waste / 100)
        proc = it.get("_sheets") if u == "sheet" else (math.ceil(total) if u in ("nos",) else total)
        rate = it.get("rate")
        amount = (proc * rate) if rate is not None else None
        rows.append(dict(it, _net=net, _total=total, _proc=proc, _kgpm=kgpm, _amount=amount))
    return rows, nesting


# ---------------------------------------------------------------- excel
def write_xlsx(data, rows, nesting, out, bom=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    p = data["project"]
    cur = p.get("currency", "SAR")
    if bom is None:
        bom = build_bom(rows, nesting)
    wb = Workbook()
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    head_fill = PatternFill("solid", fgColor="1F2A44")
    head_font = Font(bold=True, color="FFFFFF")
    tag_fill = {"VERIFIED": "C6EFCE", "CALCULATED": "DDEBF7", "ASSUMED": "FFEB9C",
                "TO BE CONFIRMED": "F8CBAD", "CONFLICT": "FF9999", "PROPOSED": "E4DFEC"}

    # ---- Cover
    ws = wb.active
    ws.title = "Cover"
    ws["A1"] = "BILL OF QUANTITIES — QUANTITY TAKE-OFF"
    ws["A1"].font = Font(bold=True, size=16, color="1F2A44")
    info = [("Project", p.get("name")), ("Client", p.get("client")), ("Reference", p.get("ref")),
            ("Revision", p.get("revision")), ("Prepared by", p.get("prepared_by")),
            ("Date", date.today().isoformat()), ("Currency", cur),
            ("Sources", "; ".join(p.get("sources", [])))]
    for i, (k, v) in enumerate(info, start=3):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    ws["A12"] = "Status legend"
    ws["A12"].font = Font(bold=True)
    for i, (k, c) in enumerate(tag_fill.items(), start=13):
        ws.cell(i, 1, k).fill = PatternFill("solid", fgColor=c)
    ws["A21"] = "Quantities are net measured; waste is shown separately; procurement quantity is what to buy."
    ws["A22"] = "Rates are budgetary unless the Source column cites a supplier quotation."
    ws["A23"] = "BOM sheet = Bill of Materials: stock bars, sheets and packs to purchase, grouped by material/spec."
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 80

    # ---- BOQ
    b = wb.create_sheet("BOQ")
    headers = ["Item", "Description", "Material / Section", "Unit", "L (m)", "W (m)", "Count",
               "kg/m", "Net Qty", "Waste %", "Total Qty", "Procure Qty", f"Rate ({cur})",
               f"Amount ({cur})", "Calculation basis", "Source", "Status"]
    for c, h in enumerate(headers, 1):
        cell = b.cell(1, c, h)
        cell.fill, cell.font, cell.border = head_fill, head_font, border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    r = 2
    for it in rows:
        u = it["unit"]
        mat = it.get("material", "") + (f" — {it['section']}" if it.get("section") else "")
        b.cell(r, 1, it["id"])
        b.cell(r, 2, it["description"])
        b.cell(r, 3, mat)
        b.cell(r, 4, u)
        b.cell(r, 5, it.get("length_m"))
        b.cell(r, 6, it.get("width_m"))
        b.cell(r, 7, it.get("count"))
        if it["_kgpm"] is not None:
            b.cell(r, 8, round(it["_kgpm"], 3))
        if u == "m":
            b.cell(r, 9, f"=E{r}*G{r}"); basis = "L × Count"
        elif u == "m2":
            b.cell(r, 9, f"=E{r}*F{r}*G{r}"); basis = "L × W × Count"
        elif u == "nos":
            b.cell(r, 9, f"=G{r}"); basis = "Count"
        elif u == "kg":
            b.cell(r, 9, f"=E{r}*G{r}*H{r}"); basis = f"L × Count × kg/m ({it['section']})"
        else:
            b.cell(r, 9, round(it["_net"], 3))
            basis = f"Nested on {it['stock'][0]}×{it['stock'][1]} sheets — see Nesting"
        b.cell(r, 10, it.get("waste_pct", 0) / 100)
        b.cell(r, 11, f"=I{r}*(1+J{r})")
        if u == "sheet":
            b.cell(r, 12, it["_sheets"])
        elif u == "nos":
            b.cell(r, 12, f"=ROUNDUP(K{r},0)")
        else:
            b.cell(r, 12, f"=K{r}")
        if it.get("rate") is not None:
            b.cell(r, 13, it["rate"])
            b.cell(r, 14, f"=L{r}*M{r}")
        b.cell(r, 15, basis)
        b.cell(r, 16, it.get("source", ""))
        st = it.get("status", "ASSUMED").upper()
        sc = b.cell(r, 17, st)
        if st in tag_fill:
            sc.fill = PatternFill("solid", fgColor=tag_fill[st])
        for c in range(1, 18):
            b.cell(r, c).border = border
            b.cell(r, c).alignment = Alignment(vertical="top", wrap_text=c in (2, 3, 15, 16))
        for c in (5, 6, 8, 9, 11, 12):
            b.cell(r, c).number_format = "#,##0.000"
        b.cell(r, 10).number_format = "0%"
        b.cell(r, 13).number_format = "#,##0.00"
        b.cell(r, 14).number_format = "#,##0.00"
        r += 1
    last = r - 1
    b.cell(r, 13, "TOTAL").font = Font(bold=True)
    b.cell(r, 14, f"=SUM(N2:N{last})").font = Font(bold=True)
    b.cell(r, 14).number_format = "#,##0.00"
    widths = [7, 34, 26, 7, 8, 8, 8, 8, 11, 8, 11, 11, 11, 13, 30, 34, 16]
    for i, w in enumerate(widths, 1):
        b.column_dimensions[get_column_letter(i)].width = w
    b.freeze_panes = "C2"

    # ---- BOM (Bill of Materials)
    m = wb.create_sheet("BOM")
    mh = ["BOM No", "Material", "Specification", "Purchase unit", "Qty to buy", "Stock length (m)",
          "kg/m", "Purchase weight (kg)", "Net used", "Utilisation %", "Used in BOQ items",
          "Part no.", "Supplier", "Lead time", f"Rate ({cur})", "Rate per", f"Amount ({cur})", "Status", "Notes"]
    for c, h in enumerate(mh, 1):
        cell = m.cell(1, c, h)
        cell.fill, cell.font, cell.border = head_fill, head_font, border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    r = 2
    for g in bom:
        is_bar = g["punit"] == "bar"
        m.cell(r, 1, g["no"])
        m.cell(r, 2, g["material"])
        m.cell(r, 3, g["spec"])
        m.cell(r, 4, f"bar {g['bar_m']:g} m" if is_bar else g["punit"])
        m.cell(r, 5, round(g["qty"], 3))
        if is_bar:
            m.cell(r, 6, g["bar_m"])
        if g["unit"] == "kg":
            m.cell(r, 7, g["kgpm"])  # unrounded so Excel matches the stdout cross-check
            m.cell(r, 8, f"=E{r}*F{r}*G{r}" if is_bar else f"=E{r}")
            net_txt, rate_per, amt = f"{g['net']:.3f} kg", "kg", f"=H{r}*O{r}"
        elif is_bar:
            net_txt, rate_per, amt = f"{g['net_len']:.3f} m", "m", f"=E{r}*F{r}*O{r}"
        elif g["punit"] == "sheet":
            net_txt, rate_per, amt = f"{g['net_eq']:.3f} sheet-eq.", "sheet", f"=E{r}*O{r}"
        else:
            net_txt, rate_per, amt = f"{g['net']:.3f} {g['punit']}", g["punit"], f"=E{r}*O{r}"
        m.cell(r, 9, net_txt)
        if g["util"] is not None:
            m.cell(r, 10, round(g["util"], 1))
        m.cell(r, 11, ", ".join(g["items"]))
        m.cell(r, 12, g["part_no"])
        m.cell(r, 13, g["supplier"] or "TO BE CONFIRMED")
        m.cell(r, 14, g["lead_time"] or "TO BE CONFIRMED")
        if g["rate"] is not None:
            m.cell(r, 15, g["rate"])
            m.cell(r, 17, amt)
        m.cell(r, 16, rate_per)
        sc = m.cell(r, 18, g["status"])
        if g["status"] in tag_fill:
            sc.fill = PatternFill("solid", fgColor=tag_fill[g["status"]])
        m.cell(r, 19, "; ".join(g["notes"]))
        for c in range(1, 20):
            m.cell(r, c).border = border
            m.cell(r, c).alignment = Alignment(vertical="top", wrap_text=c in (3, 11, 19))
        for c in (5, 6, 7, 8):
            m.cell(r, c).number_format = "#,##0.000"
        m.cell(r, 15).number_format = "#,##0.00"
        m.cell(r, 17).number_format = "#,##0.00"
        r += 1
    mlast = r - 1
    m.cell(r, 16, "TOTAL").font = Font(bold=True)
    m.cell(r, 17, f"=SUM(Q2:Q{mlast})").font = Font(bold=True)
    m.cell(r, 17).number_format = "#,##0.00"
    m.cell(r + 2, 1, "BOM = what to buy (stock bars / sheets / packs), grouped by material + specification. "
                     "BOQ = measured quantities. BOM amount ≥ BOQ amount because offcuts are bought.")
    m.cell(r + 3, 1, "Bar counts use first-fit-decreasing 1D cutting; confirm on the cutting optimiser. "
                     "Supplier, part no. and lead time are TO BE CONFIRMED unless given.")
    for i, w in enumerate([8, 14, 30, 12, 10, 10, 8, 13, 16, 11, 16, 12, 16, 12, 11, 8, 13, 16, 50], 1):
        m.column_dimensions[get_column_letter(i)].width = w
    m.freeze_panes = "C2"

    # ---- Nesting
    n = wb.create_sheet("Nesting")
    nh = ["Item", "Description", "Stock (mm)", "Pieces (w×h×n)", "Net area (sheet-eq.)", "Sheets to buy", "Utilisation %"]
    for c, h in enumerate(nh, 1):
        cell = n.cell(1, c, h)
        cell.fill, cell.font, cell.border = head_fill, head_font, border
    for i, ns in enumerate(nesting, 2):
        n.cell(i, 1, ns["id"])
        n.cell(i, 2, ns["description"])
        n.cell(i, 3, f"{ns['stock'][0]}×{ns['stock'][1]}")
        n.cell(i, 4, "; ".join(f"{p_['w']}×{p_['h']}×{p_['n']}" for p_ in ns["pieces"]))
        n.cell(i, 5, round(ns["net_eq"], 3))
        n.cell(i, 6, ns["sheets"])
        n.cell(i, 7, round(ns["util"], 1))
    for i, w in enumerate([7, 34, 14, 40, 18, 14, 14], 1):
        n.column_dimensions[get_column_letter(i)].width = w
    n.cell(len(nesting) + 3, 1, "Shelf nesting with kerf; verify on CNC nesting software before cutting.")

    # ---- Register
    g = wb.create_sheet("Conflicts & Assumptions")
    gh = ["ID", "Element", "Source A", "Source B", "Impact", "Recommended resolution", "Severity"]
    for c, h in enumerate(gh, 1):
        cell = g.cell(1, c, h)
        cell.fill, cell.font, cell.border = head_fill, head_font, border
    rr = 2
    for cf in data.get("conflicts", []):
        for c, k in enumerate(["id", "element", "source_a", "source_b", "impact", "resolution", "severity"], 1):
            g.cell(rr, c, cf.get(k, ""))
        rr += 1
    rr += 1
    g.cell(rr, 1, "Assumptions").font = Font(bold=True)
    for a in data.get("assumptions", []):
        rr += 1
        g.cell(rr, 1, "•")
        g.cell(rr, 2, a)
    for i, w in enumerate([8, 22, 28, 28, 30, 36, 10], 1):
        g.column_dimensions[get_column_letter(i)].width = w

    wb.save(out)


def main():
    ap = argparse.ArgumentParser(description="RAYEN QTO/BOQ engine")
    ap.add_argument("input", nargs="?", help="take-off JSON")
    ap.add_argument("-o", "--out", default="BOQ.xlsx")
    ap.add_argument("--example", action="store_true", help="print an example input JSON")
    a = ap.parse_args()
    if a.example:
        json.dump(EXAMPLE, sys.stdout, indent=2, ensure_ascii=False)
        return
    if not a.input:
        ap.error("input JSON required (or --example)")
    data = json.load(open(a.input, encoding="utf-8-sig"))  # -sig: accept Windows UTF-8 BOM
    rows, nesting = compute(data)
    bom = build_bom(rows, nesting)
    write_xlsx(data, rows, nesting, a.out, bom)

    cur = data["project"].get("currency", "SAR")
    print(f"BOQ written: {a.out}")
    print(f"{'Item':<6}{'Unit':<7}{'Net':>12}{'Total':>12}{'Procure':>10}{'Amount':>14}  Status")
    grand = 0.0
    for it in rows:
        amt = it["_amount"]
        grand += amt or 0
        print(f"{it['id']:<6}{it['unit']:<7}{it['_net']:>12.3f}{it['_total']:>12.3f}{float(it['_proc']):>10.2f}"
              f"{(amt if amt is not None else 0):>14,.2f}  {it.get('status','')}")
    for ns in nesting:
        print(f"Nesting {ns['id']}: {ns['sheets']} sheet(s) {ns['stock'][0]}x{ns['stock'][1]}, utilisation {ns['util']:.1f}%")
    print(f"TOTAL ({cur}, budgetary unless quoted): {grand:,.2f}")
    print("BOM (Bill of Materials — what to buy):")
    btot = 0.0
    for g in bom:
        btot += g["amount"] or 0
        unit = f"bar {g['bar_m']:g}m" if g["punit"] == "bar" else g["punit"]
        util = f"  util {g['util']:.1f}%" if g["util"] is not None else ""
        print(f"  {g['no']:<6}{g['material'][:12]:<13}{g['spec'][:30]:<31}{g['qty']:>9.2f} {unit:<10}"
              f"{(g['amount'] or 0):>12,.2f}{util}  [{', '.join(g['items'])}]")
    print(f"BOM TOTAL ({cur}): {btot:,.2f}")


if __name__ == "__main__":
    main()
