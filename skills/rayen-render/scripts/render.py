#!/usr/bin/env python3
"""RAYEN render engine — scene JSON (mm, Z-up) -> photoreal PNG renders + .blend + .glb.

Uses Blender as a Python module (`pip install bpy`, Python 3.13 for bpy 5.x) or runs
inside Blender:  blender -b -P render.py -- scene.json -o out/
Falls back to a matplotlib massing preview when bpy is unavailable.

Also imports existing models: .glb/.gltf/.obj/.fbx/.stl, and .ifc via ifcopenshell
(BIM -> render bridge).  Run `render.py --example` for a full scene.
"""
import argparse, json, math, os, sys

# ---------------------------------------------------------------- materials
LIB = {  # name: (hex base colour, roughness, metallic, extra)
    "paint_white": ("#F2F0EB", 0.85, 0, {}),
    "paint_beige": ("#D9CBB2", 0.85, 0, {}),
    "paint_sand": ("#C8A97E", 0.9, 0, {}),
    "paint_charcoal": ("#3A3A3A", 0.8, 0, {}),
    "najdi_plaster": ("#C9A27A", 0.95, 0, {"noise": 0.08}),
    "marble_white": ("#E9E6E1", 0.15, 0, {"noise": 0.04}),
    "marble_black": ("#1E1E1F", 0.12, 0, {"noise": 0.05}),
    "terrazzo": ("#CFCAC2", 0.35, 0, {"noise": 0.12}),
    "porcelain_grey": ("#9C9A96", 0.3, 0, {}),
    "concrete": ("#8F8D88", 0.9, 0, {"noise": 0.1}),
    "travertine": ("#D8C7A8", 0.5, 0, {"noise": 0.08}),
    "walnut": ("#5A3B26", 0.45, 0, {"noise": 0.15}),
    "oak": ("#B08A5B", 0.5, 0, {"noise": 0.15}),
    "mdf_lacquer_white": ("#F4F4F2", 0.25, 0, {}),
    "fabric_grey": ("#7D7B78", 1.0, 0, {}),
    "fabric_green": ("#4E5E4A", 1.0, 0, {}),
    "leather_tan": ("#8B5A2B", 0.55, 0, {}),
    "steel_black": ("#141414", 0.4, 1, {}),
    "stainless": ("#C8C8C8", 0.2, 1, {}),
    "brushed_brass": ("#B08D57", 0.3, 1, {}),
    "aluminium": ("#BFC2C5", 0.35, 1, {}),
    "acp_silver": ("#B5B8BB", 0.3, 0.8, {}),
    "glass_clear": ("#FFFFFF", 0.0, 0, {"transmission": 1.0, "ior": 1.45}),
    "glass_frosted": ("#F5F5F5", 0.35, 0, {"transmission": 1.0, "ior": 1.45}),
    "acrylic_opal": ("#FFFFFF", 0.2, 0, {"transmission": 0.6, "emission": 0}),
    "mirror": ("#FFFFFF", 0.0, 1, {}),
    "led_white": ("#FFFFFF", 0.5, 0, {"emission": 15}),
    "led_warm": ("#FFD6A5", 0.5, 0, {"emission": 15}),
    "plant": ("#3F6B35", 0.7, 0, {}),
    "grass": ("#55803D", 0.95, 0, {}),
    "asphalt": ("#2E2E2E", 0.95, 0, {}),
}


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def kelvin_rgb(k):
    """Approximate blackbody colour (Tanner Helland), linear-ish 0..1."""
    t = k / 100
    r = 255 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(srgb2lin(max(0, min(255, v)) / 255) for v in (r, g, b))


def mat_def(name, scene_mats):
    if name in scene_mats:
        d = scene_mats[name]
        extra = {k: v for k, v in d.items() if k not in ("color", "roughness", "metallic")}
        return d.get("color", "#CCCCCC"), d.get("roughness", 0.5), d.get("metallic", 0), extra
    if name in LIB:
        return LIB[name]
    if isinstance(name, str) and name.startswith("#"):
        return name, 0.6, 0, {}
    print(f"  ! material '{name}' unknown -> grey (ASSUMED)")
    return "#AAAAAA", 0.6, 0, {}


