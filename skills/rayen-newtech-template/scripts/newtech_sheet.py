#!/usr/bin/env python3
"""Newtech drawing-set composer — puts RAYEN drawings into the ORIGINAL approved Newtech identity.

Identity source (VERIFIED from Drive: "عرض_مخططات_السور_المعدني_قالب_نيوتك_الأصلي_المعتمد.pdf", Oct 2026):
16:9 sheet 1382x778 pt · logo "Пewtech" + "مصنع نيوتك للوحات الإعلانية والشاشات" + "Newtech Factory for
Billboards and Screens" · primary blue #0F4C82 · heading blue #00679F · DWG label gold #FFD158 · subtitle
orange #DE5200 · right side panels (تعديلات التصميم / تفاصيل أمر العمل / تفاصيل التصميم / عدد الجونت) ·
title bar · light content box #EBEFF2 · ticker footer · cover page and THANK YOU closing page.

  python3 newtech_sheet.py package.json -o "<WO>-Drawings.pdf" [--png] [--dxf-frame frame.dxf]
  python3 newtech_sheet.py --example

Views placed in a sheet: image (PNG/JPG render or drawing), dxf (vector, any layers can be hidden),
table (rows), notes (spec lines). Arabic is shaped automatically (arabic-reshaper + python-bidi).
"""
import argparse, json, os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

BLUE, HEAD, GOLD, ORANGE, RED, TEAL = "#0F4C82", "#00679F", "#FFD158", "#DE5200", "#D42F35", "#0075A7"
GREY_ROW, BOX, TICK, DARK, MID = "#EAEAEA", "#EBEFF2", "#B5BEC5", "#2B2B2B", "#555555"
W, H = 1152.0, 648.0  # layout units (16:9); page = 19.2 x 10.8 in
FONT = "DejaVu Sans"
HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # still works, Arabic will be unshaped
    arabic_reshaper = None


_MPL_BIDI = tuple(int(x) for x in matplotlib.__version__.split(".")[:2]) >= (3, 11)  # libraqm shaping + bidi


def _has_ar(s):
    return any("\u0600" <= c <= "\u06ff" for c in s)


def ar_visual(s):
    """Visual-order shaped Arabic for renderers without bidi (AutoCAD TEXT, old matplotlib)."""
    s = "" if s is None else str(s)
    if arabic_reshaper and _has_ar(s):
        return get_display(arabic_reshaper.reshape(s))
    return s


def ar(s):
    s = "" if s is None else str(s)
    return s if _MPL_BIDI else ar_visual(s)


EXAMPLE = {
    "project": {
        "name": "مشروع لوحة واجهة مضيئة — فرع العليا",
        "subtitle": "طريق الملك فهد - الرياض",
        "description": "المخططات التنفيذية وتفاصيل التصنيع والتركيب",
        "client": "CLIENT NAME", "client_logo": "",
        "location": "العليا - الرياض", "category": "لوحات مضيئة", "units": "mm",
        "designer": "عبدالقادر عبدالله", "sales_rep": "TO BE CONFIRMED", "wo_no": "WO-2026-XX01",
        "joints": "—", "revisions": [["2026/11/19", "R0 — للاعتماد"]],
        "cover_rows": [["المالك / العميل:", "CLIENT NAME"], ["الموقع:", "العليا - الرياض"],
                       ["الأبعاد:", "2400 × 800 × 150 مم"], ["النظام:", "إطار ألمنيوم + ACP 4مم + وجه أكريليك + LED"],
                       ["فريق الإعداد:", "المصمم: عبدالقادر عبدالله | التاريخ: نوفمبر 2026"]],
        "ticker": "مشروع لوحة واجهة مضيئة • مصنع نيوتك للوحات الإعلانية والشاشات"
    },
    "sheets": [
        {"dwg": "DWG-01: SHOP-DRAWING", "heading": "المواصفات", "title": "المخطط التنفيذي للوحة المضيئة LB-01",
         "views": [{"type": "dxf", "file": "NT-SD-LB01-R0.dxf", "box": [0.0, 0.0, 1.0, 1.0], "hide_layers": ["A-TITLE"]}]},
        {"dwg": "DWG-02: 3D-VISUALIZATION", "heading": "التصميم", "title": "المنظور ثلاثي الأبعاد (تصوّر مبدئي)",
         "views": [{"type": "image", "file": "render.png", "box": [0.0, 0.12, 1.0, 1.0], "caption": "CONCEPTUAL — ليس للتنفيذ"}],
         "notes": ["المواد والألوان النهائية حسب العينات المعتمدة."]}
    ],
    "cover": True, "closing": True
}


