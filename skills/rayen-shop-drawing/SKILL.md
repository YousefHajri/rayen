---
name: rayen-shop-drawing
description: "RAYEN shop-drawing production for Newtech signage, lightboxes, pylons, graphic frames and fit-out details. This skill should be used when the user asks to \"make a shop drawing\", \"draw this detail\", \"prepare DXF\", \"AutoCAD file\", \"fabrication drawing\", \"section through the sign\", \"title block\", \"ارسم\", \"شوب دروينج\", \"مخطط تنفيذي\", \"تفصيلة\", or to review an existing shop drawing for completeness. Produces a layered, real-scale DXF plus PDF/PNG preview and a matching take-off JSON for the BOQ.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Shop Drawings

Produce editable, dimensioned, layered drawings — not illustrations. Read `../rayen/references/shop-drawings.md` (content checklist) and `../rayen/references/structure-fabrication.md` (connections, signage structure) before drawing.

## Generator (parametric)

`scripts/shop_drawing.py` builds an A3 sheet in model space (1:1 mm) with: front elevation with hidden internal frame and member spacing dims, section A-A with face/frame/returns and leader notes, base/foundation notes for pylons, material & cutting schedule, general notes, and a Newtech title block (DWG no., rev, scale, date, drawn/checked, client, status).

Supported `type`: `lightbox`, `pylon`, `graphic_frame`. Start from `examples/<type>.json` or `python3 scripts/shop_drawing.py --example <type>`.

Key spec fields: `width`, `height`, `depth` (mm) · `frame.section`, `frame.material`, `frame.max_spacing`, `frame.rail_section` · `face`, `returns`, `back`, `lighting`, `fixing` · `base.plate`, `base.anchors` (pylon) · `notes[]` · `scale` (auto-increased to the next standard scale if the views do not fit A3).

Run:
```
python3 scripts/shop_drawing.py spec.json -o NT-SD-XXX-R0 --qto NT-SD-XXX-R0-qto.json
```
Outputs `.dxf` (layers A-OUTLINE, A-FRAME, A-FACE, A-HIDDEN, A-DIM, A-TEXT, A-TITLE, A-HATCH, A-CENTER, A-GROUND), `.pdf`, `.png`, and the take-off JSON for `rayen-boq-qto`.

## Workflow

1. Extract verified dimensions from the user's drawing/spec. Missing critical dimension → do not invent; mark TO BE CONFIRMED in `notes` and in the reply.
2. Fill the spec JSON; run the generator; **open the PNG and inspect it** (overlaps, dims, labels, title block) before sending. Fix and re-run if anything collides.
3. Audit the DXF (`ezdxf.readfile(...).audit()` must report 0 errors).
4. For anything outside the three parametric types (custom letters, complex joinery, LED screen frames), draw it with ezdxf directly using the same layers, text height 2.5 mm × scale, and the same title block — reuse `Sheet` from the script.
5. For client/factory issue, place the DXF into the original Newtech sheet with `rayen-newtech-template` (view type `dxf`, `hide_layers: ["A-TITLE"]`); part-level CNC files come from `rayen-fabrication`.
6. Deliver DXF + PDF, state the scale used, what is VERIFIED vs ASSUMED, and what needs approval (structural calc, client sign-off, site measurement).

## Limits — say them plainly

- The generator draws envelope, frame grid and section; it does not design connections or size members. Structural members of pylons and elevated signs require a qualified structural engineer's calculation (SBC 301 wind).
- A DXF is not manufacturing-ready until geometry, units, closed profiles and tolerances are verified for the CNC/laser.
- Do not claim to have read native DWG geometry unless it was actually parsed; PDFs/images give dimensions only as written on them.
