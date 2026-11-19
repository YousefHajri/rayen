#!/usr/bin/env python3
"""RAYEN IFC audit & take-off — open BIM model check without Revit.

  python3 ifc_audit.py model.ifc -o Model-Audit.xlsx [--required Pset_WallCommon.FireRating ...]
  python3 ifc_audit.py --make-sample sample.ifc      # small test model

Sheets: Summary · Elements (GUID, class, type, storey, name, material, qty) · Quantities by class/storey
· Data gaps (missing name/storey/material/required properties) · Spaces · Clash (bbox, optional --clash A B).
Needs: pip install ifcopenshell openpyxl
"""
import argparse, collections, sys

try:
    import ifcopenshell, ifcopenshell.util.element as ue
except ImportError:
    sys.exit("ifcopenshell missing: pip install ifcopenshell")


def qty(el):
    """Return dict of base quantities found on element (Qto_* sets) ."""
    out = {}
    for name, props in ue.get_psets(el, qtos_only=True).items():
        for k, v in props.items():
            if k != "id" and isinstance(v, (int, float)):
                out[k] = v
    return out


def material_name(el):
    m = ue.get_material(el)
    if m is None:
        return ""
    if m.is_a("IfcMaterial"):
        return m.Name
    try:
        mats = ue.get_materials(el)
        return " / ".join(sorted({x.Name for x in mats if x.Name}))
    except Exception:
        return m.is_a()


def get_prop(el, dotted):
    pset, prop = dotted.split(".", 1)
    return ue.get_psets(el).get(pset, {}).get(prop)