class Page:
    def __init__(self, pdf):
        self.fig = plt.figure(figsize=(19.2, 10.8), dpi=150)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(H, 0); self.ax.axis("off")
        self.pdf = pdf
        self.prims = []  # for DXF frame export

    def rect(self, x0, y0, x1, y1, fc="none", ec="none", lw=0.8):
        self.ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fc, edgecolor=ec, lw=lw))
        self.prims.append(("rect", x0, y0, x1, y1, fc, ec))

    def text(self, x, y, s, size=9, color=DARK, weight="normal", ha="left", va="center", rot=0):
        self.ax.text(x, y, ar(s), fontsize=size, color=color, weight=weight, ha=ha, va=va, rotation=rot, family=FONT)
        self.prims.append(("text", x, y, ar_visual(s), size, color, ha, rot))

    def line(self, x0, y0, x1, y1, color=TICK, lw=0.8, ls="-"):
        self.ax.plot([x0, x1], [y0, y1], color=color, lw=lw, ls=ls)
        self.prims.append(("line", x0, y0, x1, y1, color))

    def frac_axes(self, x0, y0, x1, y1):
        f = self.fig
        return f.add_axes([x0 / W, 1 - y1 / H, (x1 - x0) / W, (y1 - y0) / H])

    def save(self, pngs=None, name=None):
        self.pdf.savefig(self.fig)
        if pngs is not None:
            self.fig.savefig(name, dpi=100); pngs.append(name)
        plt.close(self.fig)


def logo(pg, x, y, scale=1.0, ha="left"):
    pg.text(x, y, "Пewtech", 34 * scale, BLUE, "bold", ha)
    pg.text(x if ha == "left" else x, y + 25 * scale, "مصنع نيوتك للوحات الإعلانية والشاشات", 10.5 * scale, BLUE, "bold", ha)
    pg.text(x, y + 38 * scale, "Newtech Factory for Billboards and Screens", 8 * scale, MID, "normal", ha)


def brand_band(pg, contacts):
    pg.rect(1072, 8, 1143, 640, BLUE)
    pg.text(1107, 320, "NEWTECH FACTORY", 17, "#EAF2FA", "bold", "center", rot=90)
    pg.rect(8, 595, 1143, 638, BLUE)
    step = 1000 / len(contacts)
    for i, c in enumerate(contacts):
        pg.text(55 + i * step, 616, "•  " + c, 8.5, "white", "bold")


def panel(pg, y, title, rows, two_col_head=None):
    x0, x1 = 962, 1118
    pg.rect(x0, y, x1, y + 13, BLUE)
    pg.text((x0 + x1) / 2, y + 6.5, title, 7.5, "white", "bold", "center")
    yy = y + 13
    if two_col_head:
        pg.rect(x0, yy, x1, yy + 10, GREY_ROW)
        pg.text(x1 - 40, yy + 5, two_col_head[0], 6, DARK, "bold", "center")
        pg.text(x0 + 38, yy + 5, two_col_head[1], 6, DARK, "bold", "center")
        yy += 10
    for i, (a, b) in enumerate(rows):
        pg.rect(x0, yy, x1, yy + 10.5, "#F7F9FB" if i % 2 else "white", "#DDE3EA", 0.4)
        if two_col_head:
            pg.line((x0 + x1) / 2, yy, (x0 + x1) / 2, yy + 10.5, "#DDE3EA", 0.4)
            pg.text(x1 - 40, yy + 5.2, a, 5.8, DARK, "normal", "center")
            pg.text(x0 + 38, yy + 5.2, b, 5.8, DARK, "normal", "center")
        else:
            pg.text(x1 - 3, yy + 5.2, a, 6, DARK, "bold", "right")
            pg.text(x0 + 3, yy + 5.2, b, 6, BLUE if i == 0 else DARK, "bold" if i == 0 else "normal", "left")
        yy += 10.5
    return yy


