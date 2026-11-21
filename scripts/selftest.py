#!/usr/bin/env python3
"""RAYEN self-test: checks packages and runs every generator on its example into ./_selftest."""
import importlib, os, subprocess, sys, tempfile, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = lambda *p: os.path.join(ROOT, "skills", *p)
pk = ["ezdxf", "openpyxl", "docx", "matplotlib", "PIL", "numpy", "ifcopenshell", "arabic_reshaper", "bidi", "pymupdf", "bpy"]
print("Packages:")
for m in pk:
    try:
        importlib.import_module(m); print(f"  OK   {m}")
    except Exception:
        print(f"  --   {m}" + ("  (optional: renders fall back to massing preview)" if m == "bpy" else "  MISSING"))
out = os.path.join(ROOT, "_selftest"); os.makedirs(out, exist_ok=True)
def run(name, args):
    r = subprocess.run([sys.executable] + args, cwd=out, capture_output=True, text=True)
    print(f"  {'PASS' if r.returncode == 0 else 'FAIL'}  {name}")
    if r.returncode: print(r.stderr[-800:])
    return r.returncode == 0
print("Generators:")
ok = True
ok &= run("shop drawing", [S("rayen-shop-drawing/scripts/shop_drawing.py"), S("rayen-shop-drawing/examples/lightbox.json"), "-o", "NT-SD-LB01-R0", "--qto", "lb-qto.json"])
ok &= run("BOQ/QTO", [S("rayen-boq-qto/scripts/qto.py"), "lb-qto.json", "-o", "LB-BOQ.xlsx"])
ok &= run("fabrication parts", [S("rayen-fabrication/scripts/fab_parts.py"), S("rayen-fabrication/examples/lightbox-parts.json"), "-o", "fab"])
ok &= run("space program", [S("rayen-architectural-design/scripts/space_program.py"), S("rayen-architectural-design/examples/office-program.json"), "-o", "program.xlsx"])
ok &= run("lighting calc", [S("rayen-interior-design/scripts/lighting_calc.py"), S("rayen-interior-design/examples/rooms-lighting.json"), "-o", "lighting.xlsx"])
ok &= run("IFC audit", [S("rayen-bim/scripts/ifc_audit.py"), S("rayen-bim/examples/sample.ifc"), "--clash", "IfcWall", "IfcColumn,IfcDuctSegment", "-o", "ifc-audit.xlsx"])
ok &= run("LOD 300 build", [S("rayen-bim/scripts/lod_build.py"), S("rayen-shop-drawing/examples/pylon.json"), "--lod", "300", "-o", "pylon-LOD300.ifc"])
ok &= run("LOD 400 build", [S("rayen-bim/scripts/lod_build.py"), S("rayen-shop-drawing/examples/pylon.json"), "--lod", "400", "-o", "pylon-LOD400.ifc"])
ok &= run("LOD 400 check", [S("rayen-bim/scripts/lod_check.py"), "pylon-LOD400.ifc", "--lod", "400", "--overlap", "-o", "pylon-LOD400-check.xlsx"])
ok &= run("render (draft)", [S("rayen-render/scripts/render.py"), S("rayen-render/examples/reception.json"), "-o", "renders", "--draft"])
pkg = json.load(open(S("rayen-newtech-template/examples/package-example.json"), encoding="utf-8"))
pkg["sheets"][0]["views"][0]["file"] = os.path.join(out, "NT-SD-LB01-R0.dxf")
r = [f for f in os.listdir(os.path.join(out, "renders")) if f.endswith(".png")] if os.path.isdir(os.path.join(out, "renders")) else []
pkg["sheets"][1]["views"][0]["file"] = os.path.join(out, "renders", r[0]) if r else "missing.png"
json.dump(pkg, open(os.path.join(out, "pkg.json"), "w", encoding="utf-8"), ensure_ascii=False)
ok &= run("Newtech template set", [S("rayen-newtech-template/scripts/newtech_sheet.py"), "pkg.json", "-o", "Newtech-Set.pdf", "--png"])
ok &= run("PMO project workbook", [S("rayen-pmo-pmp/scripts/pmo.py"), S("rayen-pmo-pmp/examples/project-plan.json"), "-o", "pm-workbook.xlsx"])
ok &= run("PMO portfolio", [S("rayen-pmo-pmp/scripts/pmo.py"), S("rayen-pmo-pmp/examples/project-plan.json"), S("rayen-pmo-pmp/examples/project-plan.json"), "--portfolio", "-o", "pmo-dashboard.xlsx"])
ok &= run("report", [S("rayen-reports/scripts/report.py"), S("rayen-reports/examples/weekly-status.json"), "-o", "weekly.docx"])
print("ALL PASS" if ok else "SOME CHECKS FAILED", "→", out)
sys.exit(0 if ok else 1)
