---
name: rayen-bim
description: "RAYEN BIM manager & coordinator — LOD 300 / 350 / 400 modelling and verification, Revit, IFC/openBIM, Navisworks/ACC coordination, BEP (ISO 19650), LOD/LOIN, model audit, clash matrix, model-based QTO, families & parameters, Dynamo/pyRevit automation, COBie. This skill should be used when the user asks about \"BIM\", \"Revit\", \"IFC\", \"model audit\", \"clash detection\", \"Navisworks\", \"ACC / BIM 360\", \"BEP\", \"LOD 300\", \"LOD 350\", \"LOD 400\", \"fabrication model\", \"model for coordination\", \"LOD check\", \"مستوى التطوير\", \"موديل تصنيعي\", \"families\", \"shared parameters\", \"Dynamo\", \"model QTO\", \"COBie\", \"نمذجة\", \"ريفيت\", \"تعارضات\", \"تنسيق الموديل\", \"خطة تنفيذ BIM\", or sends an .ifc/.rvt/.nwd file or a clash report. Audits IFC files directly (ifc_audit.py → XLSX), writes BEP/clash registers, and hands Revit-side automation to the revit-bim plugin.\n"
metadata:
  version: "0.3.0"
---

# RAYEN — BIM

Read `references/bim-standards.md` for ISO 19650 workflow, naming, clash matrix and model QA rules, and `references/lod-spec.md` for the LOD 300 / 350 / 400 element table and acceptance rules (`references/lod_requirements.json` = machine rules).

## LOD 300 & LOD 400 toolkit
| Task | Command |
|---|---|
| Build a **LOD 300** coordination model of a sign (true envelope + data) from the shop-drawing spec | `python3 scripts/lod_build.py spec.json --lod 300 -o <MARK>-LOD300.ifc [--origin x y z --rot deg]` |
| Build a **LOD 400** fabrication model (assembly → members with real profiles, plates, returns, back, LED layer, base plates, anchors; NT_Fabrication on every part) | `python3 scripts/lod_build.py spec.json --lod 400 -o <MARK>-LOD400.ifc` |
| **Check** any IFC against LOD 300 / 400 (score, hard fails, mark conflicts, parts list, internal overlaps) | `python3 scripts/lod_check.py model.ifc --lod 400 --overlap -o <Model>-LOD400-Check.xlsx` |
| LOD responsibility matrix for the BEP | `python3 scripts/lod_check.py --write-matrix BEP-LOD-Matrix.xlsx` |
| Revit: shared parameters / IFC Pset mapping / Dynamo LOD audit | `revit/NT_SharedParameters.txt` · `revit/NT_IFC_PropertySets.txt` · `revit/rayen_lod_audit_dynamo.py` |

Rules: the LOD 400 cut lengths come from the same frame rule as the shop drawing (frame inside the returns), so **parts list = cutting list** — always compare them; any difference is a CONFLICT. Edit `lod_requirements.json` per project EIR/BEP and pass `--rules`. The Dynamo script is read-only and was not run here (no Revit) — test on a copy.

## What RAYEN can do directly
| Task | How |
|---|---|
| Audit an IFC (counts, storeys, materials, types, missing data, quantities) | `python3 scripts/ifc_audit.py model.ifc -o <Model>-Audit.xlsx --required IfcWall:Pset_WallCommon.FireRating IfcDoor:Pset_DoorCommon.FireRating` |
| Clash screening between IFC classes (bounding-box) | add `--clash IfcWall,IfcColumn,IfcBeam IfcDuctSegment,IfcPipeSegment,IfcCableCarrierSegment --tol 0.01` — screening only, confirm in Navisworks / ACC Model Coordination |
| Model-based QTO | the Elements sheet (Qto_* quantities) → feed `rayen-boq-qto`; label quantities "from model — VERIFIED against model only" |
| Render the BIM model | `rayen-render` with `{"imports":[{"file":"model.ifc"}]}` |
| Create a test IFC | `python3 scripts/ifc_audit.py --make-sample sample.ifc` |
| BEP, MIDP/TIDP, naming convention, LOD matrix, clash matrix, coordination meeting minutes | write from the templates in the reference (DOCX/XLSX) |

## Revit-side work (hand-off)
Use the installed **revit-bim** plugin skills when the user works inside Revit/Dynamo: `revit-bim:audit-model`, `clash-detection`, `create-schedule`, `manage-parameters`, `shared-parameters`, `validate-parameters`, `manage-sheets`, `export-ifc`, `generate-dynamo`, `export-dynamo-file`, `revit-api-code`, `workset-manager`, `linked-model-check`, `project-setup`; ACC work → `revit-bim:acc-*` skills. Autodesk product help → Autodesk Product Help connector (`search_help_content`). Do not claim to have opened an .rvt — it cannot be parsed here; ask for IFC/NWC export or schedules.

## Coordination workflow
1. Confirm model set, versions, shared coordinates / survey point, units, levels and grids match (linked-model check).
2. Run clash tests per the matrix; group clashes (by level/zone/system), drop duplicates and tolerance noise.
3. Register: | ID | Level/Zone | Discipline A | Discipline B | Elements (GUID) | Type (hard/clearance/access) | Proposed fix | Priority | Owner | Due | Status |.
4. Priority: life safety → structure → gravity drainage → major ducts → cable trays/pipes → architecture/finishes → signage.
5. Re-run and close; report trend (open/closed per week) — use `rayen-reports`.

## Rules
Never declare "clash-free" from screening; only from a coordinated federated review with agreed tolerances. Model quantities ≠ BOQ until the measurement method is applied. Respect the CDE states: only PUBLISHED information is used for construction.