def sidebar(pg, P, page_no, total):
    logo(pg, 1040, 33, 0.5, "center")
    revs = P.get("revisions") or [["—", "—"]]
    revs = (revs + [["---", "---"]] * 5)[:5]
    panel(pg, 82, "تعديلات التصميم", revs, ("التاريخ", "عدد مرات التعديل"))
    panel(pg, 172, "تفاصيل أمر العمل", [["اسم العميل:", P.get("client", "")], ["الموقع:", P.get("location", "")],
                                       ["التصنيف:", P.get("category", "")], ["وحدة القياس:", P.get("units", "mm")]])
    panel(pg, 262, "تفاصيل التصميم", [["المصمم:", P.get("designer", "")], ["مندوب البيع:", P.get("sales_rep", "")],
                                      ["عدد الصفحات:", f"{page_no:02d} / {total:02d}"],
                                      ["عدد مرات التعديلات والمراجعات:", str(max(0, len(P.get("revisions", [])) - 1))],
                                      ["رقم أمر العمل:", P.get("wo_no", "")]])
    pg.rect(962, 352, 1118, 365, BLUE)
    pg.text(1040, 358.5, "عدد الجونت", 7.5, "white", "bold", "center")
    pg.rect(962, 365, 1118, 388, "white", "#DDE3EA", 0.5)
    pg.text(1040, 376.5, P.get("joints", "—"), 14, BLUE, "bold", "center")
    if P.get("status"):
        pg.rect(962, 400, 1118, 420, "white", ORANGE, 1.0)
        pg.text(1040, 410, P["status"], 8, ORANGE, "bold", "center")


def place_image(pg, v, bx):
    from PIL import Image
    im = Image.open(v["file"])
    x0, y0, x1, y1 = bx
    bw, bh = x1 - x0, y1 - y0
    r = min(bw / im.width, bh / im.height * (1.0))
    # keep aspect in layout units (layout is isotropic: 1152x648 on 19.2x10.8in)
    w, h = im.width * r, im.height * r
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax = pg.frac_axes(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    ax.imshow(im); ax.axis("off")


def place_dxf(pg, v, bx):
    import ezdxf
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
    doc = ezdxf.readfile(v["file"])
    msp = doc.modelspace()
    hide = set(v.get("hide_layers", []))
    if hide:
        for e in list(msp):
            if e.dxf.get("layer", "0") in hide:
                msp.delete_entity(e)
    ax = pg.frac_axes(*bx)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK,
                        lineweight_scaling=v.get("lineweight", 0.6))
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=True)
    pg.fig.set_size_inches(19.2, 10.8)  # ezdxf finalize may resize the figure
    ax.set_position([bx[0] / W, 1 - bx[3] / H, (bx[2] - bx[0]) / W, (bx[3] - bx[1]) / H])
    ax.set_facecolor("white"); ax.axis("off")


def place_table(pg, v, bx):
    rows = v["rows"]
    x0, y0, x1, y1 = bx
    n = len(rows); cols = len(rows[0])
    rh = min(16, (y1 - y0) / max(1, n))
    widths = v.get("widths") or [1 / cols] * cols
    xs = [x0]
    for w_ in widths: xs.append(xs[-1] + w_ * (x1 - x0))
    for i, r in enumerate(rows):
        yy = y0 + i * rh
        pg.rect(x0, yy, x1, yy + rh, BLUE if i == 0 else ("#F7F9FB" if i % 2 else "white"), "#C9D6E2", 0.4)
        for j, c in enumerate(r):
            rtl = v.get("rtl", True)
            cx = xs[cols - 1 - j] if rtl else xs[j]
            cw = xs[cols - j] - xs[cols - 1 - j] if rtl else xs[j + 1] - xs[j]
            pg.text(cx + cw / 2, yy + rh / 2, c, 7 if i else 7.5, "white" if i == 0 else DARK, "bold" if i == 0 else "normal", "center")


