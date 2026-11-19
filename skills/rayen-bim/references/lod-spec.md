# LOD 300 & LOD 400 — element specification (BIMForum LOD Spec logic, adapted to Newtech scope)

**LOD = Level of Development = geometry reliability + attached information.** The BEP/EIR governs; this is RAYEN's default.
- **LOD 300** — specific element, true size, shape, location, orientation (measurable from the model); generic connections not shown; information needed for coordination & quantities.
- **LOD 350** — LOD 300 + interfaces: supports, connections, clearances, penetrations with other systems.
- **LOD 400** — fabrication & assembly: every part, real profiles, cut lengths, fasteners, marks, weights, finishes; model can drive shop drawings, cutting lists and CNC.

## Element table
| Element | LOD 300 geometry | LOD 300 information | LOD 400 geometry | LOD 400 information |
|---|---|---|---|---|
| Walls / partitions | Overall thickness, height, openings, layers as single solid or compound | Type, IsExternal, FireRating, acoustic rating, material | Studs, tracks, boards, insulation, deflection head, backing plates | Stud size/gauge/spacing, board type & count, fixings, firestop system |
| Doors / windows | True frame & leaf size, swing, location | Type, FireRating, HandicapAccessible, hardware set ref | Frame profiles, leaf build-up, hardware positions | Supplier model, hardware schedule, glazing spec, certification |
| Ceilings | Ceiling zone at true level, bulkheads, access panel positions | Type, material, FireRating, acoustic NRC | Grid/channels, hangers, panels, trims, access panels as parts | Hanger spacing, system ref, panel sizes, cut list |
| Structural steel | Members with true profiles, positions, levels | Profile, grade, LoadBearing | Plates, bolts, welds, cleats, cope/notch, camber | Part & assembly marks, cut lengths, weights, finish, NC data |
| Joinery / counters | True envelope, doors/drawers divisions, top | Material/finish codes, type mark | Carcass panels, shelves, edges, hardware, sub-frame, scribes | Panel cut list, edge banding, hardware models, CNC refs |
| **Signs (Newtech)** | True envelope W×D×H at mounting position + fixing zone | NT_Sign (type, size, face, returns, lighting, fixing, status), manufacturer, LOD | Frame members, faces, returns, back, LED layer, base plates, anchors as parts in an assembly | NT_Fabrication on each part (mark, profile, length, grade, finish, weight, process, drawing ref), assembly mark |
| LED screens | Cabinet array envelope, support frame zone | Pixel pitch, cabinet size/count, weight, power | Cabinets, support steel, brackets, service access | Cabinet model, weights, power/data routing |
| MEP (ducts, pipes, trays) | True size & routing, insulation | System, size, type | Hangers/supports, fittings, spool breaks | Spool/part numbers, support types |

## Acceptance (what RAYEN checks — lod_check.py)
LOD 300: name · contained in storey · material · Body solid representation · type (warn) · classification (warn) · class Psets (e.g. Wall FireRating/IsExternal, Door FireRating, NT_Sign fields).
LOD 400: all LOD 300 + every part in an IfcElementAssembly · PartMark · MaterialGrade · Weight · DrawingRef · profile-based members with Length · plate Thickness · fastener diameter/length · **same mark = same geometry** · no internal part overlaps (detailing interfaces) · parts list by mark.

## Workflow in RAYEN
1. Shop-drawing spec (rayen-shop-drawing) → `lod_build.py --lod 300` for coordination models (drop into the federated model / Navisworks).
2. After approval → `lod_build.py --lod 400` → `lod_check.py --lod 400 --overlap` → parts list = cutting list check → `rayen-render` to review the assembly → `rayen-fabrication` for CNC.
3. Revit teams: load `revit/NT_SharedParameters.txt`, bind to categories, export IFC with `revit/NT_IFC_PropertySets.txt`, audit in Revit with `revit/rayen_lod_audit_dynamo.py`, then run lod_check.py on the exported IFC.
4. Report: score, hard fails, mark conflicts, overlaps → RFI / model-author actions (owner + due date).

## Honesty rules
Never write "LOD 400 compliant" without running the checker against the agreed rules; a geometric LOD 400 model still needs the structural engineer's approval for structural parts; ASSUMED parts (anchors, base-plate count, LED layout) stay tagged until confirmed.