# ---------------------------------------------------------------- example
EXAMPLE = {
    "name": "Newtech reception — concept",
    "status": "CONCEPTUAL — not for construction",
    "units": "mm",
    "room": {"width": 7000, "depth": 6000, "height": 3200, "floor": "marble_white",
             "walls": "paint_beige", "ceiling": "paint_white", "open_sides": ["front"]},
    "materials": {"brand_green": {"color": "#2F6B4F", "roughness": 0.6}},
    "objects": [
        {"type": "box", "name": "feature_wall_slats", "size": [4200, 60, 3200], "pos": [1400, 5940, 0], "material": "walnut",
         "array": {"count": 28, "step": [150, 0, 0], "size": [60, 60, 3200]}},
        {"type": "box", "name": "logo_panel", "size": [2400, 30, 700], "pos": [2300, 5880, 1700], "material": "brushed_brass"},
        {"type": "text", "name": "logo", "text": "NEWTECH", "height": 320, "depth": 40, "pos": [3500, 5860, 1880],
         "facing": "-y", "material": "led_white"},
        {"type": "box", "name": "counter_body", "size": [3000, 700, 1050], "pos": [2000, 3600, 0], "material": "mdf_lacquer_white"},
        {"type": "box", "name": "counter_top", "size": [3100, 800, 30], "pos": [1950, 3550, 1050], "material": "marble_black"},
        {"type": "box", "name": "counter_led", "size": [3000, 10, 20], "pos": [2000, 3590, 80], "material": "led_warm"},
        {"type": "box", "name": "sofa", "size": [2200, 850, 420], "pos": [400, 600, 0], "material": "fabric_green"},
        {"type": "box", "name": "sofa_back", "size": [2200, 200, 400], "pos": [400, 600, 420], "material": "fabric_green"},
        {"type": "cylinder", "name": "coffee_table", "radius": 450, "height": 380, "pos": [1500, 2000, 0], "material": "travertine"},
        {"type": "cylinder", "name": "planter", "radius": 300, "height": 600, "pos": [6300, 5300, 0], "material": "concrete"},
        {"type": "sphere", "name": "plant", "radius": 550, "pos": [6300, 5300, 1150], "material": "plant"},
    ],
    "lights": [
        {"type": "area", "pos": [3500, 3000, 3150], "size": [4000, 3000], "watts": 900, "kelvin": 4000},
        {"type": "spot", "pos": [3500, 4800, 3150], "target": [3500, 5900, 2000], "watts": 400, "kelvin": 3000, "angle": 40},
        {"type": "sun", "angle": [50, 0, 160], "strength": 3, "kelvin": 5500},
    ],
    "cameras": [
        {"name": "V01_entrance", "pos": [3500, -2500, 1600], "target": [3500, 4000, 1300], "lens": 24},
        {"name": "V02_corner", "pos": [6500, 500, 1700], "target": [2500, 4500, 1000], "lens": 20},
    ],
    "render": {"engine": "CYCLES", "samples": 96, "resolution": [1600, 1000], "exposure": 0.0,
               "view_transform": "AgX", "world_color": "#DDE6EE", "world_strength": 0.6},
}


