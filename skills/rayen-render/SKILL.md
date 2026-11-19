---
name: rayen-render
description: "RAYEN photoreal rendering & visualization — Blender (Cycles/EEVEE) driven from a JSON scene, plus import of IFC/GLB/OBJ/FBX/STL/SVG models, day/night signage lighting, material library (marble, walnut, brass, acrylic, LED, ACP, glass…), multiple cameras, .blend and .glb export. This skill should be used when the user asks for a \"render\", \"3D view\", \"perspective\", \"visualization\", \"before/after\", \"night view\", \"walkthrough still\", \"mood render\", \"رندر\", \"منظور\", \"تصور ثلاثي الأبعاد\", \"لقطة ليلية\", or wants to see a design, a sign on a façade, a BIM model or a fit-out concept.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Render

`scripts/render.py` builds a real 3D scene in Blender and renders it. Coordinates in **mm**, Z up, origin at room corner (x = width, y = depth).

```
python3 scripts/render.py --example > scene.json        # full reception example
python3 scripts/render.py scene.json -o renders --draft  # 16 samples, 40 % — check composition
python3 scripts/render.py scene.json -o renders          # final (samples/resolution from scene)
python3 scripts/render.py scene.json -o renders --gpu    # on a machine with a GPU
```
Outputs: `<name>_<camera>.png` per camera, `<name>.blend` (open in Blender, refine), `<name>.glb` (SketchUp/Twinmotion/Enscape/web viewers).

## Scene JSON
- `room`: width/depth/height, floor/walls/ceiling materials, `open_sides` (["front"] leaves the camera side open).
- `objects[]`: `box` (size, pos = min corner, rot_z, optional `array` {count, step, size} for slats/fins/louvres), `cylinder` (radius, height, pos = base centre), `sphere`, `text` (Latin text, height, depth, facing, font .ttf), `import` (file, pos, rot_z, material override, `file_units_mm`).
- `imports[]`: whole models — **.ifc** (meshed through ifcopenshell, materials by IFC class or `material_map`), .glb/.gltf, .obj, .fbx, .stl, .svg (logos — use this for Arabic logos: Blender does not shape Arabic text).
- `materials{}`: custom `{"color":"#hex","roughness":..,"metallic":..,"emission":..,"transmission":..}`; built-in library: paint_white/beige/sand/charcoal, najdi_plaster, marble_white/black, terrazzo, porcelain_grey, concrete, travertine, walnut, oak, mdf_lacquer_white, fabric_grey/green, leather_tan, steel_black, stainless, brushed_brass, aluminium, acp_silver, glass_clear/frosted, acrylic_opal, mirror, led_white, led_warm, plant, grass, asphalt; any `#hex` works too.
- `lights[]`: `area` (pos, size, watts, kelvin), `spot` (pos, target, angle, watts, kelvin), `point`, `sun` (angle [x,y,z] deg, strength).
- `cameras[]`: name, pos, target, lens (mm; 18–24 interiors, 35–50 façades).
- `render`: engine CYCLES/EEVEE, samples, resolution, exposure, view_transform (AgX), world_color/strength.

## Workflow
1. Build the scene from VERIFIED dimensions (drawings) — label anything else ASSUMED; brand colours from brand guide.
2. `--draft` first → open the PNG and check composition, scale, light; then final render.
3. Night views of signage: world_strength 0.02–0.05, LED materials emission 10–30, sun removed.
4. Same camera set for every option (A/B/C) so the client compares like with like.
5. Mark every render **CONCEPTUAL — not for construction** in the sheet (`rayen-newtech-template`).
6. Alternatives when Blender is not available: matplotlib massing preview (automatic fallback), the Trimble SketchUp connector (`build_model` → model), Canva/Gamma/Figma `generate_image` for mood images (label AI-generated, never as design evidence).

## Limits
Physically based but not photometrically certified — lux levels come from `rayen-interior-design` lighting calc / DIALux, not from renders. Install: `pip install bpy` (Python 3.13 for bpy 5.x) or run inside Blender: `blender -b -P render.py -- scene.json -o out`.