def content_sheet(pg, S, P, page_no, total):
    pg.text(50, 38, S.get("heading", "المواصفات"), 22, HEAD, "bold")
    pg.rect(47, 69, 945, 90, BLUE)
    pg.text(67, 79.5, S.get("title", ""), 12, "white", "bold")
    pg.text(925, 79.5, S.get("dwg", ""), 11, GOLD, "bold", "right")
    notes = S.get("notes", [])
    nb = 18 + 13 * len(notes) if notes else 0
    pg.rect(60, 100, 933, 572, BOX, "#C9D3DC", 0.6)
    cx0, cy0, cx1, cy1 = 66, 106, 927, 566 - nb
    for v in S.get("views", []):
        b = v.get("box", [0, 0, 1, 1])
        bx = (cx0 + b[0] * (cx1 - cx0), cy0 + b[1] * (cy1 - cy0), cx0 + b[2] * (cx1 - cx0), cy0 + b[3] * (cy1 - cy0))
        if v.get("caption") and v["type"] != "table":
            bx = (bx[0], bx[1], bx[2], bx[3] - 16)  # room for caption under the view
        if v["type"] in ("image", "dxf") and not os.path.exists(v["file"]):
            pg.text((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, f"MISSING FILE: {v['file']}", 12, RED, "bold", "center")
            print("  ! missing", v["file"]); continue
        {"image": place_image, "dxf": place_dxf, "table": place_table}[v["type"]](pg, v, bx)
        if v.get("caption"):
            pg.text((bx[0] + bx[2]) / 2, bx[1] - 6 if v["type"] == "table" else bx[3] + 9, v["caption"], 9, BLUE, "bold", "center")
    if notes:
        y = 566 - nb + 6
        pg.line(66, y - 3, 927, y - 3, "#C9D3DC")
        pg.text(925, y + 5, "الملاحظات والمواصفات:", 9, BLUE, "bold", "right")
        for i, n in enumerate(notes):
            pg.text(925, y + 18 + 13 * i, f"{i + 1}. {n}", 7.8, DARK, "normal", "right")
    t = P.get("ticker", P.get("name", ""))
    pg.line(30, 612, 1120, 612, "#D5DDE5", 0.6)
    pg.text(576, 621, "  •  ".join([t] * 2), 6.5, TICK, "normal", "center")
    sidebar(pg, P, page_no, total)


def cover(pg, P, contacts):
    logo(pg, 65, 75, 1.0)
    if P.get("client_logo") and os.path.exists(P["client_logo"]):
        place_image(pg, {"file": P["client_logo"]}, (100, 200, 400, 305))
    else:
        pg.text(140, 260, P.get("client", ""), 30, "#5B2C83" if not P.get("client_color") else P["client_color"], "bold")
    pg.text(480, 362, P.get("name", ""), 19, BLUE, "bold", "center")
    pg.text(480, 395, P.get("subtitle", ""), 13, ORANGE, "bold", "center")
    pg.text(480, 425, P.get("description", ""), 11, DARK, "normal", "center")
    rows = P.get("cover_rows", [])
    if rows:
        pg.rect(110, 452, 948, 452 + 17 * len(rows) + 14, "#F2F6F9", "#C9D6E2", 0.6)
        for i, (a, b) in enumerate(rows):
            y = 467 + 17 * i
            pg.text(240, y, a, 8, BLUE, "bold", "right")
            pg.text(600, y, b, 8, DARK, "normal", "center")
    brand_band(pg, contacts)


def closing(pg, P, contacts):
    logo(pg, 86, 85, 1.0)
    pg.text(140, 380, "شكراً لكم", 42, BLUE, "bold")
    pg.text(140, 432, "THANK YOU", 36, BLUE, "bold")
    # 25-years billboard (positions measured from the approved closing page)
    pg.rect(688, 232, 938, 335, "none", TEAL, 4)
    pg.text(698, 283, P.get("years", "25"), 44, TEAL, "bold")
    pg.text(838, 262, "عاماً من الخبرة", 13, BLUE, "bold", "center")
    pg.text(838, 283, "في صناعة الإعلانات", 11, BLUE, "bold", "center")
    pg.text(838, 303, "IN ADVERTISING", 8.5, MID, "bold", "center")
    pg.line(742, 335, 742, 486, TEAL, 5); pg.line(884, 335, 884, 486, TEAL, 5)
    pg.text(522, 553, "نرجو المراجعة والتدقيق على كافة البيانات والأخطاء الإملائية والعناوين والأرقام والأبعاد قبل التعميد النهائي للطباعة أو التصنيع بالمصنع",
            11.5, RED, "bold", "center")
    pg.text(196, 552, "⚠", 16, ORANGE, "bold", "center")
    brand_band(pg, contacts)


def export_dxf_frame(prims, path, sheet_w=488.0):
    """Write the identity frame as DXF (1:1 mm, sheet 488 x 274.5 mm) for AutoCAD layouts."""
    import ezdxf
    k = sheet_w / W
    doc = ezdxf.new("R2018", setup=True); msp = doc.modelspace()
    for n, c in (("NT-FRAME", 5), ("NT-FILL", 254), ("NT-TEXT", 7)):
        doc.layers.add(n, color=c)
    doc.styles.add("NT", font="DejaVuSans.ttf")
    for p in prims:
        if p[0] == "rect":
            _, x0, y0, x1, y1, fc, ec = p
            pts = [(x0 * k, (H - y0) * k), (x1 * k, (H - y0) * k), (x1 * k, (H - y1) * k), (x0 * k, (H - y1) * k)]
            if fc not in ("none", "white"):
                h = msp.add_hatch(dxfattribs={"layer": "NT-FILL"}); h.paths.add_polyline_path(pts, is_closed=True)
                h.rgb = tuple(int(fc.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "NT-FRAME"})
        elif p[0] == "line":
            _, x0, y0, x1, y1, c = p
            msp.add_line((x0 * k, (H - y0) * k), (x1 * k, (H - y1) * k), dxfattribs={"layer": "NT-FRAME"})
        else:
            _, x, y, s, size, color, ha, rot = p
            if not s.strip():
                continue
            t = msp.add_text(s, height=size * 0.32 * k * 1.9, rotation=rot, dxfattribs={"layer": "NT-TEXT", "style": "NT"})
            t.rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if color.startswith("#") else (255, 255, 255)
            from ezdxf.enums import TextEntityAlignment as A
            t.set_placement((x * k, (H - y) * k), align={"left": A.MIDDLE_LEFT, "right": A.MIDDLE_RIGHT, "center": A.MIDDLE_CENTER}[ha])
    doc.saveas(path); print("  DXF frame:", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package", nargs="?"); ap.add_argument("-o", "--out", default="Newtech-Drawings.pdf")
    ap.add_argument("--png", action="store_true", help="also save one PNG per page")
    ap.add_argument("--dxf-frame", help="export the content-sheet identity frame as DXF")
    ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False)); return
    if not a.package:
        ap.error("package JSON required")
    D = json.load(open(a.package, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.package))
    for S in D.get("sheets", []):
        for v in S.get("views", []):
            if "file" in v and not os.path.isabs(v["file"]):
                v["file"] = os.path.join(base, v["file"])
    P = D["project"]
    if P.get("client_logo") and not os.path.isabs(P["client_logo"]):
        P["client_logo"] = os.path.join(base, P["client_logo"])
    contacts = D.get("contacts", ["newtechadv", "newtechsa1", "www.nt.com.sa", "sales@nt.com.sa", "+966 544 415 004"])
    sheets = D.get("sheets", [])
    total = len(sheets) + int(D.get("cover", True)) + int(D.get("closing", True))
    pngs = [] if a.png else None
    stem = os.path.splitext(a.out)[0]
    frame_prims = None
    with PdfPages(a.out) as pdf:
        n = 0
        if D.get("cover", True):
            n += 1; pg = Page(pdf); cover(pg, P, contacts); pg.save(pngs, f"{stem}_p{n:02d}.png")
        for S in sheets:
            n += 1; pg = Page(pdf); content_sheet(pg, S, P, n, total)
            if frame_prims is None:
                frame_prims = pg.prims
            pg.save(pngs, f"{stem}_p{n:02d}.png")
        if D.get("closing", True):
            n += 1; pg = Page(pdf); closing(pg, P, contacts); pg.save(pngs, f"{stem}_p{n:02d}.png")
    print(f"PDF: {a.out} ({n} pages)")
    if pngs:
        print("PNG:", *pngs, sep="\n  ")
    if a.dxf_frame and frame_prims:
        export_dxf_frame(frame_prims, a.dxf_frame)


if __name__ == "__main__":
    main()
