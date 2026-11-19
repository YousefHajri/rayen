#!/usr/bin/env python3
"""RAYEN lighting calc — lumen method (zonal cavity simplified) + LPD check.

  python3 lighting_calc.py rooms.json [-o Lighting.xlsx]
  python3 lighting_calc.py --example

N = (E x A) / (F x n x UF x MF)
  E target maintained illuminance (lx) · A area (m2) · F lumens per lamp · n lamps per luminaire
  UF utilisation factor (from manufacturer table vs room index K; default estimated) · MF maintenance factor
Room index K = (L x W) / (Hm x (L + W)),  Hm = mounting height above working plane.
Outputs: luminaire count, layout grid (rows x cols), spacing, achieved lux, W/m2 (LPD).
Targets are TYPICAL (EN 12464-1 style) — confirm against project spec / SBC 601 energy LPD limits.
"""
import argparse, json, math

TARGETS = {  # lx maintained, UGR limit, Ra min  (typical, EN 12464-1:2021 order of magnitude)
    "office_open": (500, 19, 80), "meeting": (500, 19, 80), "reception": (300, 22, 80),
    "corridor": (100, 28, 40), "toilet": (200, 25, 80), "retail_general": (300, 22, 80),
    "showroom": (500, 22, 90), "classroom": (500, 19, 80), "restaurant": (200, 22, 80),
    "kitchen_commercial": (500, 22, 80), "lobby": (200, 22, 80), "stair": (150, 25, 40),
    "storage": (100, 25, 60), "workshop_fine": (750, 19, 80), "parking": (75, 25, 40),
}

EXAMPLE = {"project": "Newtech showroom", "mf": 0.8, "workplane_m": 0.8,
           "rooms": [
               {"name": "Showroom", "use": "showroom", "length": 12, "width": 8, "ceiling_h": 3.2,
                "luminaire": {"model": "LED downlight 30W (ASSUMED)", "lumens": 3300, "watts": 30, "lamps": 1}},
               {"name": "Open office", "use": "office_open", "length": 10, "width": 6, "ceiling_h": 2.9,
                "luminaire": {"model": "LED panel 600x600 36W (ASSUMED)", "lumens": 4000, "watts": 36, "lamps": 1}, "uf": 0.6},
               {"name": "Corridor", "use": "corridor", "length": 15, "width": 1.8, "ceiling_h": 2.7,
                "luminaire": {"model": "LED downlight 12W (ASSUMED)", "lumens": 1200, "watts": 12, "lamps": 1}}]}


def uf_estimate(k):
    """Rough UF for direct LED downlights, reflectances 70/50/20. Replace with photometric table."""
    table = [(0.6, 0.40), (0.8, 0.47), (1.0, 0.52), (1.25, 0.57), (1.5, 0.61), (2.0, 0.66), (2.5, 0.70), (3.0, 0.72), (4.0, 0.75), (5.0, 0.77)]
    if k <= table[0][0]: return table[0][1]
    for (k1, u1), (k2, u2) in zip(table, table[1:]):
        if k <= k2: return u1 + (u2 - u1) * (k - k1) / (k2 - k1)
    return table[-1][1]


def calc(r, mf, wp):
    L, W, H = r["length"], r["width"], r["ceiling_h"]
    E, ugr, ra = TARGETS.get(r["use"], (r.get("lux", 300), None, 80))
    E = r.get("lux", E)
    A = L * W
    hm = H - wp
    K = (L * W) / (hm * (L + W))
    uf_src = "given" if "uf" in r else "ESTIMATED"
    uf = r.get("uf", uf_estimate(K))
    lum = r["luminaire"]
    phi = lum["lumens"] * lum.get("lamps", 1)
    N = math.ceil(E * A / (phi * uf * mf))
    best = None  # smallest grid >= N with near-square spacing (ratio <= 1.5 preferred)
    for c in range(1, N + 1):
        rr = math.ceil(N / c)
        ratio = max(L / c, W / rr) / min(L / c, W / rr)
        key = (ratio > 1.5, c * rr, ratio)
        if best is None or key < best[0]:
            best = (key, c, rr)
    cols, rows = best[1], best[2]
    N2 = rows * cols
    Eavg = N2 * phi * uf * mf / A
    lpd = N2 * lum["watts"] / A
    sx, sy = L / cols, W / rows
    return dict(name=r["name"], use=r["use"], area=round(A, 2), K=round(K, 2), uf=round(uf, 2), uf_src=uf_src, mf=mf,
                target=E, ugr=ugr, ra=ra, n_calc=N, grid=f"{cols} x {rows}", n=N2, spacing=f"{sx:.2f} x {sy:.2f} m",
                shr=round(max(sx, sy) / hm, 2), lux=round(Eavg), lpd=round(lpd, 1), model=lum["model"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", nargs="?"); ap.add_argument("-o", "--out"); ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2)); return
    d = json.load(open(a.json, encoding="utf-8"))
    res = [calc(r, d.get("mf", 0.8), d.get("workplane_m", 0.8)) for r in d["rooms"]]
    print(f"{'Room':14s}{'A m2':>7s}{'K':>6s}{'UF':>6s}{'Target':>8s}{'N':>4s}{'Grid':>8s}{'Spacing':>14s}{'S/Hm':>6s}{'Avg lx':>8s}{'W/m2':>7s}")
    for x in res:
        flag = " ! S/Hm>1.5 check uniformity" if x["shr"] > 1.5 else ""
        print(f"{x['name'][:14]:14s}{x['area']:7.1f}{x['K']:6.2f}{x['uf']:6.2f}{x['target']:8d}{x['n']:4d}{x['grid']:>8s}{x['spacing']:>14s}{x['shr']:6.2f}{x['lux']:8d}{x['lpd']:7.1f}{flag}")
    print("UF ESTIMATED where not given — replace with manufacturer photometric data (DIALux/Relux for final design).")
    if a.out:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = "Lighting"
        head = ["Room", "Use", "L m", "W m", "H m", "Area m2", "Hm m", "K", "UF", "UF source", "MF", "Target lx", "UGR max", "Ra min",
                "Luminaire", "Lumens", "Watts", "Rows", "Cols", "N", "Avg lx (formula)", "W/m2 (formula)"]
        ws.append([d.get("project", "")]); ws.append(head)
        for c in ws[2]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3864")
        wp = d.get("workplane_m", 0.8)
        for r, x in zip(d["rooms"], res):
            i = ws.max_row + 1
            cols, rows = x["grid"].split(" x ")
            lum = r["luminaire"]
            ws.append([x["name"], x["use"], r["length"], r["width"], r["ceiling_h"], f"=C{i}*D{i}", f"=E{i}-{wp}",
                       f"=ROUND(C{i}*D{i}/(G{i}*(C{i}+D{i})),2)", x["uf"], x["uf_src"], x["mf"], x["target"], x["ugr"], x["ra"],
                       lum["model"], lum["lumens"] * lum.get("lamps", 1), lum["watts"], int(rows), int(cols), f"=R{i}*S{i}",
                       f"=ROUND(T{i}*P{i}*I{i}*K{i}/F{i},0)", f"=ROUND(T{i}*Q{i}/F{i},1)"])
        ws.append([]); ws.append(["Status: CALCULATED (lumen method). UF estimated unless 'given'. Final design by photometric software; LPD limits per SBC 601 to be verified."])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 13
        wb.save(a.out); print("saved", a.out)


if __name__ == "__main__":
    main()
