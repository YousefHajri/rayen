---
name: rayen-interior-design
description: "RAYEN interior design & fit-out engine — offices, showrooms, retail, F&B, hospitality, majlis, villas, exhibition stands, reception and brand environments. This skill should be used when the user asks for \"interior design\", \"fit-out\", \"layout\", \"furniture plan\", \"reflected ceiling plan\", \"RCP\", \"lighting design\", \"lux\", \"finishes schedule\", \"FF&E\", \"material board\", \"mood board\", \"joinery\", \"feature wall\", \"ceiling detail\", \"partition\", \"acoustic\", \"majlis\", \"reception counter\", \"تصميم داخلي\", \"فرش\", \"توزيع أثاث\", \"سقف مستعار\", \"إضاءة\", \"جدول تشطيبات\", \"ديكور\", \"مجلس\", \"كاونتر استقبال\", \"جدار مميز\", or sends a room photo / plan. Produces layouts (DXF), RCP, lighting calc (XLSX), finishes & FF&E schedules (XLSX), joinery details, renders (rayen-render) and boards in Newtech identity.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Interior Design & Fit-out

Interior design that a joinery shop, a ceiling contractor and an electrician can build without calling back. Read only what the task needs:

| Task | Reference |
|---|---|
| Space planning, furniture, ergonomics, majlis, retail, F&B | `references/space-ergonomics.md` |
| Finishes, FF&E, fire class, acoustics, slip, durability | `references/finishes-ffe.md` |
| Lighting design, lux, CCT, CRI, UGR, controls | `references/lighting.md` |
| Joinery, gypsum ceilings & partitions, details, tolerances | `references/joinery-ceilings-partitions.md` |

## Workflow
1. **Survey & brief** — existing condition (site photos, as-built, measured survey: VERIFIED only if measured), brand guidelines, user count, operations, budget class, programme, landlord fit-out manual (mall / tower rules), authority (Civil Defense, Balady).
2. **Concept** — 2–3 directions: narrative, palette (60/30/10), material board, lighting mood, key feature (reception, feature wall, ceiling). Use Canva / Figma / Gamma connectors for boards; `rayen-render` for 3D views (same camera for every option).
3. **Layout** — zoning, circulation (main aisles ≥ 1200–1500, secondary ≥ 900), furniture plan with clearances, accessible route, egress kept clear, MEP points (power/data/floor boxes), FF&E tags.
4. **RCP & lighting** — ceiling types and levels, bulkheads, access panels, diffusers/grilles, sprinklers & detectors coordination (zones not to clash), luminaire layout from `python3 scripts/lighting_calc.py rooms.json -o <Project>-Lighting.xlsx` (lumen method; final by DIALux/Relux with real IES files).
5. **Finishes & FF&E schedules** — codes (e.g. FL-01, WL-02, CL-01, JN-01, FF-01) → material, supplier/basis, finish, fire class, location, area/qty (qty via `rayen-boq-qto`).
6. **Details** — joinery elevations/sections, ceiling details, partition types, floor transitions, feature-wall build-ups — every detail answers WHAT / SIZE / MATERIAL / FIXING / FINISH / TOLERANCE / ACCESS. Hand production items (acrylic, ACP, steel, MDF CNC) to `rayen-fabrication`.
7. **Package** — compose sheets in the original Newtech identity with `rayen-newtech-template`; BOQ via `rayen-boq-qto`; submittals via `rayen-rfi-submittal`.

## Rules
- Fire: interior finish class, fire-rated doors/partitions and ceiling penetrations follow SBC 801/201 and the fire strategy — state "verify class with Civil Defense / fire consultant".
- Never block exits, extinguishers, hose reels, FA devices, sprinkler spray patterns or access panels with joinery or signage.
- Lighting numbers are CALCULATED with estimated UF unless photometric data is supplied.
- Brand: approved logo/colour/typography are fixed; propose, don't alter.
- Wet areas: waterproofing, moisture-resistant boards (MR/green board, HMR MDF), slip-resistant floors.
