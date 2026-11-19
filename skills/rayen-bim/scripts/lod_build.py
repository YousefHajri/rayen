#!/usr/bin/env python3
"""RAYEN LOD builder — shop-drawing spec JSON -> IFC4 model at LOD 300 or LOD 400.

Same spec as rayen-shop-drawing (lightbox | pylon | graphic_frame), so drawing, BOQ and BIM agree.

  python3 lod_build.py spec.json --lod 300 -o NT-P01-LOD300.ifc
  python3 lod_build.py spec.json --lod 400 -o NT-P01-LOD400.ifc [--origin x y z] [--rot 0]

LOD 300  one IfcBuildingElementProxy (ObjectType SIGN): true envelope W x D x H at its location,
         type object, material, NT_Sign + NT_LOD + Pset_ManufacturerTypeInformation + Qto.
LOD 400  IfcElementAssembly (SIGN) decomposed into fabrication parts:
         IfcMember (real hollow/circle/angle profiles, true lengths) · IfcPlate (face, returns, back,
         base plates) · IfcMechanicalFastener (anchors) · IfcLightFixture (LED array, lightbox) — every part
         with NT_Fabrication {PartMark, AssemblyMark, Profile, Length_mm, MaterialGrade, Finish, Weight_kg,
         Process, DrawingRef, Status} and Qto. Weights CALCULATED from section geometry (corner radii ignored).
Coordinates mm: X = width, Y = depth (front face at Y=0), Z = up.
Items not defined by the spec (anchor embedment, base-plate count, anchor edge distance) are modelled with
ASSUMED values and tagged Status = "ASSUMED — confirm by structural engineer".
"""
import argparse, json, math, re, sys
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.guid

DENS = {"steel": 7850, "alum": 2700, "acrylic": 1190, "acp": 1400, "mdf": 750, "glass": 2500, "ss": 8000}


def density(mat):
    m = mat.lower()
    if "led" in m: return 500  # ~5 kg/m2 at 10 mm module layer (ASSUMED)
    if "acp" in m: return DENS["acp"]  # 4 mm ACP ~ 5.6 kg/m2 -> equivalent density (ASSUMED)
    if "acryl" in m: return DENS["acrylic"]
    if "stainless" in m or m.startswith("ss"): return DENS["ss"]
    if "alum" in m: return DENS["alum"]
    if "mdf" in m: return DENS["mdf"]
    if "glass" in m: return DENS["glass"]
    return DENS["steel"]


def thk(s, default):
    m = re.search(r"([\d.]+)\s*mm", s or "")
    return float(m.group(1)) if m else default


def nums(s):
    return [float(x) for x in re.findall(r"[\d.]+", s)]


def member_positions(total, member, max_spacing):
    clear = total - member
    n_bays = max(1, math.ceil(clear / max_spacing))
    return [member / 2 + i * clear / n_bays for i in range(n_bays + 1)]