def bbox_index(f, classes):
    import ifcopenshell.geom
    st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
    boxes = {}
    for c in classes:
        for el in f.by_type(c):
            try:
                sh = ifcopenshell.geom.create_shape(st, el)
            except Exception:
                continue
            v = sh.geometry.verts
            xs, ys, zs = v[0::3], v[1::3], v[2::3]
            boxes[el.GlobalId] = (el, (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
    return boxes


def clash(f, A, B, tol):
    a, b = bbox_index(f, A), bbox_index(f, B)
    res = []
    for ga, (ea, ba) in a.items():
        for gb, (eb, bb) in b.items():
            if ga == gb:
                continue
            ov = [min(ba[i + 3], bb[i + 3]) - max(ba[i], bb[i]) for i in range(3)]
            if all(o > tol for o in ov):
                res.append((ea, eb, round(min(ov) * 1000)))
    return res


def make_sample(path):
    import ifcopenshell.api as api, numpy as np
    f = api.run("project.create_file", version="IFC4")
    proj = api.run("root.create_entity", f, ifc_class="IfcProject", name="RAYEN sample")
    api.run("unit.assign_unit", f)
    ctx = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
    bld = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Showroom")
    st = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="GF")
    api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
    api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
    api.run("aggregate.assign_object", f, relating_object=bld, products=[st])
    conc = api.run("material.add_material", f, name="Concrete C30")
    blk = api.run("material.add_material", f, name="Blockwork 200")

    def place(el, x, y, z=0.0):
        m = np.eye(4); m[:3, 3] = [x, y, z]
        api.run("geometry.edit_object_placement", f, product=el, matrix=m)
        api.run("spatial.assign_container", f, relating_structure=st, products=[el])

    walls = [(0, 0, 8, "W-01"), (0, 6, 8, "W-02")]
    for x, y, L, n in walls:
        w = api.run("root.create_entity", f, ifc_class="IfcWall", name=n)
        rep = api.run("geometry.add_wall_representation", f, context=body, length=L, height=3.2, thickness=0.2)
        api.run("geometry.assign_representation", f, product=w, representation=rep); place(w, x, y)
        api.run("material.assign_material", f, products=[w], material=blk)
        q = api.run("pset.add_qto", f, product=w, name="Qto_WallBaseQuantities")
        api.run("pset.edit_qto", f, qto=q, properties={"Length": L, "Height": 3.2, "NetSideArea": L * 3.2})
        if n == "W-01":
            ps = api.run("pset.add_pset", f, product=w, name="Pset_WallCommon")
            api.run("pset.edit_pset", f, pset=ps, properties={"FireRating": "1HR", "IsExternal": True})
    s = api.run("root.create_entity", f, ifc_class="IfcSlab", name="GF slab")
    rep = api.run("geometry.add_slab_representation", f, context=body, depth=0.2, polyline=[(0, 0), (8, 0), (8, 6.2), (0, 6.2)])
    api.run("geometry.assign_representation", f, product=s, representation=rep); place(s, 0, 0, -0.2)
    api.run("material.assign_material", f, products=[s], material=conc)
    c = api.run("root.create_entity", f, ifc_class="IfcColumn", name="C-01")  # intentionally clashes with W-01
    rep = api.run("geometry.add_profile_representation", f, context=body,
                  profile=f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", XDim=400.0, YDim=400.0), depth=3.2)  # profile in file units (mm)
    api.run("geometry.assign_representation", f, product=c, representation=rep); place(c, 4, 0.1)
    d = api.run("root.create_entity", f, ifc_class="IfcDuctSegment", name="SA duct")  # no storey/material -> gap
    rep = api.run("geometry.add_wall_representation", f, context=body, length=8, height=0.4, thickness=0.6)
    api.run("geometry.assign_representation", f, product=d, representation=rep)
    m = np.eye(4); m[:3, 3] = [0, -0.3, 2.7]  # runs through W-01 -> clash; api.run("geometry.edit_object_placement", f, product=d, matrix=m)
    f.write(path); print("sample written", path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ifc", nargs="?")
    ap.add_argument("-o", "--out")
    ap.add_argument("--required", nargs="*", default=[], help="[IfcClass:]Pset.Property required, e.g. IfcWall:Pset_WallCommon.FireRating IfcDoor:Pset_DoorCommon.FireRating")
    ap.add_argument("--req-classes", nargs="*", default=["IfcWall", "IfcDoor", "IfcWindow", "IfcSlab"])
    ap.add_argument("--clash", nargs=2, metavar=("CLASSES_A", "CLASSES_B"), help="comma lists, e.g. IfcWall,IfcColumn IfcDuctSegment,IfcPipeSegment")
    ap.add_argument("--tol", type=float, default=0.01, help="clash tolerance m (bbox overlap)")
    ap.add_argument("--make-sample")
    a = ap.parse_args()
    if a.make_sample:
        return make_sample(a.make_sample)
    if not a.ifc:
        ap.error("ifc file required")
    f = ifcopenshell.open(a.ifc)
    els = [e for e in f.by_type("IfcElement") if not e.is_a("IfcOpeningElement")]
    rows, gaps = [], []
    for e in els:
        cont = ue.get_container(e)
        if not cont:  # parts of an assembly inherit the assembly's storey
            agg = ue.get_aggregate(e)
            cont = ue.get_container(agg) if agg else None
        t = ue.get_type(e)
        mat = material_name(e)
        q = qty(e)
        rows.append([e.GlobalId, e.is_a(), t.Name if t else "", cont.Name if cont else "", e.Name or "", mat,
                     q.get("Length") or q.get("Width"), q.get("NetSideArea") or q.get("NetArea") or q.get("GrossArea"),
                     q.get("NetVolume") or q.get("GrossVolume"), q.get("Count")])
        if not e.Name: gaps.append([e.GlobalId, e.is_a(), "Name missing", "Model author"])
        if not cont: gaps.append([e.GlobalId, e.is_a(), "Not contained in a storey", "Model author"])
        if not mat: gaps.append([e.GlobalId, e.is_a(), "No material", "Model author"])
        if not t: gaps.append([e.GlobalId, e.is_a(), "No type object", "Model author"])
        for r in a.required:
            cls, _, rr = r.rpartition(":")
            applies = e.is_a(cls) if cls else e.is_a() in a.req_classes
            if applies and get_prop(e, rr) in (None, ""):
                gaps.append([e.GlobalId, e.is_a(), f"{rr} missing", "Model author"])
    by = collections.Counter((r[1], r[3]) for r in rows)
    spaces = []
    for s in f.by_type("IfcSpace"):
        par = ue.get_container(s) or ue.get_aggregate(s)
        q = qty(s)
        spaces.append([s.GlobalId, s.Name, s.LongName, par.Name if par else "", q.get("NetFloorArea") or q.get("GrossFloorArea")])
    clashes = []
    if a.clash:
        clashes = clash(f, a.clash[0].split(","), a.clash[1].split(","), a.tol)

    proj = f.by_type("IfcProject")[0]
    print(f"IFC {f.schema} · project '{proj.Name}' · storeys {[s.Name for s in f.by_type('IfcBuildingStorey')]}")
    print(f"elements {len(rows)} · data gaps {len(gaps)} · spaces {len(spaces)} · clashes {len(clashes)}")
    for (c, s), n in sorted(by.items()):
        print(f"  {c:28s} {s or '(no storey)':12s} {n}")
    for g in gaps[:15]:
        print("  GAP", g[1], g[0], g[2])
    for ea, eb, mm in clashes:
        print(f"  CLASH {ea.is_a()} '{ea.Name}' x {eb.is_a()} '{eb.Name}' overlap ~{mm} mm")

    if a.out:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = "Summary"
        hdr = PatternFill("solid", fgColor="1F3864")
        def table(ws, head, data):
            ws.append(head)
            for c in ws[ws.max_row]: c.font = Font(bold=True, color="FFFFFF"); c.fill = hdr
            for r in data: ws.append(r)
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 18
        table(ws, ["Item", "Value"], [["File", a.ifc], ["Schema", f.schema], ["Project", proj.Name],
              ["Storeys", ", ".join(s.Name or "" for s in f.by_type("IfcBuildingStorey"))],
              ["Elements", len(rows)], ["Data gaps", len(gaps)], ["Spaces", len(spaces)], ["BBox clashes", len(clashes)],
              ["Note", "Quantities = model Qto sets (VERIFIED from model only). Clashes = bounding-box screening; confirm in Navisworks/ACC."]])
        table(wb.create_sheet("Elements"), ["GlobalId", "Class", "Type", "Storey", "Name", "Material", "Length/Width m", "Area m2", "Volume m3", "Count"], rows)
        table(wb.create_sheet("By class-storey"), ["Class", "Storey", "Count"], [[c, s, n] for (c, s), n in sorted(by.items())])
        table(wb.create_sheet("Data gaps"), ["GlobalId", "Class", "Issue", "Responsible"], gaps)
        table(wb.create_sheet("Spaces"), ["GlobalId", "Number", "Name", "Storey", "Area m2"], spaces)
        table(wb.create_sheet("Clash screening"), ["No.", "Element A", "Name A", "GUID A", "Element B", "Name B", "GUID B", "Overlap mm", "Status", "Responsibility"],
              [[i + 1, ea.is_a(), ea.Name, ea.GlobalId, eb.is_a(), eb.Name, eb.GlobalId, mm, "OPEN", ""] for i, (ea, eb, mm) in enumerate(clashes)])
        wb.save(a.out); print("saved", a.out)


if __name__ == "__main__":
    main()
