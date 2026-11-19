---
name: rayen-fabrication
description: "RAYEN fabrication drawings & CNC production for Newtech's factory — parts drawings, CNC/laser/router-ready DXF (one part per file, CUT/DRILL/BEND/ENGRAVE layers), sheet-metal flat patterns with bend allowance & K-factor, channel-letter return developed lengths, brackets, trays, acrylic faces, ACP cassettes, steel frames, assembly & welding notes, parts lists and nesting take-off. This skill should be used when the user asks for \"fabrication drawing\", \"workshop drawing\", \"CNC file\", \"laser file\", \"cutting file\", \"flat pattern\", \"unfold\", \"bend allowance\", \"parts list\", \"assembly drawing\", \"welding detail\", \"ACP cassette\", \"channel letter returns\", \"مخططات تصنيع\", \"ملف ليزر\", \"ملف CNC\", \"فرد الصاج\", \"ثني\", \"قائمة قطع\", \"تفاصيل لحام\". Outputs drop straight into the original Newtech sheet template.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Fabrication Drawings & CNC

Read `references/fabrication-standards.md` (processes, tolerances, bend tables, welding, finishing, QA) before producing.

## Generator
`scripts/fab_parts.py` — parts JSON → per-part CNC DXF + parts sheet (DXF/PNG with dims) + parts list XLSX + optional take-off JSON for nesting in `rayen-boq-qto`.
```
python3 scripts/fab_parts.py --example > parts.json
python3 scripts/fab_parts.py parts.json -o fab --qto fab/parts-qto.json
```
Part kinds: `plate` (rect with corner radius or polygon; holes, perimeter `hole_pattern`, slots, bends, engrave), `tray` (box/tray flat pattern: W, H, F outside, thickness, R, K, relief holes; holes given from outside corner of the finished base), `strip` (bent return: segments on outline, angles, depth, back flange → developed length).

## Fabrication package (order of sheets)
1. GA / assembly (from `rayen-shop-drawing`): elevations, sections, exploded/isometric, part marks.
2. Parts drawings: each part with mark, material, thickness, qty, finish, process, dims, holes, bends (UP/DOWN, angle, inner R).
3. Flat patterns / CNC files list (file name = `<DWG>-<MARK>-t<thk>.dxf`).
4. Welding & connection details: weld type/size/length, bolt grade, torque (from engineer), galvanising/painting.
5. Electrical: LED module layout, PSU sizing (load × 1.2–1.25 margin), cable route, access.
6. Parts list + cutting list + hardware schedule.
7. QA/ITP checkpoints (cut, bend, weld, finish, assembly, light test, packing).
Compose the whole set in the original Newtech identity with `rayen-newtech-template` (cover → sheets → closing page).

## Rules
- CNC DXF: units mm, 1:1, closed polylines only on CUT/CUT-IN, no dims/text on cut layers, one part per file at origin, arcs not exploded into thousands of segments, kerf/tool offset applied by CAM — not in the drawing (state this).
- Flat patterns are CALCULATED: confirm K-factor/bend deduction with the press-brake test piece for the actual material, thickness and tooling before batch cutting.
- Structural items (pylons, elevated frames, base plates, anchors, welds carrying load) — sizes from the structural engineer's approved calculation only.
- Never release "for fabrication" while dimensions are ASSUMED/TO BE CONFIRMED — status stays FOR APPROVAL.
