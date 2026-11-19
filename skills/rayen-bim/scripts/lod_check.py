#!/usr/bin/env python3
"""RAYEN LOD checker — verify an IFC model against LOD 300 / LOD 400 requirements (geometry + information).

  python3 lod_check.py model.ifc --lod 300 -o Model-LOD300-Check.xlsx
  python3 lod_check.py model.ifc --lod 400 -o Model-LOD400-Check.xlsx --overlap
  python3 lod_check.py --write-matrix BEP-LOD-Matrix.xlsx          # element x stage LOD/author matrix (BEP)

Rules: ../references/lod_requirements.json (edit per project BEP/EIR; --rules other.json). LOD 400 = LOD 300 + 400 rules.
LOD 400 extra checks: unique PartMark geometry (same mark => same profile & length), parts list by mark with
weights, and (--overlap) internal part-to-part overlaps inside each assembly (detailing interfaces).
Result is a compliance score, not an approval: "LOD compliant" only within the rules used.
"""
import argparse, collections, json, os, sys
import ifcopenshell
import ifcopenshell.util.element as ue

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "references", "lod_requirements.json")


def psets(el):
    try:
        return ue.get_psets(el)
    except Exception:
        return {}


def body_items(el):
    rep = getattr(el, "Representation", None)
    if not rep:
        return None, []
    for r in rep.Representations:
        if r.RepresentationIdentifier == "Body":
            return r, list(r.Items)
    return None, []


def in_assembly(el):
    for rel in getattr(el, "Decomposes", []) or []:
        if rel.RelatingObject.is_a("IfcElementAssembly"):
            return rel.RelatingObject
    return None


def contained(el):
    c = ue.get_container(el)
    if c:
        return c
    a = in_assembly(el)
    return ue.get_container(a) if a else None


def has_class(el):
    for rel in getattr(el, "HasAssociations", []) or []:
        if rel.is_a("IfcRelAssociatesClassification"):
            return True
    t = ue.get_type(el)
    if t:
        for rel in getattr(t, "HasAssociations", []) or []:
            if rel.is_a("IfcRelAssociatesClassification"):
                return True
    return False


def check(el, code, P):
    if code == "name":
        return bool(el.Name), el.Name or "missing"
    if code == "type":
        t = ue.get_type(el); return bool(t), t.Name if t else "no type object"
    if code == "storey":
        c = contained(el); return bool(c), c.Name if c else "not in a storey"
    if code == "material":
        m = ue.get_material(el); return m is not None, (getattr(m, "Name", None) or (m.is_a() if m else "none"))
    if code == "body":
        r, items = body_items(el); return bool(items), r.RepresentationType if r else "no Body"
    if code == "solid":
        r, items = body_items(el)
        ok = bool(r) and r.RepresentationType in ("SweptSolid", "Brep", "AdvancedBrep", "AdvancedSweptSolid", "CSG", "Clipping", "Tessellation", "MappedRepresentation")
        return ok, r.RepresentationType if r else "no Body"
    if code == "profile":
        r, items = body_items(el)
        for it in items:
            if it.is_a("IfcSweptAreaSolid"):
                pr = it.SweptArea
                ok = not (pr.is_a() == "IfcRectangleProfileDef" and not getattr(pr, "ProfileName", None))
                return ok, f"{pr.is_a()} {getattr(pr, 'ProfileName', '') or ''}".strip()
        return False, "no swept profile"
    if code == "classification":
        return has_class(el), "classified" if has_class(el) else "no classification reference"
    if code == "assembly":
        a = in_assembly(el); return bool(a), a.Name if a else "not in an assembly"
    if code == "mark":
        v = P.get("NT_Fabrication", {}).get("PartMark"); return bool(v), v or "no PartMark"
    if code == "parts":
        n = sum(len(r.RelatedObjects) for r in getattr(el, "IsDecomposedBy", []) or []); return n > 0, f"{n} parts"
    if code.startswith(("pset:", "qto:")):
        ps, prop = code.split(":", 1)[1].split(".", 1)
        v = P.get(ps, {}).get(prop)
        return v not in (None, ""), "missing" if v in (None, "") else str(v)[:40]
    return False, f"unknown check {code}"


