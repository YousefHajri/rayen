---
name: rayen-newtech-template
description: "Newtech original drawing identity (قالب نيوتك الأصلي المعتمد) — composes any RAYEN output (shop drawings DXF, fabrication parts, renders, tables, specs) into the approved Newtech presentation/drawing set: cover page, content sheets with the Пewtech logo, blue title bar with gold DWG label, side panels (تعديلات التصميم / تفاصيل أمر العمل / تفاصيل التصميم / عدد الجونت), footer ticker, and the THANK YOU closing page with the approval disclaimer. This skill should be used whenever drawings, renders or a submission package go to a client or the factory, or when the user says \"بقالب نيوتك\", \"هوية نيوتك\", \"Newtech template\", \"اعرضها للعميل\", \"جهّز ملف المخططات\", \"work order drawings\", \"أمر عمل\".\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Newtech Original Template

Identity VERIFIED from Drive file `عرض_مخططات_السور_المعدني_قالب_نيوتك_الأصلي_المعتمد.pdf` (Oct 2026). Details, colours and page anatomy: `references/identity.md`; reference images in `assets/` (`reference-cover.jpg`, `reference-sheet.jpg`, `reference-closing.jpg`). Do not invent other logos, colours or contact data — if the approved identity changes, update `references/identity.md` and the constants at the top of the script.

## Compose a set
```
python3 scripts/newtech_sheet.py --example > package.json      # edit fields + sheets
python3 scripts/newtech_sheet.py package.json -o "WO-2026-XX01 Drawings.pdf" --png
python3 scripts/newtech_sheet.py package.json --dxf-frame NT-frame.dxf   # identity frame for AutoCAD layouts
```
`project`: name (title, blue), subtitle (orange), description, client, client_logo (PNG/JPG), location, category (التصنيف), units, designer (المصمم), sales_rep (مندوب البيع), wo_no (رقم أمر العمل), joints (عدد الجونت), revisions [[date, note]…], cover_rows [[label, value]…], ticker, status (optional badge e.g. "FOR APPROVAL").
`sheets[]`: dwg ("DWG-04: ARCH-ELEVATION"), heading ("المواصفات" / "التصميم"), title, `views[]` (type image | dxf | table, file, box [x0,y0,x1,y1] as fractions of the content box, hide_layers for DXF e.g. ["A-TITLE"], caption), notes[] (spec lines under the drawing).
Page numbers "NN / TT" and revision count are automatic.

## Standard Newtech sheet order (from the approved set)
01 Cover · DWG-02 3D-VISUALIZATION (day/night renders) · DWG-03 GENERAL-LAYOUT · DWG-04 ARCH-ELEVATION · DWG-05 STRUCTURAL-SECTION · DWG-06 STEEL-FRAMING (members table) · DWG-07 CONNECTIONS · DWG-08 RC-FOOTINGS-BBS · DWG-09 ARCH-FINISHES / details · closing THANK YOU. For interior/LED jobs: DESIGN (before/after) → ELEVATIONS → SECTIONS → FABRICATION PARTS → ELECTRICAL → FINISHES.

## Workflow
1. Produce the content first: `rayen-shop-drawing` (DXF, run with its A3 title block — hide layer `A-TITLE` when placing), `rayen-fabrication` (parts PNG/DXF), `rayen-render` (PNG), tables from `rayen-boq-qto`.
2. Fill package.json — every field from the work order; unknown → "TO BE CONFIRMED", never blank-guessed.
3. Run, then open the PNGs and check: nothing overlaps the side panels, text readable, page count, revision row, DWG labels in sequence.
4. Deliver PDF (+ DXF frame if the drafter needs it). The closing page carries Newtech's own approval disclaimer — keep it.

## Limits
Logo is reproduced as in the approved file (typeset "Пewtech" wordmark, blue #0F4C82). If the user supplies an official vector logo, pass it as an image view or replace `logo()` in the script. Arabic shaping needs matplotlib ≥ 3.11 (native) or arabic-reshaper + python-bidi.
