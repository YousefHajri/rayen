#!/usr/bin/env python3
"""
RAYEN parametric shop-drawing generator (signage / panels / frames).

Writes an editable DXF (AutoCAD-ready, real-scale mm, layered) plus a PDF/PNG preview,
and optionally a take-off JSON for qto.py so drawing and BOQ stay consistent.

Usage:
  python3 shop_drawing.py spec.json -o SD-001            # -> SD-001.dxf, SD-001.pdf, SD-001.png
  python3 shop_drawing.py spec.json -o SD-001 --qto qto.json
  python3 shop_drawing.py --example lightbox > spec.json  # lightbox | pylon | graphic_frame

Model space is 1:1 in millimetres. The A3 sheet border and title block are drawn
around the views at the requested scale (e.g. 1:20 -> border 8400 x 5940 mm in model).
"""
import argparse
import json
import math
import re
import sys
from datetime import date

import ezdxf
from ezdxf.enums import TextEntityAlignment

EXAMPLES = {
    "lightbox": {
        "type": "lightbox",
        "project": "ALMAREEFA University — Interior Signage", "client": "Client",
        "title": "LIGHTBOX SIGN LB-01 — SHOP DRAWING", "drawing_no": "NT-SD-LB01", "rev": "R0",
        "scale": 10, "drawn_by": "RAYEN", "checked_by": "A. Abdalla",
        "width": 2400, "height": 800, "depth": 150,
        "frame": {"section": "RHS 40x20x1.5", "material": "Aluminum", "max_spacing": 600},
        "face": "Acrylic 5mm opal + printed vinyl", "returns": "ACP 4mm (RAL 9005)",
        "back": "Aluminum sheet 1.5mm", "lighting": "LED modules 12V @ 100mm grid, PSU in service bay",
        "fixing": "4 x M10 expansion anchors to RC wall — substrate TO BE CONFIRMED",
        "notes": ["All dimensions in mm unless noted.", "Verify all site dimensions before fabrication.",
                  "Electrical works by licensed electrician; IP65 outdoor components."]
    },
    "pylon": {
        "type": "pylon",
        "project": "Retail Park — Pylon P-01", "client": "Client",
        "title": "DOUBLE-SIDED PYLON SIGN P-01 — SHOP DRAWING", "drawing_no": "NT-SD-P01", "rev": "R0",
        "scale": 25, "drawn_by": "RAYEN", "checked_by": "A. Abdalla",
        "width": 1500, "height": 4500, "depth": 400,
        "frame": {"section": "SHS 100x100x4", "material": "Steel S275, HDG", "max_spacing": 800,
                  "rail_section": "RHS 60x40x3"},
        "face": "ACP 4mm + cut vinyl / push-through acrylic logo", "returns": "ACP 4mm",
        "base": {"plate": "PL 500x500x25", "anchors": "4 x M24 cast-in", "plinth_h": 300},
        "lighting": "Internal LED, PSU access door on side return",
        "fixing": "Base plate on RC foundation — FOUNDATION & WIND DESIGN BY STRUCTURAL ENGINEER (SBC 301)",
        "notes": ["MISSION-CRITICAL: structural calculation required before fabrication.",
                  "All steel hot-dip galvanized + 2 coat paint.", "Earthing per electrical spec."]
    },
    "graphic_frame": {
        "type": "graphic_frame",
        "project": "ALMAREEFA University — Basement", "client": "Client",
        "title": "GRAPHIC FRAME GF-01 — MAGNETIC FIXING DETAIL", "drawing_no": "NT-SD-GF01", "rev": "R0",
        "scale": 5, "drawn_by": "RAYEN", "checked_by": "A. Abdalla",
        "width": 1200, "height": 900, "depth": 30,
        "frame": {"section": "SHS 30x30x1.5", "material": "Aluminum, powder coated", "max_spacing": 9999},
        "face": "Acrylic 3mm clear over printed graphic", "returns": "—",
        "fixing": "Neodymium magnets embedded in EXISTING wood slats; steel plates on frame back",
        "notes": ["Existing wood slat positions TO BE CONFIRMED on site.", "Magnet pull force per supplier data."]
    }
}

LAYERS = {
    "A-OUTLINE": 7, "A-FRAME": 1, "A-FACE": 4, "A-HIDDEN": 8, "A-DIM": 3, "A-TEXT": 7,
    "A-TITLE": 7, "A-HATCH": 9, "A-CENTER": 2, "A-GROUND": 30,
}