ASSEMBLY_EXEMPT = {"material", "body", "solid", "profile", "type"}  # an assembly's geometry/material = its parts


def rules_for(R, lod, el):
    out, seen = [], set()
    is_asm = el.is_a("IfcElementAssembly")
    levels = ["300"] + (["400"] if lod >= 400 else [])
    for lv in levels:
        cls_rules = R.get(lv, {})
        skip_star = lv == "400" and any(el.is_a(c) for c in R.get("_skip_400_classes", []))
        for key, rl in cls_rules.items():
            if key.startswith("_"):
                continue
            if (key == "*" and not skip_star) or (key != "*" and el.is_a(key)):
                for code, sev in rl:
                    if is_asm and code in ASSEMBLY_EXEMPT:
                        continue
                    if code not in seen:
                        seen.add(code); out.append((lv, code, sev))
    return out


def bbox(el, settings):
    import ifcopenshell.geom
    try:
        sh = ifcopenshell.geom.create_shape(settings, el)
    except Exception:
        return None
    v = sh.geometry.verts
    return (min(v[0::3]), min(v[1::3]), min(v[2::3]), max(v[0::3]), max(v[1::3]), max(v[2::3]))


def overlaps(f, tol_mm):
    import ifcopenshell.geom
    st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
    scale = 1.0
    try:
        import ifcopenshell.util.unit as uu
        scale = uu.calculate_unit_scale(f) * 1000  # file unit -> mm
    except Exception:
        pass
    res = []
    for asm in f.by_type("IfcElementAssembly"):
        # fasteners pass through parts by design -> excluded from overlap screening
        parts = [p for r in asm.IsDecomposedBy for p in r.RelatedObjects if not p.is_a("IfcFastener") and not p.is_a("IfcMechanicalFastener")]
        boxes = [(p, bbox(p, st)) for p in parts]
        boxes = [(p, b) for p, b in boxes if b]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (pa, a), (pb, b) = boxes[i], boxes[j]
                ov = [(min(a[k + 3], b[k + 3]) - max(a[k], b[k])) * 1000 for k in range(3)]  # geometry in metres
                if all(o > tol_mm for o in ov):
                    res.append((asm, pa, pb, round(min(ov), 1)))
    return res


MATRIX = [
    ("Architecture", "Walls / partitions", 200, 300, 350, "—", "Architect"),
    ("Architecture", "Doors & windows", 200, 300, 350, "400 (supplier)", "Architect"),
    ("Architecture", "Ceilings", 200, 300, 350, "400 (ceiling contractor)", "Interior designer"),
    ("Architecture", "Floors / finishes", 200, 300, 300, "—", "Interior designer"),
    ("Architecture", "Curtain wall / façade", 200, 300, 350, "400 (façade contractor)", "Façade consultant"),
    ("Interior", "Joinery / counters", 100, 300, 350, "400 (Newtech joinery)", "Newtech"),
    ("Interior", "Loose furniture (FF&E)", 100, 200, 300, "—", "Interior designer"),
    ("Structure", "Columns / beams / slabs", 200, 300, 350, "400 (steel fabricator)", "Structural engineer"),
    ("Structure", "Steel connections", "—", 200, 350, 400, "Steel fabricator"),
    ("MEP", "Ducts / pipes / trays", 200, 300, 350, "400 (MEP contractor)", "MEP engineer"),
    ("MEP", "Light fixtures", 200, 300, 350, "—", "MEP / lighting designer"),
    ("Signage", "Signs (envelope + fixing zone)", 100, 300, 350, "—", "Newtech"),
    ("Signage", "Sign assemblies (frame, faces, returns, anchors, LED)", "—", "—", 350, 400, "Newtech"),
    ("Signage", "LED screens (cabinets + support frame)", 100, 300, 350, 400, "Newtech"),
]