# ---------------------------------------------------------------- blender build
def build_blender(scene, outdir, args):
    import bpy
    from mathutils import Vector
    S = 0.001  # mm -> m
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cache = {}

    def material(name):
        if name in cache:
            return cache[name]
        col, rough, metal, extra = mat_def(name, scene.get("materials", {}))
        m = bpy.data.materials.new(str(name))
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        rgb = tuple(srgb2lin(c) for c in hex2rgb(col)) + (1,)
        bsdf.inputs["Base Color"].default_value = rgb
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if extra.get("transmission"):
            for k in ("Transmission Weight", "Transmission"):
                if k in bsdf.inputs:
                    bsdf.inputs[k].default_value = extra["transmission"]
                    break
            bsdf.inputs["IOR"].default_value = extra.get("ior", 1.45)
        if extra.get("emission"):
            for k in ("Emission Color", "Emission"):
                if k in bsdf.inputs:
                    bsdf.inputs[k].default_value = rgb
                    break
            bsdf.inputs["Emission Strength"].default_value = extra["emission"]
        if extra.get("noise"):  # subtle variation so stone/wood is not flat
            tex = nt.nodes.new("ShaderNodeTexNoise")
            tex.inputs["Scale"].default_value = 8.0
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.inputs["Factor"].default_value = extra["noise"]
            mix.inputs[6].default_value = rgb
            nt.links.new(tex.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        cache[name] = m
        return m

    def put(obj, mat, rot_z=0):
        obj.data.materials.append(material(mat))
        obj.rotation_euler[2] = math.radians(rot_z)
        return obj

    def box(name, size, pos, mat, rot_z=0):
        w, d, h = size
        x, y, z = pos
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x + w / 2) * S, (y + d / 2) * S, (z + h / 2) * S))
        o = bpy.context.active_object
        o.name = name
        o.scale = (w * S, d * S, h * S)
        bpy.ops.object.transform_apply(scale=True)
        if args.bevel and min(size) > 15:
            mod = o.modifiers.new("bevel", "BEVEL")
            mod.width = 0.002
            mod.segments = 2
        return put(o, mat, rot_z)

    # room shell
    r = scene.get("room")
    if r:
        W, D, H = r["width"], r["depth"], r["height"]
        t = r.get("wall_thickness", 150)
        openings = set(r.get("open_sides", ["front"]))
        box("floor", [W + 2 * t, D + 2 * t, 50], [-t, -t, -50], r.get("floor", "porcelain_grey"))
        if "ceiling" not in openings:
            box("ceiling", [W + 2 * t, D + 2 * t, 50], [-t, -t, H], r.get("ceiling", "paint_white"))
        walls = {"back": ([W, t, H], [0, D, 0]), "front": ([W, t, H], [0, -t, 0]),
                 "left": ([t, D, H], [-t, 0, 0]), "right": ([t, D, H], [W, 0, 0])}
        for side, (sz, ps) in walls.items():
            if side not in openings:
                box(f"wall_{side}", sz, ps, r.get("walls", "paint_white"))

    # objects
    for i, ob in enumerate(scene.get("objects", [])):
        typ, name, mat = ob["type"], ob.get("name", f"obj{i}"), ob.get("material", "paint_white")
        pos = ob.get("pos", [0, 0, 0])
        rz = ob.get("rot_z", 0)
        if typ == "box":
            if "array" in ob:
                a = ob["array"]
                for k in range(a["count"]):
                    p = [pos[j] + a["step"][j] * k for j in range(3)]
                    box(f"{name}_{k+1:02d}", a.get("size", ob["size"]), p, mat, rz)
            else:
                box(name, ob["size"], pos, mat, rz)
        elif typ == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=ob["radius"] * S, depth=ob["height"] * S,
                                                location=(pos[0] * S, pos[1] * S, (pos[2] + ob["height"] / 2) * S))
            o = bpy.context.active_object; o.name = name; put(o, mat, rz)
            bpy.ops.object.shade_smooth()
        elif typ == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=ob["radius"] * S,
                                                 location=tuple(v * S for v in pos))
            o = bpy.context.active_object; o.name = name; put(o, mat)
            bpy.ops.object.shade_smooth()
        elif typ == "text":
            bpy.ops.object.text_add(location=tuple(v * S for v in pos))
            o = bpy.context.active_object; o.name = name
            o.data.body = ob["text"]
            o.data.size = ob.get("height", 200) * S
            o.data.extrude = ob.get("depth", 20) * S / 2
            o.data.align_x = "CENTER"
            if ob.get("font"):
                o.data.font = bpy.data.fonts.load(ob["font"])
            face = ob.get("facing", "-y")
            o.rotation_euler = {"-y": (math.pi / 2, 0, 0), "+y": (math.pi / 2, 0, math.pi),
                                "up": (0, 0, 0)}.get(face, (math.pi / 2, 0, 0))
            o.data.materials.append(material(mat))
            if any("؀" <= ch <= "ۿ" for ch in ob["text"]):
                print("  ! Arabic text: Blender does not shape Arabic. Use an SVG/DXF logo via 'import' instead.")
        elif typ == "import":
            import_file(bpy, ob, S, material)
        else:
            print(f"  ! unknown object type {typ} skipped")

    for imp in scene.get("imports", []):
        import_file(bpy, imp, S, material)

    # lights
    for i, L in enumerate(scene.get("lights", [])):
        col = kelvin_rgb(L.get("kelvin", 4000))
        if L["type"] == "sun":
            ld = bpy.data.lights.new(f"sun{i}", "SUN"); ld.energy = L.get("strength", 3); ld.angle = math.radians(1.5)
            o = bpy.data.objects.new(f"sun{i}", ld)
            o.rotation_euler = tuple(math.radians(a) for a in L.get("angle", [50, 0, 160]))
        else:
            kind = {"area": "AREA", "spot": "SPOT", "point": "POINT"}[L["type"]]
            ld = bpy.data.lights.new(f"light{i}", kind); ld.energy = L.get("watts", 100)
            if kind == "AREA":
                ld.shape = "RECTANGLE"; ld.size, ld.size_y = (v * S for v in L.get("size", [1000, 1000]))
            if kind == "SPOT":
                ld.spot_size = math.radians(L.get("angle", 40)); ld.spot_blend = 0.4
            o = bpy.data.objects.new(f"light{i}", ld)
            o.location = tuple(v * S for v in L["pos"])
            if "target" in L:
                d = Vector(tuple(v * S for v in L["target"])) - o.location
                o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        ld.color = col
        sc.collection.objects.link(o)

    # world
    R = scene.get("render", {})
    world = bpy.data.worlds.new("world"); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = tuple(srgb2lin(c) for c in hex2rgb(R.get("world_color", "#DDE6EE"))) + (1,)
    bg.inputs[1].default_value = R.get("world_strength", 0.6)

    # render settings
    eng = R.get("engine", "CYCLES").upper()
    if args.draft:
        eng = "CYCLES"
    if eng != "CYCLES" and not args.gpu:
        print("  ! EEVEE needs a GPU/OpenGL context — using Cycles (pass --gpu on a workstation to keep EEVEE)")
        eng = "CYCLES"
    sc.render.engine = "CYCLES" if eng == "CYCLES" else "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in \
        [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = 16 if args.draft else R.get("samples", 96)
        sc.cycles.use_denoising = True
        sc.cycles.device = "GPU" if args.gpu else "CPU"
    res = R.get("resolution", [1600, 1000])
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 40 if args.draft else 100
    try:
        sc.view_settings.view_transform = R.get("view_transform", "AgX")
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    sc.view_settings.exposure = R.get("exposure", 0.0)
    sc.render.image_settings.file_format = "PNG"

    os.makedirs(outdir, exist_ok=True)
    base = args.name or scene.get("name", "render").split("—")[0].strip().replace(" ", "_")
    outs = []
    for c in scene.get("cameras", []):
        cd = bpy.data.cameras.new(c["name"]); cd.lens = c.get("lens", 24); cd.clip_end = 1000
        co = bpy.data.objects.new(c["name"], cd); sc.collection.objects.link(co)
        co.location = tuple(v * S for v in c["pos"])
        d = Vector(tuple(v * S for v in c["target"])) - co.location
        co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        sc.camera = co
        if args.no_render:
            continue
        p = os.path.join(outdir, f"{base}_{c['name']}.png")
        sc.render.filepath = p
        print(f"  rendering {c['name']} ({sc.render.engine}) ...", flush=True)
        bpy.ops.render.render(write_still=True)
        outs.append(p)
    blend = os.path.join(outdir, f"{base}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
    glb = os.path.join(outdir, f"{base}.glb")
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.abspath(glb), export_format="GLB", export_lights=False, export_cameras=True)
        outs.append(glb)
    except Exception as e:
        print("  ! glb export failed:", e)
    outs.append(blend)
    return outs


