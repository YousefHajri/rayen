---
name: rayen-boq-qto
description: "RAYEN quantity take-off and BOQ engine for Newtech signage, displays and fit-out. This skill should be used when the user asks to \"calculate quantities\", \"prepare a BOQ\", \"QTO\", \"cutting list\", \"how many sheets\", \"steel weight\", \"nesting\", \"material take-off\", \"cost estimate\", \"pricing\", \"value engineering\", \"احسب الكميات\", \"جدول كميات\", \"قائمة قص\", \"كم لوح\", \"وزن الحديد\", or when a drawing must be turned into quantities. Produces a traceable XLSX with live formulas, waste shown separately, sheet nesting and a conflicts/assumptions register.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — BOQ / QTO

Turn drawings, specs or the user's description into a traceable, formula-driven BOQ. Never hand-type large quantity tables: build the take-off JSON and run the engine.

## Workflow

1. **Collect inputs from the source.** For each element record: description, material/section, unit, dimensions (m), count, source (drawing no. + rev + view), status tag. Read `../rayen/references/boq-cost-ve.md` for measurement rules and `../rayen/references/newtech-context.md` for stock sizes and default waste.
2. **Choose the unit per item:**

   | Unit | Use for | Required fields |
   |---|---|---|
   | `kg` | Steel/aluminum sections | `section` (e.g. `SHS 100x100x4`, `RHS 60x40x3`, `CHS 48.3x3`, `L 50x50x5`, `PL 400x400x20`), `length_m`, `count` |
   | `m` | Profiles, trims, LED strip, sealant runs | `length_m`, `count` |
   | `m2` | Vinyl, paint, cladding by area | `length_m`, `width_m`, `count` |
   | `nos` | Fixings, PSUs, LED modules, accessories | `count` |
   | `sheet` | Acrylic, ACP, MDF, aluminum sheet | `stock` [w,h] mm, `kerf_mm`, `allow_rotation` (false if grain/print direction matters), `pieces` [{w,h,n}] mm |

3. **Write the JSON** (start from `examples/pylon-takeoff.json` or `python3 scripts/qto.py --example`). Put drawing conflicts in `conflicts` and every assumption in `assumptions`. Add `rate` only with a price basis in `source` (quotation ref, market estimate, or "budgetary").
4. **Run:** `python3 scripts/qto.py takeoff.json -o <Project>-BOQ-<Rev>.xlsx`. The script prints an independent Python re-computation; then recalculate the workbook with the xlsx skill's `recalc.py` and confirm zero formula errors and that totals match the printout.
5. **If a shop drawing exists from `rayen-shop-drawing`,** start from its `--qto` JSON so drawing and BOQ stay identical, then add finishes, fixings, electrical and consumables.
6. **Report** in chat: total by trade, the top 3 cost drivers, sheets to buy and utilisation, items still ASSUMED / TO BE CONFIRMED, and any conflict needing an RFI (hand to `rayen-rfi-submittal`).

## Rules

- Net measured quantity ≠ waste ≠ procurement quantity — keep all three visible.
- Steel kg/m is computed from the section ignoring corner radii (≈1–3% conservative); state this when weights drive price.
- Shelf nesting is a planning estimate; final cutting must be checked on the CNC nesting software.
- Never present an estimate as a quotation. Search current Saudi market prices when pricing matters and label them.
- Value engineering: offer at most three options (A preserve design, B VE, C balanced) with cost delta and performance trade-off; never reduce structural, fire or electrical safety to save cost.
