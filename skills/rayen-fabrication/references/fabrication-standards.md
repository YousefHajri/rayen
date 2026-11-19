# Fabrication standards for signage & fit-out (typical — confirm with workshop and spec)

## Processes & typical capability
| Process | Materials | Notes |
|---|---|---|
| Fibre laser | Steel ≤ 20, SS ≤ 12, Al ≤ 10 mm (machine-dependent) | Kerf 0.1–0.3; min hole ≈ thickness; micro-joints for small parts |
| CO₂ laser | Acrylic ≤ 20–25, MDF ≤ 12, fabric/vinyl | Flame-polished acrylic edges; MDF char edges need sanding/paint |
| CNC router | Acrylic, ACP, MDF, plywood, Al ≤ 6 | Tool Ø 3–6 → inside corners have radius = tool/2; V-groove for ACP folding |
| Press brake | Steel, SS, Al sheet | Min flange ≈ 4×t + R; holes ≥ 2×t + R from bend |
| Channel-letter bender | Al coil 0.6–1.2, SS 0.6–1.0 | Notching for tight corners; return depth per LED/sign spec |
| Welding | MIG/TIG/MMA | Steel E70XX / ER70S-6; Al ER4043/5356; SS 308L |
| Finishing | Powder coat, PVDF, wet paint, HDG, PVD | HDG ≥ 85 µm (ASTM A123 typical); vent/drain holes for HDG hollow sections |

## Bend data (starting values — verify with a test bend)
K-factor: soft Al 0.33–0.40 · mild steel 0.40–0.45 (air bending R ≈ t) · SS 0.45.
BA(90°) = π/2·(R + K·t) · OSSB = R + t · BD = 2·OSSB − BA · flat = Σ outside dims − n·BD.
Min inner R: Al 5052 ≈ 1t, Al 6061-T6 ≈ 2–3t (prefer 5052 for bent parts), mild steel ≈ 1t, SS ≈ 1–1.5t.

## ACP cassettes
4 mm ACP (0.5 mm skins for façades), fire-rated core (FR/A2) where façade fire rules apply — VERIFY with Civil Defense. Rout V-groove leaving ≈ 0.3–0.5 mm of core + skin, fold 90°, rivet corner angles, hang on a stiffened aluminium subframe; joint 10–15 mm with backer rod + sealant, or open joint with EPDM; keep the direction arrows of coated panels the same across a façade.

## Acrylic
Cast acrylic for laser/engraving and lit faces; extruded for cost (more stress cracking). Expansion ≈ 0.07 mm/m/°C → a 2400 mm face over 40 °C moves ≈ 6.7 mm: oversized/slotted holes, floating fixing. LED-to-face distance ≈ 1–1.5× module pitch for even light (opal 3–5 mm). No solvent cleaners; keep protective film until installation.

## Steel frames for signs
RHS/SHS S275/S355 (by engineer), welded or bolted; base plates, anchors and welds sized by the engineer; HDG, or primer + PU paint; earthing lug for lit signs; drain holes in hollow sections; lifting points marked; max transport size (≈ 2.5 m wide, 12 m long on a standard trailer — confirm) sets the split joints.

## Tolerances (typical factory)
Laser/CNC cut ±0.2–0.5 mm · bend angle ±1° · bent flange ±0.5–1 mm · welded frame overall ±2 mm, diagonal difference ≤ 3 mm · face flatness ≤ L/500 · hole position ±0.5 mm.

## Electrical (lit signage)
LED modules IP65+ outdoors, SELV 12/24 V; outdoor-rated PSU loaded ≤ 80 %; cable lengths checked for voltage drop; drainage + ventilation; isolator / photocell / timer; RCD protection and earthing per SBC 401 — by a licensed electrician.

## QA / ITP checkpoints
Material receiving (certificate, thickness, coating) → first-article check of CNC parts → bend test piece → weld visual (+ NDT where specified) → coating thickness (DFT) → dry assembly & light test (uniformity, hotspots, colour) → protection & packing → site installation inspection.