def import_file(bpy, ob, S, material):
    f = ob["file"]
    ext = os.path.splitext(f)[1].lower()
    before = set(bpy.data.objects)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=f)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=f)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=f)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=f)
    elif ext == ".ifc":
        import_ifc(bpy, f, material, ob.get("material_map", {}))
    elif ext == ".svg":
        try:
            bpy.ops.wm.svg_import(filepath=f)
        except Exception:
            bpy.ops.import_curve.svg(filepath=f)
    else:
        print(f"  ! unsupported import {f}"); return
    new = set(bpy.data.objects) - before
    unit = ob.get("file_units_mm", 1000 if ext in (".glb", ".gltf", ".fbx", ".ifc") else 1)  # mm per file unit
    pos = ob.get("pos", [0, 0, 0])
    for o in new:
        if o.parent is None:
            if ext not in (".glb", ".gltf", ".fbx", ".ifc"):
                o.scale = tuple(v * unit * S for v in o.scale)
            o.location = (o.location[0] + pos[0] * S, o.location[1] + pos[1] * S, o.location[2] + pos[2] * S)
            o.rotation_euler[2] += math.radians(ob.get("rot_z", 0))
        if ob.get("material") and o.type in ("MESH", "CURVE"):
            o.data.materials.clear(); o.data.materials.append(material(ob["material"]))
    print(f"  imported {f}: {len(new)} objects")


IFC_DEFAULT = {"IfcWall": "paint_white", "IfcWallStandardCase": "paint_white", "IfcSlab": "concrete",
               "IfcColumn": "concrete", "IfcBeam": "concrete", "IfcWindow": "glass_clear", "IfcDoor": "oak",
               "IfcRoof": "concrete", "IfcStair": "concrete", "IfcRailing": "steel_black", "IfcCovering": "paint_white",
               "IfcPlate": "glass_clear", "IfcMember": "aluminium", "IfcFurnishingElement": "oak"}