def sec_dims(section):
    nums = [float(x) for x in re.findall(r"[\d.]+", section)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    return nums[0], nums[0]


def frame_envelope(spec):
    """Frame sits INSIDE the cladding returns: x0, z0 offsets and frame width/height.
    Pylon: verticals run down to the base plate (no bottom return), top under the cap."""
    ret = spec.get("returns") or "—"
    m = re.search(r"([\d.]+)\s*mm", ret)
    rt = float(m.group(1)) if (m and ret != "—") else 0.0
    W, H = spec["width"], spec["height"]
    if spec.get("type") == "pylon":
        return rt, 0.0, W - 2 * rt, H - rt, rt
    return rt, rt, W - 2 * rt, H - 2 * rt, rt


def member_positions(total, member, max_spacing):
    """centre-lines of members incl. both edges, spacing <= max_spacing."""
    clear = total - member
    n_bays = max(1, math.ceil(clear / max_spacing))
    return [member / 2 + i * clear / n_bays for i in range(n_bays + 1)]


class Sheet:
    def __init__(self, spec):
        self.s = spec
        self.k = float(spec.get("scale", 10))
        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = ezdxf.units.MM
        for name, color in LAYERS.items():
            lay = self.doc.layers.add(name, color=color)
            if name == "A-HIDDEN":
                lay.dxf.linetype = "DASHED"
            if name == "A-CENTER":
                lay.dxf.linetype = "CENTER"
        self.msp = self.doc.modelspace()
        self.txt = 2.5 * self.k  # 2.5 mm text on paper
        dim = self.doc.dimstyles.duplicate_entry("EZDXF", "RAYEN")
        dim.dxf.dimtxt = 2.5
        dim.dxf.dimasz = 2.0
        dim.dxf.dimexe = 1.25
        dim.dxf.dimexo = 1.0
        dim.dxf.dimgap = 0.8
        dim.dxf.dimscale = self.k
        dim.dxf.dimdec = 0
        dim.dxf.dimlfac = 1.0  # model is 1:1 mm
        self.cut = []  # cutting list rows

    # ---- primitives
    def rect(self, x, y, w, h, layer):
        self.msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True, dxfattribs={"layer": layer})

    def line(self, p1, p2, layer):
        self.msp.add_line(p1, p2, dxfattribs={"layer": layer})

    def text(self, s, x, y, h=None, layer="A-TEXT", align=TextEntityAlignment.LEFT):
        t = self.msp.add_text(s, height=h or self.txt, dxfattribs={"layer": layer, "style": "OpenSans"})
        t.set_placement((x, y), align=align)
        return t

    def hdim(self, x1, x2, y, base_y):
        d = self.msp.add_linear_dim(base=(x1, base_y), p1=(x1, y), p2=(x2, y), dimstyle="RAYEN",
                                    dxfattribs={"layer": "A-DIM"})
        d.render()

    def vdim(self, y1, y2, x, base_x):
        d = self.msp.add_linear_dim(base=(base_x, y1), p1=(x, y1), p2=(x, y2), angle=90, dimstyle="RAYEN",
                                    dxfattribs={"layer": "A-DIM"})
        d.render()

    def label(self, s, x, y, tx, ty):
        self.line((x, y), (tx, ty), "A-TEXT")
        self.msp.add_circle((x, y), radius=0.6 * self.k, dxfattribs={"layer": "A-TEXT"})
        self.text(s, tx + 1.0 * self.k, ty - self.txt / 2)

    # ---- views
    def elevation(self, ox, oy):
        s = self.s
        W, H = s["width"], s["height"]
        fw, fh = sec_dims(s["frame"]["section"])
        sp = s["frame"].get("max_spacing", 600)
        self.rect(ox, oy, W, H, "A-OUTLINE")
        # internal frame (hidden)
        x0, z0, Wf, Hf, rt = frame_envelope(s)
        xs = [x0 + v for v in member_positions(Wf, fw, sp)]
        ys = [z0 + v for v in member_positions(Hf, fw, sp)]
        for x in xs:
            self.rect(ox + x - fw / 2, oy, fw, H, "A-HIDDEN")
        for y in ys[1:-1] if len(ys) > 2 else []:
            self.line((ox, oy + y), (ox + W, oy + y), "A-HIDDEN")
        self.line((ox, oy + fw), (ox + W, oy + fw), "A-HIDDEN")
        self.line((ox, oy + H - fw), (ox + W, oy + H - fw), "A-HIDDEN")
        # centre lines
        self.line((ox + W / 2, oy - 3 * self.k), (ox + W / 2, oy + H + 3 * self.k), "A-CENTER")
        # dims
        self.hdim(ox, ox + W, oy, oy - 12 * self.k)
        self.vdim(oy, oy + H, ox, ox - 12 * self.k)
        if len(xs) > 2:
            for a, b in zip(xs[:-1], xs[1:]):
                self.hdim(ox + a, ox + b, oy + H, oy + H + 8 * self.k)
        self.text("FRONT ELEVATION", ox, oy - 22 * self.k, h=4 * self.k)
        self.text(f"SCALE 1:{int(self.k)}", ox, oy - 27 * self.k)
        # cutting list (frame)
        n_vert = len(xs)
        n_hor = 2 + max(0, len(ys) - 2)
        hor_len = W - 2 * fw if True else W
        self.cut.append({"mark": "F1", "desc": "Vertical member", "section": s["frame"]["section"],
                         "material": s["frame"]["material"], "length": round(Hf, 1), "qty": n_vert * (2 if s["type"] == "pylon" and s.get("depth", 0) > 2 * fw else 1)})
        self.cut.append({"mark": "F2", "desc": "Horizontal member (between verticals)", "section": s["frame"].get("rail_section", s["frame"]["section"]),
                         "material": s["frame"]["material"], "length": round((Wf - n_vert * fw) / max(1, n_vert - 1), 1),
                         "qty": n_hor * (n_vert - 1) * (2 if s["type"] == "pylon" and s.get("depth", 0) > 2 * fw else 1)})
        return xs, ys

    def section(self, ox, oy):
        s = self.s
        H, D = s["height"], s["depth"]
        fw, fh = sec_dims(s["frame"]["section"])
        face_t = 5 if "5mm" in s.get("face", "") else 3 if "3mm" in s.get("face", "") else 4
        self.rect(ox, oy, D, H, "A-OUTLINE")
        # face
        self.rect(ox + D - face_t, oy, face_t, H, "A-FACE")
        self.msp.add_hatch(color=9, dxfattribs={"layer": "A-HATCH"}).paths.add_polyline_path(
            [(ox + D - face_t, oy), (ox + D, oy), (ox + D, oy + H), (ox + D - face_t, oy + H)], is_closed=True)
        # frame members (back and, for deep boxes, front)
        self.rect(ox, oy, fh, H, "A-FRAME")
        if D > 2 * fh + 20 and s["type"] != "graphic_frame":
            self.rect(ox + D - face_t - fh, oy, fh, H, "A-FRAME")
        # dims
        self.hdim(ox, ox + D, oy, oy - 12 * self.k)
        self.vdim(oy, oy + H, ox + D, ox + D + 12 * self.k)
        # labels
        top = oy + H
        self.label(s.get("face", "FACE"), ox + D - face_t / 2, top - 0.15 * H, ox + D + 25 * self.k, top - 0.10 * H)
        self.label(f"FRAME {s['frame']['section']} {s['frame']['material']}", ox + fh / 2, top - 0.35 * H,
                   ox + D + 25 * self.k, top - 0.30 * H)
        if s.get("returns") and s["returns"] != "—":
            self.label(f"RETURNS: {s['returns']}", ox + D / 2, oy + H, ox + D + 25 * self.k, top - 0.50 * H)
        if s.get("lighting"):
            self.label(f"LIGHTING: {s['lighting']}", ox + D / 2, oy + 0.5 * H, ox + D + 25 * self.k, top - 0.70 * H)
        self.text("SECTION A-A", ox, oy - 22 * self.k, h=4 * self.k)
        self.text(f"SCALE 1:{int(self.k)}", ox, oy - 27 * self.k)

    def base(self, ox, oy):
        b = self.s.get("base")
        if not b:
            return
        pw = sec_dims(b["plate"])[0]
        ph = b.get("plinth_h", 300)
        W = self.s["width"]
        # ground line + plinth
        self.line((ox - 200, oy), (ox + W + 200, oy), "A-GROUND")
        for i in range(12):
            x = ox - 200 + i * (W + 400) / 12
            self.line((x, oy), (x - 60, oy - 60), "A-GROUND")
        self.text(f"BASE PLATE {b['plate']} + {b['anchors']}", ox, oy - 33 * self.k)
        self.text("FOUNDATION BY STRUCTURAL ENGINEER", ox, oy - 37 * self.k)

    def title_block(self, x0, y0):
        k, s = self.k, self.s
        PW, PH = 420 * k, 297 * k
        m = 10 * k
        self.rect(x0, y0, PW, PH, "A-TITLE")
        self.rect(x0 + m, y0 + m, PW - 2 * m, PH - 2 * m, "A-TITLE")
        tbw, tbh = 180 * k, 55 * k
        tx, ty = x0 + PW - m - tbw, y0 + m
        self.rect(tx, ty, tbw, tbh, "A-TITLE")
        rows = [("NEWTECH — TECHNICAL OFFICE", 5), (s.get("project", ""), 3.5), (s.get("title", ""), 3.5)]
        yy = ty + tbh - 9 * k
        for t, h in rows:
            self.text(t[:70], tx + 3 * k, yy, h=h * k, layer="A-TITLE")
            yy -= (h + 3.5) * k
        self.line((tx, ty + 22 * k), (tx + tbw, ty + 22 * k), "A-TITLE")
        cells = [("DWG No.", s.get("drawing_no", "")), ("REV", s.get("rev", "")), ("SCALE", f"1:{int(k)} @A3"),
                 ("DATE", s.get("date", date.today().isoformat())), ("DRAWN", s.get("drawn_by", "")),
                 ("CHECKED", s.get("checked_by", "")), ("CLIENT", s.get("client", "")), ("STATUS", s.get("status", "FOR APPROVAL"))]
        cw = tbw / 4
        for i, (a, v) in enumerate(cells):
            cx = tx + (i % 4) * cw
            cy = ty + (11 * k if i < 4 else 0)
            self.rect(cx, cy, cw, 11 * k, "A-TITLE")
            self.text(a, cx + 1.5 * k, cy + 7 * k, h=1.8 * k, layer="A-TITLE")
            self.text(str(v)[:22], cx + 1.5 * k, cy + 2 * k, h=2.5 * k, layer="A-TITLE")
        return x0 + m, y0 + m, PW - 2 * m, PH - 2 * m, tx, ty, tbw, tbh

    def schedule(self, x, y):
        k, s = self.k, self.s
        self.text("MATERIAL / CUTTING SCHEDULE", x, y, h=3.5 * k)
        y -= 6 * k
        cols = [("MARK", 14), ("DESCRIPTION", 60), ("SECTION", 34), ("MATERIAL", 38), ("LENGTH", 18), ("QTY", 12)]
        rows = self.cut + [{"mark": "P1", "desc": "Face panel", "section": "-", "material": s.get("face", ""),
                            "length": f"{s['width']}x{s['height']}", "qty": 2 if s["type"] == "pylon" else 1}]
        for r_i, row in enumerate([None] + rows):
            cx = x
            for (name, cw), key in zip(cols, ["mark", "desc", "section", "material", "length", "qty"]):
                self.rect(cx, y - 1.5 * k, cw * k, 6 * k, "A-TITLE")
                val = name if row is None else str(row[key])
                self.text(val[: int(cw / 1.55)], cx + 1.2 * k, y, h=2.2 * k)
                cx += cw * k
            y -= 6 * k

    def notes(self, x, y_bottom):
        k, s = self.k, self.s
        notes = list(s.get("notes", []))
        if s.get("fixing"):
            notes.insert(0, f"FIXING: {s['fixing']}")
        if s["type"] == "pylon":
            notes.append("Depth cross-members and bracing TO BE DETAILED after structural design.")
        lines = []
        for i, n in enumerate(notes, 1):
            words, cur = f"{i}. {n}".split(), ""
            for w in words:
                if len(cur) + len(w) + 1 > 78:
                    lines.append(cur); cur = "   " + w
                else:
                    cur = (cur + " " + w).strip() if not cur.startswith("   ") or cur.strip() else cur + w
            lines.append(cur)
        y = y_bottom + (len(lines)) * 4.2 * k
        self.text("GENERAL NOTES", x, y + 2 * k, h=3.5 * k)
        for ln in lines:
            y -= 4.2 * k
            self.text(ln, x, y, h=2.2 * k)