class B:
    def __init__(self, spec, lod, origin, rot):
        self.s, self.lod = spec, lod
        self.ox, self.oy, self.oz = origin
        self.rot = math.radians(rot)
        f = self.f = api.run("project.create_file", version="IFC4")
        self.proj = api.run("root.create_entity", f, ifc_class="IfcProject", name=spec.get("project", "Newtech"))
        lu = f.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE")
        au = f.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE")
        vu = f.create_entity("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE")
        mu = f.create_entity("IfcSIUnit", UnitType="MASSUNIT", Prefix="KILO", Name="GRAM")
        pa = f.create_entity("IfcSIUnit", UnitType="PLANEANGLEUNIT", Name="RADIAN")
        self.proj.UnitsInContext = f.create_entity("IfcUnitAssignment", Units=[lu, au, vu, mu, pa])
        ctx = api.run("context.add_context", f, context_type="Model")
        self.body = api.run("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
        site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
        bld = api.run("root.create_entity", f, ifc_class="IfcBuilding", name=spec.get("building", "Building"))
        self.st = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name=spec.get("storey", "GF"))
        api.run("aggregate.assign_object", f, relating_object=self.proj, products=[site])
        api.run("aggregate.assign_object", f, relating_object=site, products=[bld])
        api.run("aggregate.assign_object", f, relating_object=bld, products=[self.st])
        self.mats = {}
        self.parts = []
        self.types = {}

    # ---------- low-level geometry (file units = mm)
    def pt(self, x, y, z):
        c, s = math.cos(self.rot), math.sin(self.rot)
        return (float(self.ox + c * x - s * y), float(self.oy + s * x + c * y), float(self.oz + z))

    def dir(self, v):
        c, s = math.cos(self.rot), math.sin(self.rot)
        return (float(c * v[0] - s * v[1]), float(s * v[0] + c * v[1]), float(v[2]))

    def placement(self, loc, z=(0, 0, 1), x=(1, 0, 0)):
        f = self.f
        a = f.create_entity("IfcAxis2Placement3D", Location=f.create_entity("IfcCartesianPoint", Coordinates=self.pt(*loc)),
                            Axis=f.create_entity("IfcDirection", DirectionRatios=self.dir(z)),
                            RefDirection=f.create_entity("IfcDirection", DirectionRatios=self.dir(x)))
        return f.create_entity("IfcLocalPlacement", RelativePlacement=a)

    def extrude(self, profile, depth):
        f = self.f
        pos = f.create_entity("IfcAxis2Placement3D", Location=f.create_entity("IfcCartesianPoint", Coordinates=(0., 0., 0.)))
        solid = f.create_entity("IfcExtrudedAreaSolid", SweptArea=profile, Position=pos,
                                ExtrudedDirection=f.create_entity("IfcDirection", DirectionRatios=(0., 0., 1.)), Depth=float(depth))
        rep = f.create_entity("IfcShapeRepresentation", ContextOfItems=self.body, RepresentationIdentifier="Body",
                              RepresentationType="SweptSolid", Items=[solid])
        return f.create_entity("IfcProductDefinitionShape", Representations=[rep])

    def profile(self, section):
        f = self.f
        n = nums(section)
        key = section.strip().upper()
        if key.startswith(("RHS", "SHS")):
            X, Y, t = (n + [n[0], 2])[:3] if len(n) >= 3 else (n[0], n[0], n[1])
            return f.create_entity("IfcRectangleHollowProfileDef", ProfileType="AREA", ProfileName=section, XDim=X, YDim=Y, WallThickness=t), \
                X * Y - (X - 2 * t) * (Y - 2 * t), (X, Y)
        if key.startswith("CHS"):
            D, t = n[0], n[1]
            return f.create_entity("IfcCircleHollowProfileDef", ProfileType="AREA", ProfileName=section, Radius=D / 2, WallThickness=t), \
                math.pi / 4 * (D ** 2 - (D - 2 * t) ** 2), (D, D)
        if key.startswith("L"):
            a, b, t = n[0], n[1], n[2]
            return f.create_entity("IfcLShapeProfileDef", ProfileType="AREA", ProfileName=section, Depth=a, Width=b, Thickness=t), \
                (a + b - t) * t, (b, a)
        X, Y = n[0], n[1] if len(n) > 1 else n[0]
        return f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", ProfileName=section, XDim=X, YDim=Y), X * Y, (X, Y)

    def rect_profile(self, x, y):
        f = self.f
        return f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", XDim=float(x), YDim=float(y),
                               Position=f.create_entity("IfcAxis2Placement2D", Location=f.create_entity("IfcCartesianPoint", Coordinates=(x / 2, y / 2))))

    def material(self, name):
        if name not in self.mats:
            self.mats[name] = api.run("material.add_material", self.f, name=name[:60])
        return self.mats[name]

    def element(self, cls, name, shape, plc, mat, psets, qto=None, predefined=None):
        f = self.f
        el = api.run("root.create_entity", f, ifc_class=cls, name=name, predefined_type=predefined)
        el.Representation, el.ObjectPlacement = shape, plc
        api.run("material.assign_material", f, products=[el], material=self.material(mat))
        for pn, props in psets.items():
            ps = api.run("pset.add_pset", f, product=el, name=pn)
            api.run("pset.edit_pset", f, pset=ps, properties={k: v for k, v in props.items() if v not in (None, "")})
        if qto:
            q = api.run("pset.add_qto", f, product=el, name=qto[0])
            api.run("pset.edit_qto", f, qto=q, properties=qto[1])
        fb = psets.get("NT_Fabrication")
        if fb and self.lod == 400:  # one type object per part mark + profile (Revit-style family type)
            key = (cls, fb["PartMark"], fb["Profile"])
            if key not in self.types:
                tcls = {"IfcMember": "IfcMemberType", "IfcPlate": "IfcPlateType", "IfcMechanicalFastener": "IfcMechanicalFastenerType",
                        "IfcLightFixture": "IfcLightFixtureType"}.get(cls)
                if tcls:
                    self.types[key] = api.run("root.create_entity", f, ifc_class=tcls, name=f"{fb['PartMark']} {fb['Profile']}")
            if key in self.types:
                api.run("type.assign_type", f, related_objects=[el], relating_type=self.types[key])
        return el

    # ---------- parts
    def fab(self, mark, profile, length, matgrade, weight, process, status="CALCULATED"):
        s = self.s
        return {"NT_Fabrication": {"PartMark": mark, "AssemblyMark": s.get("mark", s.get("drawing_no", "A1")),
                                   "Profile": profile, "Length_mm": round(length, 1), "MaterialGrade": matgrade,
                                   "Finish": s.get("finish", "HDG + paint" if "hdg" in matgrade.lower() else "TO BE CONFIRMED"),
                                   "Weight_kg": round(weight, 2), "Process": process,
                                   "DrawingRef": f"{s.get('drawing_no', '')} {s.get('rev', '')}", "Status": status},
                "NT_LOD": {"LOD": "400", "Discipline": "Signage", "ModelAuthor": "Newtech / RAYEN"}}

    def member(self, mark, section, mat, p0, axis, length, refx=(1, 0, 0), name=None):
        prof, area, _ = self.profile(section)
        w = area * length * 1e-9 * density(mat)
        el = self.element("IfcMember", name or f"{mark} {section}", self.extrude(prof, length), self.placement(p0, axis, refx), mat,
                          self.fab(mark, section, length, mat, w, "Cut + weld/bolt"),
                          ("Qto_MemberBaseQuantities", {"Length": float(length), "NetWeight": round(w, 3)}),
                          predefined="MEMBER" if axis == (0, 0, 1) else "STUD")
        self.parts.append((mark, section, length, mat, w, el)); return el

    def plate(self, mark, desc, mat, t, p0, size_x, size_y, axis, refx, status="CALCULATED", cls="IfcPlate", process="CNC / laser"):
        w = size_x * size_y * t * 1e-9 * density(mat)
        el = self.element(cls, f"{mark} {desc}", self.extrude(self.rect_profile(size_x, size_y), t), self.placement(p0, axis, refx), mat,
                          self.fab(mark, f"PL {size_x:.0f}x{size_y:.0f}x{t:g}", max(size_x, size_y), mat, w, process, status),
                          ("Qto_PlateBaseQuantities", {"Width": float(size_x), "Length": float(size_y), "Thickness": float(t),
                                                       "NetArea": round(size_x * size_y * 1e-6, 4), "NetWeight": round(w, 3)}) if cls == "IfcPlate" else None,
                          predefined="SHEET" if cls == "IfcPlate" else None)
        self.parts.append((mark, f"PL t{t:g}", max(size_x, size_y), mat, w, el)); return el

    def anchor(self, mark, d, L, p0, axis, refx=(1, 0, 0)):
        f = self.f
        prof = f.create_entity("IfcCircleProfileDef", ProfileType="AREA", Radius=d / 2)
        w = math.pi / 4 * d * d * L * 1e-9 * 7850
        ps = self.fab(mark, f"M{d:g} x {L:g}", L, self.s.get("anchor_grade", "Grade 8.8 HDG (ASSUMED)"), w, "Supply / install",
                      "ASSUMED — confirm by structural engineer")
        ps["Pset_MechanicalFastenerCommon"] = {"NominalDiameter": float(d), "NominalLength": float(L)}
        el = self.element("IfcMechanicalFastener", f"{mark} anchor M{d:g}", self.extrude(prof, L), self.placement(p0, axis, refx), "Steel anchor", ps,
                          predefined="ANCHORBOLT")
        self.parts.append((mark, f"M{d:g}x{L:g}", L, "Steel anchor", w, el)); return el

    # ---------- build
    def build(self):
        s = self.s
        typ = s["type"]
        W, H, D = float(s["width"]), float(s["height"]), float(s["depth"])
        sign_ps = {"NT_Sign": {"SignType": typ, "Mark": s.get("mark", s.get("drawing_no", "")), "Width": W, "Height": H, "Depth": D,
                               "Face": s.get("face", ""), "Returns": s.get("returns", ""), "Back": s.get("back", ""),
                               "Frame": f"{s['frame']['section']} {s['frame']['material']}", "Lighting": s.get("lighting", ""),
                               "Fixing": s.get("fixing", ""), "Illuminated": bool(s.get("lighting")),
                               "DrawingRef": f"{s.get('drawing_no', '')} {s.get('rev', '')}", "Status": s.get("status", "FOR APPROVAL")},
                   "NT_LOD": {"LOD": str(self.lod), "Discipline": "Signage", "ModelAuthor": "Newtech / RAYEN"},
                   "Pset_ManufacturerTypeInformation": {"Manufacturer": "Newtech Factory for Billboards and Screens",
                                                        "ModelLabel": s.get("drawing_no", ""), "ModelReference": s.get("title", "")}}
        if self.lod == 300:
            el = self.element("IfcBuildingElementProxy", s.get("title", "Sign"), self.extrude(self.rect_profile(W, D), H),
                              self.placement((0, 0, 0)), s.get("face", "Sign"), sign_ps,
                              ("Qto_BuildingElementProxyQuantities", {"Width": W, "Height": H, "Depth": D,
                                                                      "NetVolume": round(W * H * D * 1e-9, 4)}), predefined="USERDEFINED")
            el.ObjectType = "SIGN"
            t = api.run("root.create_entity", self.f, ifc_class="IfcBuildingElementProxyType", name=f"{typ.upper()} {W:.0f}x{H:.0f}x{D:.0f}",
                        predefined_type="USERDEFINED")
            t.ElementType = "SIGN"
            api.run("type.assign_type", self.f, related_objects=[el], relating_type=t)
            api.run("spatial.assign_container", self.f, relating_structure=self.st, products=[el])
            return [el]

        # LOD 400
        asm = api.run("root.create_entity", self.f, ifc_class="IfcElementAssembly", name=s.get("title", "Sign assembly"), predefined_type="USERDEFINED")
        asm.ObjectType, asm.AssemblyPlace = "SIGN", "FACTORY"
        asm.ObjectPlacement = self.placement((0, 0, 0))
        for pn, props in sign_ps.items():
            ps = api.run("pset.add_pset", self.f, product=asm, name=pn)
            api.run("pset.edit_pset", self.f, pset=ps, properties={k: v for k, v in props.items() if v not in (None, "")})
        api.run("spatial.assign_container", self.f, relating_structure=self.st, products=[asm])

        fr = s["frame"]; sec, fmat = fr["section"], fr["material"]
        _, _, (fw, fd) = self.profile(sec)
        rail = fr.get("rail_section", sec)
        _, _, (rw, rd) = self.profile(rail)
        face_t = thk(s.get("face"), 4)
        ret = s.get("returns", "—")
        ret_t = thk(ret, 4) if ret and ret != "—" else 0
        back_t = thk(s.get("back"), 0) if s.get("back") else 0
        double = typ == "pylon"
        # frame inside the returns (same rule as shop_drawing.frame_envelope)
        x0 = ret_t; z0 = 0.0 if double else ret_t
        Wf = W - 2 * ret_t; Hf = H - ret_t * (1 if double else 2)
        xs = [x0 + v for v in member_positions(Wf, fw, fr.get("max_spacing", 600))]
        ys = [z0 + v for v in member_positions(Hf, fw, fr.get("max_spacing", 600))]
        if double:
            rows = [face_t + fd / 2, D - face_t - fd / 2]
        elif back_t:
            rows = [D - back_t - fd / 2]
        else:
            rows = [face_t + fd / 2]
        # F1 verticals
        for r_i, yc in enumerate(rows):
            for i, x in enumerate(xs):
                self.member("F1", sec, fmat, (x, yc, z0), (0, 0, 1), Hf)
        # F2 horizontals between verticals (centre-line levels ys)
        for yc in rows:
            for z in ys:
                for a, b in zip(xs[:-1], xs[1:]):
                    self.member("F2", rail, fmat, (a + fw / 2, yc, z), (1, 0, 0), b - a - fw, refx=(0, 0, 1))
        # faces
        fmat_face = s.get("face", "Face")
        self.plate("P1", "Face panel", fmat_face, face_t, (0, face_t, 0), W, H, (0, -1, 0), (1, 0, 0))
        if double:
            self.plate("P2", "Face panel (rear)", fmat_face, face_t, (W, D - face_t, 0), W, H, (0, 1, 0), (-1, 0, 0))
        if back_t:
            self.plate("BK1", "Back sheet", s["back"], back_t, (W, D - back_t, 0), W, H, (0, 1, 0), (-1, 0, 0))
        if ret_t:
            inner = D - face_t * (2 if double else 1) - back_t
            y0 = face_t
            self.plate("R1", "Return top", ret, ret_t, (0, y0, H - ret_t), W, inner, (0, 0, 1), (1, 0, 0))
            zb = 0 if double else ret_t  # pylon: no bottom return (frame passes to base plate)
            if not double:
                self.plate("R2", "Return bottom", ret, ret_t, (0, y0, 0), W, inner, (0, 0, 1), (1, 0, 0))
            self.plate("R3", "Return left", ret, ret_t, (0, y0, zb), inner, H - ret_t - zb, (1, 0, 0), (0, 1, 0))
            self.plate("R4", "Return right", ret, ret_t, (W - ret_t, y0, zb), inner, H - ret_t - zb, (1, 0, 0), (0, 1, 0))
        # LED array (lightbox / single-face boxes)
        if s.get("lighting") and not double and D > 60:
            yl = rows[0] - fd / 2 - 10
            self.plate("E1", "LED module array", "LED modules", 10, (W - x0 - fw, yl - 10, z0 + fw), Wf - 2 * fw, Hf - 2 * fw, (0, 1, 0), (-1, 0, 0),
                       "ASSUMED layout — per LED supplier", cls="IfcLightFixture", process="Electrical install")
        # base plates + anchors (pylon)
        if s.get("base"):
            b = s["base"]; pn = nums(b["plate"]); px, py, pt = pn[0], pn[1], pn[2]
            ad = nums(b.get("anchors", "4 x M24"))
            n_anc, d_anc = (int(ad[0]), ad[1]) if len(ad) >= 2 else (4, 24)
            emb = b.get("anchor_length", 400); edge = b.get("anchor_edge", 60)
            for i, x in enumerate(xs):
                self.plate("BP1", "Base plate", "Steel S275 HDG", pt, (x - px / 2, D / 2 - py / 2, -pt), px, py, (0, 0, 1), (1, 0, 0),
                           "ASSUMED count/position — confirm by structural engineer", process="Laser + drill")
                for (dx, dy) in [(-1, -1), (1, -1), (1, 1), (-1, 1)][:n_anc]:
                    # embedded length + plate thickness modelled; nut/projection above plate not modelled
                    self.anchor("A1", d_anc, emb + pt, (x + dx * (px / 2 - edge), D / 2 + dy * (py / 2 - edge), -pt - emb), (0, 0, 1))
        elif "anchor" in s.get("fixing", "").lower():
            ad = nums(s["fixing"]); n_anc, d_anc = (int(ad[0]), ad[1]) if len(ad) >= 2 else (4, 10)
            pts = [(xs[0], ys[0]), (xs[-1], ys[0]), (xs[-1], ys[-1]), (xs[0], ys[-1])][:n_anc]
            for x, z in pts:
                self.anchor("A1", d_anc, 100, (x, D - 20, z), (0, 1, 0))
        api.run("aggregate.assign_object", self.f, relating_object=asm, products=[p[-1] for p in self.parts])
        return [asm] + [p[-1] for p in self.parts]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("--lod", type=int, choices=[300, 400], default=400)
    ap.add_argument("-o", "--out"); ap.add_argument("--origin", nargs=3, type=float, default=[0, 0, 0])
    ap.add_argument("--rot", type=float, default=0, help="rotation about Z (deg)")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    b = B(spec, a.lod, a.origin, a.rot)
    els = b.build()
    out = a.out or f"{spec.get('drawing_no', 'SIGN')}-LOD{a.lod}.ifc"
    b.f.write(out)
    print(f"IFC4 LOD {a.lod}: {out} · elements {len(els)}")
    if b.parts:
        agg = {}
        for mark, prof, L, mat, w, _ in b.parts:
            k = (mark, prof, round(L), mat)
            agg[k] = (agg.get(k, (0, 0))[0] + 1, agg.get(k, (0, 0))[1] + w)
        print(f"  {'Mark':5s}{'Profile':18s}{'L mm':>8s}{'Qty':>5s}{'kg':>9s}  Material")
        for (mark, prof, L, mat), (n, w) in sorted(agg.items()):
            print(f"  {mark:5s}{prof[:17]:18s}{L:8d}{n:5d}{w:9.2f}  {mat[:40]}")
        print(f"  TOTAL weight {sum(p[4] for p in b.parts):.1f} kg (CALCULATED, corner radii ignored; ACP density ASSUMED)")


if __name__ == "__main__":
    main()