def import_ifc(bpy, path, material, mmap):
    import ifcopenshell, ifcopenshell.geom
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)
    f = ifcopenshell.open(path)
    it = ifcopenshell.geom.iterator(st, f, os.cpu_count() or 2)
    n = 0
    if it.initialize():
        while True:
            sh = it.get()
            el = f.by_id(sh.id)
            if el.is_a() in ("IfcSpace", "IfcOpeningElement", "IfcSite"):
                if not it.next(): break
                continue
            v, fc = sh.geometry.verts, sh.geometry.faces
            verts = [tuple(v[i:i + 3]) for i in range(0, len(v), 3)]
            faces = [tuple(fc[i:i + 3]) for i in range(0, len(fc), 3)]
            me = bpy.data.meshes.new(f"{el.is_a()}_{sh.id}")
            me.from_pydata(verts, [], faces)
            o = bpy.data.objects.new(f"{el.is_a()}:{getattr(el, 'Name', '') or sh.id}", me)
            bpy.context.scene.collection.objects.link(o)
            o.data.materials.append(material(mmap.get(el.is_a(), IFC_DEFAULT.get(el.is_a(), "paint_white"))))
            n += 1
            if not it.next():
                break
    print(f"  IFC: {n} elements meshed")


# ---------------------------------------------------------------- fallback preview
def preview_matplotlib(scene, outdir, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(12, 8), dpi=150)
    ax = fig.add_subplot(111, projection="3d")

    def cube(sz, p, col):
        w, d, h = sz; x, y, z = p
        V = [(x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z),
             (x, y, z + h), (x + w, y, z + h), (x + w, y + d, z + h), (x, y + d, z + h)]
        F = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4]]
        ax.add_collection3d(Poly3DCollection([[V[i] for i in f] for f in F], facecolor=col, edgecolor="#333", lw=0.2, alpha=0.95))

    r = scene.get("room")
    if r:
        cube([r["width"], r["depth"], 20], [0, 0, -20], hex2rgb(mat_def(r.get("floor", "porcelain_grey"), {})[0]))
    for ob in scene.get("objects", []):
        col = hex2rgb(mat_def(ob.get("material", "paint_white"), scene.get("materials", {}))[0])
        p = ob.get("pos", [0, 0, 0])
        if ob["type"] == "box":
            if "array" in ob:
                a = ob["array"]
                for k in range(a["count"]):
                    cube(a.get("size", ob["size"]), [p[j] + a["step"][j] * k for j in range(3)], col)
            else:
                cube(ob["size"], p, col)
        elif ob["type"] in ("cylinder", "sphere"):
            rr = ob["radius"]; h = ob.get("height", 2 * rr)
            z0 = p[2] if ob["type"] == "cylinder" else p[2] - rr
            cube([2 * rr, 2 * rr, h], [p[0] - rr, p[1] - rr, z0], col)
    if r:
        ax.set_xlim(0, r["width"]); ax.set_ylim(0, r["depth"]); ax.set_zlim(0, r["height"])
        ax.set_box_aspect((r["width"], r["depth"], r["height"]))
    ax.view_init(25, -60)
    ax.set_title(f"{scene.get('name', '')}\nMASSING PREVIEW (bpy not installed) — {scene.get('status', 'CONCEPTUAL')}")
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, (args.name or "preview") + "_massing.png")
    fig.savefig(p, bbox_inches="tight"); print("  saved", p)
    return [p]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", nargs="?")
    ap.add_argument("-o", "--outdir", default="renders")
    ap.add_argument("--name")
    ap.add_argument("--draft", action="store_true", help="fast low-res check (16 samples, 40%%)")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--no-render", action="store_true", help="build .blend/.glb only")
    ap.add_argument("--no-bevel", dest="bevel", action="store_false")
    ap.add_argument("--preview", action="store_true", help="force matplotlib massing preview")
    ap.add_argument("--example", action="store_true")
    a = ap.parse_args(argv)
    if a.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False)); return
    if not a.scene:
        ap.error("scene JSON required (or --example)")
    scene = json.load(open(a.scene, encoding="utf-8"))
    try:
        if a.preview:
            raise ImportError
        import bpy  # noqa
        outs = build_blender(scene, a.outdir, a)
    except ImportError:
        print("bpy not available -> massing preview only. Install: pip install bpy  (or run inside Blender)")
        outs = preview_matplotlib(scene, a.outdir, a)
    print("OUTPUTS:"); [print("  ", o) for o in outs]


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