def write_matrix(path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "LOD Matrix"
    ws.append(["Discipline", "Element", "Concept/SD", "DD", "IFC / Coordination", "Fabrication / Shop", "Model author (MEA)", "Notes"])
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="0F4C82")
    for r in MATRIX: ws.append(list(r) + [""])
    ws.append([]); ws.append(["LOD 300: specific system, true size/shape/location/orientation, non-graphic data attached."])
    ws.append(["LOD 350: + interfaces with other systems (supports, connections, clearances)."])
    ws.append(["LOD 400: fabrication & assembly detail — parts, profiles, lengths, fasteners, marks, weights; model can drive shop drawings & CNC."])
    ws.append(["Edit per project EIR/BEP. Template by RAYEN — TO BE CONFIRMED by the BIM manager."])
    for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 22
    wb.save(path); print("LOD matrix:", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ifc", nargs="?"); ap.add_argument("--lod", type=int, choices=[300, 350, 400], default=300)
    ap.add_argument("--rules", default=RULES); ap.add_argument("-o", "--out")
    ap.add_argument("--overlap", action="store_true", help="LOD 400: part-to-part overlaps inside assemblies")
    ap.add_argument("--tol", type=float, default=1.0, help="overlap tolerance mm")
    ap.add_argument("--classes", nargs="*", help="only these IFC classes")
    ap.add_argument("--write-matrix")
    a = ap.parse_args()
    if a.write_matrix:
        write_matrix(a.write_matrix)
        if not a.ifc: return
    if not a.ifc:
        ap.error("ifc required")
    R = json.load(open(a.rules, encoding="utf-8"))
    f = ifcopenshell.open(a.ifc)
    exempt = R.get("_exempt", [])
    els = [e for e in f.by_type("IfcElement") if not any(e.is_a(x) for x in exempt)]
    if a.classes:
        els = [e for e in els if any(e.is_a(c) for c in a.classes)]
    rows, fails = [], []
    stat = collections.defaultdict(lambda: [0, 0, 0])  # class: checks, passed, failed(fail-severity)
    el_ok = collections.Counter()
    for e in els:
        P = psets(e)
        failed_hard = False
        for lv, code, sev in rules_for(R, a.lod, e):
            ok, info = check(e, code, P)
            stat[e.is_a()][0] += 1
            stat[e.is_a()][1] += ok
            if not ok:
                if sev == "fail":
                    stat[e.is_a()][2] += 1; failed_hard = True
                fails.append([e.GlobalId, e.is_a(), e.Name, lv, code, sev.upper(), info])
            rows.append([e.GlobalId, e.is_a(), e.Name, lv, code, sev, "PASS" if ok else "FAIL", info])
        el_ok[(e.is_a(), not failed_hard)] += 1
    # LOD 400 fabrication consistency
    parts, conflicts, ovl = [], [], []
    if a.lod >= 400:
        marks = collections.defaultdict(list)
        for e in els:
            fb = psets(e).get("NT_Fabrication")
            if fb and fb.get("PartMark"):
                asm = in_assembly(e)
                marks[(asm.GlobalId if asm else "-", fb["PartMark"])].append((e, fb))
        for (ag, mk), lst in sorted(marks.items(), key=lambda x: x[0][1]):
            geo = {(str(fb.get("Profile")), round(float(fb.get("Length_mm") or 0))) for _, fb in lst}
            if len(geo) > 1:
                conflicts.append([mk, len(lst), "; ".join(f"{p} L={l}" for p, l in sorted(geo))])
            for (prof, L) in sorted(geo):
                sub = [x for x in lst if (str(x[1].get("Profile")), round(float(x[1].get("Length_mm") or 0))) == (prof, L)]
                w = sum(float(x[1].get("Weight_kg") or 0) for x in sub)
                parts.append([mk + ("" if len(geo) == 1 else f"-{sorted(geo).index((prof, L)) + 1}"), prof, L, len(sub),
                              sub[0][1].get("MaterialGrade", ""), round(w, 2), sub[0][1].get("Status", ""), sub[0][1].get("DrawingRef", "")])
        if a.overlap:
            ovl = overlaps(f, a.tol)
    # report
    tot_c = sum(v[0] for v in stat.values()); tot_p = sum(v[1] for v in stat.values())
    n_ok = sum(v for (c, ok), v in el_ok.items() if ok); n_el = sum(el_ok.values())
    score = 100 * tot_p / tot_c if tot_c else 0
    print(f"LOD {a.lod} check · {os.path.basename(a.ifc)} · elements {n_el} · checks {tot_c} · score {score:.1f}% · "
          f"elements without FAIL {n_ok}/{n_el}")
    for c, (n, p, fl) in sorted(stat.items()):
        print(f"  {c:28s} checks {n:4d}  pass {p:4d}  ({100 * p / n:5.1f}%)  hard-fails {fl}")
    shown = collections.Counter()
    for fr in fails:
        k = (fr[1], fr[4])
        shown[k] += 1
        if shown[k] == 1:
            print(f"  {fr[5]:4s} {fr[1]:24s} {fr[4]:42s} e.g. '{fr[2]}' → {fr[6]}")
    if parts:
        print("  Parts list (LOD 400):")
        for p in parts:
            print(f"    {p[0]:6s} {p[1]:20s} L={p[2]:6d} x{p[3]:3d}  {p[5]:8.2f} kg  {p[6]}")
    for c in conflicts:
        print(f"  MARK CONFLICT {c[0]}: {c[1]} parts with different geometry: {c[2]}")
    for asm, pa, pb, mm in ovl[:20]:
        print(f"  OVERLAP {pa.Name} x {pb.Name} ≈ {mm} mm (assembly '{asm.Name}')")
    if len(ovl) > 20:
        print(f"  ... {len(ovl)} overlaps total")
    verdict = "MEETS" if all(v[2] == 0 for v in stat.values()) and not conflicts else "DOES NOT MEET"
    print(f"VERDICT: model {verdict} LOD {a.lod} rules ({os.path.basename(a.rules)})" + (f" · {len(ovl)} internal overlaps to review" if ovl else ""))
    if a.out:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = "Summary"
        H = PatternFill("solid", fgColor="0F4C82")
        def table(ws, head, data):
            ws.append(head)
            for c in ws[ws.max_row]: c.font = Font(bold=True, color="FFFFFF"); c.fill = H
            for r in data: ws.append(r)
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 20
        table(ws, ["Item", "Value"], [["Model", a.ifc], ["Target LOD", a.lod], ["Rules", a.rules], ["Elements", n_el],
              ["Checks", tot_c], ["Score %", round(score, 1)], ["Elements without hard fail", f"{n_ok}/{n_el}"],
              ["Mark conflicts", len(conflicts)], ["Internal overlaps", len(ovl)], ["Verdict", verdict],
              ["Note", "Compliance within the listed rules only; not an approval. Geometry accuracy vs. site/shop data must be verified by the author."]])
        ws.append([]); table(ws, ["IFC class", "Checks", "Passed", "Hard fails", "Pass %"],
                             [[c, n, p, fl, round(100 * p / n, 1)] for c, (n, p, fl) in sorted(stat.items())])
        table(wb.create_sheet("Compliance"), ["GlobalId", "Class", "Name", "LOD", "Check", "Severity", "Result", "Value / reason"], rows)
        table(wb.create_sheet("Failures"), ["GlobalId", "Class", "Name", "LOD", "Check", "Severity", "Reason"], fails)
        if a.lod >= 400:
            table(wb.create_sheet("Parts list"), ["Mark", "Profile", "Length mm", "Qty", "Material", "Weight kg", "Status", "Drawing"], parts)
            table(wb.create_sheet("Mark conflicts"), ["Mark", "Parts", "Different geometries"], conflicts)
            table(wb.create_sheet("Internal overlaps"), ["Assembly", "Part A", "Part B", "Overlap mm", "Action"],
                  [[x.Name, pa.Name, pb.Name, mm, "Resolve detail (cut length / cope / gap)"] for x, pa, pb, mm in ovl])
        wb.save(a.out); print("saved", a.out)


if __name__ == "__main__":
    main()