STD_SCALES = [5, 10, 15, 20, 25, 50, 75, 100, 125, 150, 200]


def fit_scale(spec):
    """Smallest standard scale >= requested at which elevation + section + labels fit on A3."""
    req = float(spec.get("scale", 10))
    W, H, D = spec["width"], spec["height"], spec["depth"]
    for k in [x for x in STD_SCALES if x >= req] or [STD_SCALES[-1]]:
        if (W + D) / k <= 230 and H / k <= 150:
            return k
    return STD_SCALES[-1]


def build(spec, out):
    k_fit = fit_scale(spec)
    if k_fit != float(spec.get("scale", 10)):
        print(f"NOTE: scale changed 1:{spec.get('scale')} -> 1:{k_fit} to fit A3", file=sys.stderr)
        spec = dict(spec, scale=k_fit)
    sh = Sheet(spec)
    k = sh.k
    W, H, D = spec["width"], spec["height"], spec["depth"]
    ix, iy, iw, ih, tx, ty, tbw, tbh = sh.title_block(0.0, 0.0)
    ex = ix + 30 * k
    ey = iy + ih - 22 * k - H
    sh.elevation(ex, ey)
    if spec["type"] == "pylon":
        sh.base(ex, ey)
    sh.section(ex + W + 45 * k, ey)
    sh.schedule(ix + 20 * k, iy + 70 * k)
    sh.notes(tx, ty + tbh + 8 * k)
    dxf_path = f"{out}.dxf"
    sh.doc.saveas(dxf_path)
    # preview
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
        fig = plt.figure(figsize=(16.54, 11.69))
        ax = fig.add_axes([0, 0, 1, 1])
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
        Frontend(RenderContext(sh.doc), MatplotlibBackend(ax), config=cfg).draw_layout(sh.msp, finalize=True)
        fig.savefig(f"{out}.pdf")
        fig.savefig(f"{out}.png", dpi=110)
        plt.close(fig)
    except Exception as e:  # preview is optional
        print(f"Preview skipped: {e}", file=sys.stderr)
    return sh


