#!/usr/bin/env python3
"""RAYEN fabrication parts — CNC/laser-ready DXF per part + parts sheet + parts list + flat patterns.

  python3 fab_parts.py parts.json -o OUTDIR [--qto parts-qto.json]
  python3 fab_parts.py --example

Part kinds
  plate  : shape rect (w,h,corner_r) or polygon (pts) + holes / hole_pattern / slots / engrave text
  tray   : sheet-metal box/tray flat pattern (base outside W x H, flange F, thickness T, inner R, K-factor)
           BA = pi/2 * (R + K*T) per 90deg bend · OSSB = R + T · flat = W + 2F - 2*(2*OSSB - BA)
  strip  : bent return strip (channel-letter / lightbox return): developed length + bend/notch marks

CNC layers: CUT (red, closed polylines, outer contour) · CUT-IN (inner contours) · DRILL (circles) ·
BEND (dashed, with UP/DOWN + angle note) · ENGRAVE · NOTE (never cut) · DIM.
Units mm, 1:1. Each part DXF has ONE part at origin — ready for nesting software (SigmaNEST, RDWorks, Aspire…).
Status of every output: CALCULATED — verify K-factor / bend deduction with the press-brake shop before cutting.
"""
import argparse, json, math, os, sys
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

EXAMPLE = {
    "project": "LB-01 Lightbox — Newtech", "drawing_no": "NT-FAB-LB01", "rev": "R0",
    "parts": [
        {"mark": "P1", "kind": "plate", "name": "Face panel", "material": "Acrylic opal", "thickness": 5, "qty": 1,
         "process": "CNC router", "shape": {"type": "rect", "w": 2400, "h": 800, "corner_r": 10},
         "hole_pattern": {"d": 5, "edge": 12, "max_pitch": 300}},
        {"mark": "T1", "kind": "tray", "name": "Back tray", "material": "Aluminium 5052", "thickness": 1.5, "qty": 1,
         "process": "Laser + press brake", "W": 2400, "H": 800, "F": 150, "R": 1.5, "K": 0.33,
         "holes": [{"x": 200, "y": 400, "d": 22, "note": "cable gland"}], "relief_d": 4},
        {"mark": "B1", "kind": "plate", "name": "Wall bracket", "material": "GI steel", "thickness": 3, "qty": 6,
         "process": "Laser + bend 90", "shape": {"type": "polygon", "pts": [[0, 0], [120, 0], [120, 60], [80, 60], [80, 30], [0, 30]]},
         "holes": [{"x": 20, "y": 15, "d": 11}, {"x": 60, "y": 15, "d": 11}, {"x": 100, "y": 45, "d": 9}],
         "bends": [{"x1": 80, "y1": 0, "x2": 80, "y2": 30, "angle": 90, "dir": "UP"}]},
        {"mark": "R1", "kind": "strip", "name": "Letter return 'N'", "material": "Aluminium coil 1.0", "thickness": 1.0,
         "qty": 1, "process": "Channel-letter bender", "depth": 100, "segments": [400, 250, 400, 250], "angles": [90, 90, 90],
         "flange_back": 10},
    ],
}


class Out:
    def __init__(self):
        self.doc = ezdxf.new("R2010", setup=True)
        for n, c, lt in (("CUT", 1, "CONTINUOUS"), ("CUT-IN", 6, "CONTINUOUS"), ("DRILL", 3, "CONTINUOUS"),
                         ("BEND", 5, "DASHED"), ("ENGRAVE", 4, "CONTINUOUS"), ("NOTE", 7, "CONTINUOUS"), ("DIM", 8, "CONTINUOUS")):
            self.doc.layers.add(n, color=c, linetype=lt)
        self.msp = self.doc.modelspace()

    def poly(self, pts, layer="CUT", closed=True, ox=0, oy=0):
        self.msp.add_lwpolyline([(x + ox, y + oy) for x, y in pts], close=closed, dxfattribs={"layer": layer})

    def circle(self, x, y, d, ox=0, oy=0):
        self.msp.add_circle((x + ox, y + oy), d / 2, dxfattribs={"layer": "DRILL"})

    def line(self, p, q, layer="BEND", ox=0, oy=0):
        self.msp.add_line((p[0] + ox, p[1] + oy), (q[0] + ox, q[1] + oy), dxfattribs={"layer": layer})

    def text(self, s, x, y, h=5, layer="NOTE", ox=0, oy=0, align=TA.LEFT):
        self.msp.add_text(s, height=h, dxfattribs={"layer": layer}).set_placement((x + ox, y + oy), align=align)

    def dim(self, p1, p2, base, ox=0, oy=0, angle=0, h=5):
        d = self.msp.add_linear_dim(base=(base[0] + ox, base[1] + oy), p1=(p1[0] + ox, p1[1] + oy), p2=(p2[0] + ox, p2[1] + oy),
                                    angle=angle, dimstyle="EZDXF", override={"dimtxt": h, "dimasz": h * 0.7, "dimexe": h * 0.4, "dimexo": h * 0.3, "dimdec": 0, "dimrnd": 0.5, "dimlfac": 1.0}, dxfattribs={"layer": "DIM"})
        d.render()


