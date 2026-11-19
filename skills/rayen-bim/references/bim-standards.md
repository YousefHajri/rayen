# BIM standards & practice

## ISO 19650 essentials
Appointing party (client) → OIR/AIR/PIR/EIR → lead appointed party BEP (pre- & post-appointment) → MIDP/TIDP → CDE.
CDE states: **WIP → SHARED → PUBLISHED → ARCHIVED**; status codes S0 WIP, S1 coordination, S2 information, S3 review/comment, S4 stage approval; A1… published for construction (use project-specific codes).
Naming (UK annex style, adapt): `Project-Originator-Volume/System-Level/Location-Type-Role-Number` e.g. `NT01-NTK-ZZ-GF-DR-A-0101`. Roles: A arch, S struct, M mech, E elec, P plumbing, F fire, I interior, G signage (project-defined).

## LOD / LOIN (BIMForum-style)
| LOD | Meaning | Typical stage |
|---|---|---|
| 100 | Symbol/massing | Concept |
| 200 | Generic system, approximate size | SD |
| 300 | Specific element, accurate size/location | DD / IFC |
| 350 | + interfaces/connections to other systems | Coordination |
| 400 | Fabrication/assembly detail | Shop drawings |
| 500 | As-built verified | Handover |
Define LOIN per element: geometry + information (parameters) + documentation, per stage — table in BEP.

## Revit model standards (checklist)
Shared coordinates & survey point set; levels/grids from one source (copy/monitor) · worksets by discipline/zone (Shared Levels & Grids, Links, Interior, Exterior, FF&E, Signage) · view templates and filters · family naming `<Category>_<Type>_<Size>_<Originator>` · no in-place families for repeated items · purge unused, warnings < agreed limit (e.g. < 200), no imported CAD in project views (link instead) · rooms placed, bounded and named per program · parameters: shared parameters for anything scheduled or exported (IFC/COBie) · phases/design options controlled.

## Model health KPIs
File size trend, warnings count, in-place families, CAD imports, unplaced/unbounded rooms, duplicate marks, elements on wrong workset, unused views/sheets, links status, IFC export mapping coverage.

## Clash matrix (example tolerances)
| | STR | MEP Duct | Pipe | Cable tray | Ceiling | Arch walls | Signage/FF&E |
|---|---|---|---|---|---|---|---|
| STR | — | 0 mm hard | 0 | 0 | 0 | 25 | 10 |
| Duct | | — | 25 | 50 | 50 clearance (ceiling void) | 25 | 25 |
| Pipe | | | — | 50 | 50 | 25 | 25 |
| Cable tray | | | | — | 150 access above | 25 | 25 |
Add soft clashes: maintenance zones (FCU, valves), access panels, door swings, egress paths, sign viewing zones.

## IFC
IFC 2x3 CV2.0 for wide compatibility, IFC4 RV/ADD where accepted. Map Revit categories → IFC classes; export base quantities; include Pset_*Common (FireRating, IsExternal, AcousticRating, LoadBearing). Check with ifc_audit.py / Solibri / BIMcollab Zoom.

## COBie (if required)
Facility, Floor, Space, Zone, Type, Component, System, Spare, Resource, Job, Document, Attribute. Validate completeness before handover; RAYEN validates Type/Component naming and required attributes from IFC.

## Signage in BIM (Newtech)
Model signs as Specialty Equipment / Generic Models with parameters: SignType, Message_AR, Message_EN, Illuminated (Y/N), Power_W, Weight_kg, Fixing, SubstrateCheck, MountHeight, Status. Schedule → message schedule, power schedule, fixing schedule. Check soft-clash: sign viewing cone vs columns, sprinklers and ceiling devices.