def to_qto(spec, sh):
    items = []
    for i, c in enumerate(sh.cut, 1):
        if c["qty"] <= 0:
            continue
        items.append({"id": f"1.{i}", "description": f"{c['desc']} ({c['mark']})", "material": c["material"],
                      "section": c["section"], "unit": "kg", "length_m": round(c["length"] / 1000, 3),
                      "count": c["qty"], "waste_pct": 5 if "steel" in c["material"].lower() else 7,
                      "source": f"{spec.get('drawing_no')} {spec.get('rev')} cutting schedule", "status": "CALCULATED"})
    faces = 2 if spec["type"] == "pylon" else 1
    items.append({"id": "2.1", "description": "Face panel", "material": spec.get("face", ""), "unit": "sheet",
                  "stock": [1220, 2440], "kerf_mm": 3, "allow_rotation": True,
                  "pieces": [{"w": spec["width"], "h": spec["height"], "n": faces}] if max(spec["width"], spec["height"]) <= 2440 and min(spec["width"], spec["height"]) <= 1220 else [],
                  "waste_pct": 0, "source": f"{spec.get('drawing_no')} elevation", "status": "CALCULATED"})
    if not items[-1]["pieces"]:
        items[-1] = {"id": "2.1", "description": "Face panel (exceeds one sheet — joint layout required)",
                     "material": spec.get("face", ""), "unit": "m2", "length_m": spec["width"] / 1000,
                     "width_m": spec["height"] / 1000, "count": faces, "waste_pct": 15,
                     "source": f"{spec.get('drawing_no')} elevation; joints TO BE CONFIRMED", "status": "ASSUMED"}
    return {"project": {"name": spec.get("project"), "client": spec.get("client"), "ref": spec.get("drawing_no") + "-QTO",
                        "revision": spec.get("rev"), "prepared_by": "RAYEN", "currency": "SAR",
                        "sources": [f"{spec.get('drawing_no')} {spec.get('rev')}"]},
            "items": items, "conflicts": [], "assumptions": ["Rates not included — add supplier rates."]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?")
    ap.add_argument("-o", "--out", default="SHOP-DRAWING")
    ap.add_argument("--qto", help="write take-off JSON for qto.py")
    ap.add_argument("--example", choices=list(EXAMPLES))
    a = ap.parse_args()
    if a.example:
        json.dump(EXAMPLES[a.example], sys.stdout, indent=2, ensure_ascii=False)
        return
    if not a.spec:
        ap.error("spec JSON required (or --example TYPE)")
    spec = json.load(open(a.spec, encoding="utf-8"))
    sh = build(spec, a.out)
    print(f"DXF: {a.out}.dxf  | preview: {a.out}.pdf / {a.out}.png")
    print("Cutting schedule:")
    for c in sh.cut:
        print(f"  {c['mark']}: {c['desc']} — {c['section']} {c['material']} L={c['length']} mm x {c['qty']}")
    if a.qto:
        json.dump(to_qto(spec, sh), open(a.qto, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"Take-off JSON: {a.qto}")


if __name__ == "__main__":
    main()