def rounded_rect(w, h, r, seg=6):
    if r <= 0:
        return [(0, 0), (w, 0), (w, h), (0, h)]
    pts = []
    for cx, cy, a0 in ((w - r, r, -90), (w - r, h - r, 0), (r, h - r, 90), (r, r, 180)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def perimeter_holes(w, h, hp):
    e, d, mp = hp["edge"], hp["d"], hp["max_pitch"]
    holes = []
    for L, fixed, horiz in ((w, None, True), (h, None, False)):
        n = max(2, math.ceil((L - 2 * e) / mp) + 1)
        step = (L - 2 * e) / (n - 1)
        for i in range(n):
            t = e + i * step
            if horiz:
                holes += [{"x": t, "y": e, "d": d}, {"x": t, "y": h - e, "d": d}]
            elif 0 < i < n - 1:
                holes += [{"x": e, "y": t, "d": d}, {"x": w - e, "y": t, "d": d}]
    return holes


def geom(p):
    """Return dict: outline pts, inner contours, holes, bends, bbox, flat info, notes."""
    k = p["kind"]
    g = {"inner": [], "holes": list(p.get("holes", [])), "bends": [], "notes": [], "engrave": p.get("engrave", [])}
    if k == "plate":
        s = p["shape"]
        if s["type"] == "rect":
            g["outline"] = rounded_rect(s["w"], s["h"], s.get("corner_r", 0))
            w, h = s["w"], s["h"]
        else:
            g["outline"] = [tuple(v) for v in s["pts"]]
            xs, ys = [v[0] for v in s["pts"]], [v[1] for v in s["pts"]]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
        if p.get("hole_pattern"):
            g["holes"] += perimeter_holes(w, h, p["hole_pattern"])
        for sl in p.get("slots", []):
            g["inner"].append(rounded_rect(sl["w"], sl["h"], min(sl["w"], sl["h"]) / 2) if sl.get("round", True) else
                              [(0, 0), (sl["w"], 0), (sl["w"], sl["h"]), (0, sl["h"])])
            g["inner"][-1] = [(x + sl["x"], y + sl["y"]) for x, y in g["inner"][-1]]
        for b in p.get("bends", []):
            g["bends"].append(((b["x1"], b["y1"]), (b["x2"], b["y2"]), f"BEND {b.get('dir', 'UP')} {b.get('angle', 90)}°"))
        g["bbox"] = (w, h)
    elif k == "tray":
        W, H, F, T, R, K = p["W"], p["H"], p["F"], p["thickness"], p.get("R", p["thickness"]), p.get("K", 0.33)
        BA = math.pi / 2 * (R + K * T)
        OSSB = R + T
        BD = 2 * OSSB - BA
        a, b = W - 2 * OSSB, H - 2 * OSSB      # flat base between bend zones
        e = BA + (F - OSSB)                    # bend zone + flange flat
        # cross-shaped outline, origin at lower-left of the base flat zone
        g["outline"] = [(0, -e), (a, -e), (a, 0), (a + e, 0), (a + e, b), (a, b), (a, b + e), (0, b + e), (0, b), (-e, b), (-e, 0), (0, 0)]
        rd = p.get("relief_d", 0)
        if rd:
            g["holes"] += [{"x": x, "y": y, "d": rd, "note": "relief"} for x, y in ((0, 0), (a, 0), (a, b), (0, b))]
        h = BA / 2  # bend centre lines (middle of each bend allowance zone), offset outward from base flat
        g["bends"] = [((0, -h), (a, -h), "BEND UP 90°"), ((0, b + h), (a, b + h), "BEND UP 90°"),
                      ((-h, 0), (-h, b), "BEND UP 90°"), ((a + h, 0), (a + h, b), "BEND UP 90°")]
        # holes given in finished-base coordinates (from outside corner) -> flat coords
        g["holes"] = [dict(hh, x=hh["x"] - OSSB, y=hh["y"] - OSSB) if hh.get("note") != "relief" else hh for hh in g["holes"]]
        g["bbox"] = (a + 2 * e, b + 2 * e)
        g["shift"] = (e, e)
        g["flat"] = {"BA": round(BA, 3), "OSSB": round(OSSB, 3), "BD": round(BD, 3), "flat_W": round(a + 2 * e, 2),
                     "flat_H": round(b + 2 * e, 2), "check": round(W + 2 * F - 2 * BD, 2)}
        g["notes"].append(f"Flat {a + 2 * e:.1f} x {b + 2 * e:.1f} (BA {BA:.2f}, BD {BD:.2f}, R{R}, K{K}) — CALCULATED")
        g["notes"].append("Corners: open cross; seal/rivet corner tabs if watertightness required")
    elif k == "strip":
        T, Dp = p["thickness"], p["depth"]
        segs, angs = p["segments"], p.get("angles", [])
        R = p.get("R", T); K = p.get("K", 0.33)
        L = sum(segs)  # segments measured on the outside face of the letter outline
        corr = sum(-(2 * (R + T) * math.tan(math.radians(a) / 2) - math.pi * a / 180 * (R + K * T)) for a in angs)
        Lf = L + corr
        fb = p.get("flange_back", 0)
        hh = Dp + fb
        g["outline"] = [(0, 0), (Lf, 0), (Lf, hh), (0, hh)]
        x = 0
        for i, a in enumerate(angs):
            x += segs[i] + (-(2 * (R + T) * math.tan(math.radians(a) / 2) - math.pi * a / 180 * (R + K * T)))
            g["bends"].append(((x, 0), (x, hh), f"BEND {a}°"))
        if fb:
            g["bends"].append(((0, Dp), (Lf, Dp), f"FLANGE {fb} mm 90°"))
        g["bbox"] = (Lf, hh)
        g["flat"] = {"developed_length": round(Lf, 1), "outline_length": L, "correction": round(corr, 2)}
        g["notes"].append(f"Developed length {Lf:.1f} mm (outline {L} mm) — CALCULATED, confirm on bender")
    else:
        raise ValueError(k)
    return g


def draw_part(o, p, g, ox=0, oy=0, label=True):
    sx, sy = g.get("shift", (0, 0))
    ox, oy = ox + sx, oy + sy
    o.poly(g["outline"], "CUT", True, ox, oy)
    for c in g["inner"]:
        o.poly(c, "CUT-IN", True, ox, oy)
    for hh in g["holes"]:
        o.circle(hh["x"], hh["y"], hh["d"], ox, oy)
    for p1, p2, note in g["bends"]:
        o.line(p1, p2, "BEND", ox, oy)
        o.text(note, (p1[0] + p2[0]) / 2 + 3, (p1[1] + p2[1]) / 2 + 3, 4, "NOTE", ox, oy)
    for e in g["engrave"]:
        o.text(e["text"], e["x"], e["y"], e.get("h", 10), "ENGRAVE", ox, oy)
    if label:
        bw, bh = g["bbox"]
        xs = [v[0] for v in g["outline"]]; ys = [v[1] for v in g["outline"]]
        x0, y0, x1, y1 = min(xs) + ox, min(ys) + oy, max(xs) + ox, max(ys) + oy
        th = max(6, min(30, max(bw, bh) / 25))
        o.dim((x0, y0), (x1, y0), (x0, y0 - th * 2.5), h=th * 0.8)
        o.dim((x1, y0), (x1, y1), (x1 + th * 2.5, y0), angle=90, h=th * 0.8)
        o.text(f"{p['mark']} — {p['name']}", x0, y0 - th * 6, th)
        o.text(f"{p['material']} t={p['thickness']}  QTY {p['qty']}  {p.get('process', '')}", x0, y0 - th * 6 - th * 1.6, th * 0.7)
        for i, n in enumerate(g["notes"]):
            o.text(n, x0, y0 - th * 6 - th * 1.6 * (i + 2), th * 0.6)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", nargs="?"); ap.add_argument("-o", "--outdir", default="fab")
    ap.add_argument("--qto"); ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False)); return
    D = json.load(open(a.json, encoding="utf-8"))
    os.makedirs(os.path.join(a.outdir, "cnc"), exist_ok=True)
    sheet = Out()
    x_cursor, rows, pieces = 0.0, [], {}
    for p in D["parts"]:
        g = geom(p)
        one = Out(); draw_part(one, p, g, label=False)
        one.text(f"{p['mark']} {p['material']} t{p['thickness']} x{p['qty']}", 0, -20, 6, "NOTE")
        fn = os.path.join(a.outdir, "cnc", f"{D.get('drawing_no', 'FAB')}-{p['mark']}-t{p['thickness']}.dxf")
        one.doc.saveas(fn)
        assert not one.doc.audit().has_errors, fn
        draw_part(sheet, p, g, x_cursor, 0)
        bw, bh = g["bbox"]
        x_cursor += bw + max(150, bw * 0.15)
        cut_len = sum(math.dist(g["outline"][i], g["outline"][(i + 1) % len(g["outline"])]) for i in range(len(g["outline"])))
        cut_len += sum(math.pi * h_["d"] for h_ in g["holes"])
        rows.append([p["mark"], p["name"], p["material"], p["thickness"], round(bw, 1), round(bh, 1), p["qty"],
                     len(g["holes"]), len(g["bends"]), round(cut_len / 1000 * p["qty"], 2), p.get("process", ""), os.path.basename(fn),
                     json.dumps(g.get("flat", {}))])
        pieces.setdefault((p["material"], p["thickness"]), []).append({"w": round(bw), "h": round(bh), "n": p["qty"], "mark": p["mark"]})
    sheet.text(f"{D.get('project', '')} — {D.get('drawing_no', '')} {D.get('rev', '')} — FABRICATION PARTS (CALCULATED, verify before cutting)",
               0, max(r[5] for r in rows) + 120, 30)
    sp = os.path.join(a.outdir, f"{D.get('drawing_no', 'FAB')}-{D.get('rev', 'R0')}-parts.dxf")
    sheet.doc.saveas(sp)
    # preview PNG
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
        fig = plt.figure(figsize=(16, 9)); ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
        Frontend(RenderContext(sheet.doc), MatplotlibBackend(ax),
                 config=Configuration(background_policy=BackgroundPolicy.WHITE)).draw_layout(sheet.msp, finalize=True)
        fig.set_size_inches(16, 9); fig.savefig(sp.replace(".dxf", ".png"), dpi=120); plt.close(fig)
    except Exception as e:
        print("preview skipped:", e)
    # parts list
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Parts list"
    ws.append([D.get("project", ""), D.get("drawing_no", ""), D.get("rev", "")])
    ws.append(["Mark", "Name", "Material", "t mm", "Flat W mm", "Flat H mm", "Qty", "Holes", "Bends", "Cut length m (all qty)", "Process", "CNC file", "Flat-pattern data"])
    for c in ws[2]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="0F4C82")
    for r in rows: ws.append(r)
    ws.append([]); ws.append(["Status: CALCULATED. Confirm K-factor/bend deduction, kerf and tool offsets with the workshop. Nesting in CAM software."])
    for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 15
    xl = os.path.join(a.outdir, f"{D.get('drawing_no', 'FAB')}-{D.get('rev', 'R0')}-parts-list.xlsx"); wb.save(xl)
    print(f"{'Mark':5s}{'Name':22s}{'Material':22s}{'t':>5s}{'Flat W':>9s}{'Flat H':>9s}{'Qty':>5s}{'Cut m':>8s}")
    for r in rows:
        print(f"{r[0]:5s}{r[1][:21]:22s}{r[2][:21]:22s}{r[3]:5}{r[4]:9.1f}{r[5]:9.1f}{r[6]:5d}{r[9]:8.2f}  {r[12] if r[12] != '{}' else ''}")
    print("OUT:", sp, sp.replace(".dxf", ".png"), xl, os.path.join(a.outdir, "cnc/"), sep="\n  ")
    if a.qto:  # sheet items for qto.py nesting
        items = [{"id": f"FAB-{i+1}", "description": f"{m} t{t} — CNC parts", "unit": "sheet", "material": m,
                  "stock": [1220, 2440], "kerf_mm": 3, "allow_rotation": True, "pieces": pcs,
                  "source": f"{D.get('drawing_no')} {D.get('rev')}", "status": "CALCULATED"} for i, ((m, t), pcs) in enumerate(pieces.items())]
        json.dump({"project": {"name": D.get("project", ""), "sources": [D.get("drawing_no", "")]}, "items": items,
                   "assumptions": ["Stock 1220x2440 ASSUMED — set the real sheet size per material."], "conflicts": []},
                  open(a.qto, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print("  take-off JSON:", a.qto)


if __name__ == "__main__":
    main()
