# RAYEN — Revit LOD audit (Dynamo Python node, CPython3 or IronPython2) — READ-ONLY.
# NOT executed in RAYEN's environment (no Revit there): test on a copy of the model first.
# Inputs:  IN[0] = target LOD as string ("300" or "400")
# Output:  list of [ElementId, Category, Family:Type, Check, Result] rows — feed to Data.ExportCSV / Excel.
# Requires shared parameters from NT_SharedParameters.txt bound to the checked categories.
import clr
clr.AddReference("RevitAPI"); clr.AddReference("RevitServices")
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter, ElementId
from RevitServices.Persistence import DocumentManager
doc = DocumentManager.Instance.CurrentDBDocument
LOD = str(IN[0]) if len(IN) and IN[0] else "300"

CATS = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows, BuiltInCategory.OST_Floors,
        BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_StructuralColumns, BuiltInCategory.OST_StructuralFraming,
        BuiltInCategory.OST_SpecialityEquipment, BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_Casework,
        BuiltInCategory.OST_Furniture, BuiltInCategory.OST_LightingFixtures]
REQ300 = ["NT_LOD", "NT_ModelAuthor"]
REQ300_BY_CAT = {"Walls": ["Fire Rating"], "Doors": ["Fire Rating"], "Specialty Equipment": ["NT_SignType", "NT_Fixing", "NT_Status"],
                 "Generic Models": ["NT_SignType", "NT_Fixing", "NT_Status"]}
REQ400 = ["NT_PartMark", "NT_AssemblyMark", "NT_Profile", "NT_MaterialGrade", "NT_Weight_kg", "NT_DrawingRef"]

def val(el, name):
    p = el.LookupParameter(name)
    if p is None:
        t = doc.GetElement(el.GetTypeId())
        p = t.LookupParameter(name) if t else None
    if p is None:
        return None
    s = p.AsValueString() or p.AsString()
    if s is None and p.HasValue:
        s = str(p.AsDouble() if p.StorageType.ToString() == "Double" else p.AsInteger())
    return s

rows = [["ElementId", "Category", "Family:Type", "Check", "Result"]]
for bic in CATS:
    for el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType():
        cat = el.Category.Name if el.Category else ""
        t = doc.GetElement(el.GetTypeId())
        ft = (t.FamilyName + ":" + t.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()) if t and hasattr(t, "FamilyName") else ""
        checks = REQ300 + REQ300_BY_CAT.get(cat, [])
        if LOD == "400" and cat in ("Specialty Equipment", "Generic Models", "Structural Framing", "Structural Columns", "Casework"):
            checks = checks + REQ400
        for c in checks:
            v = val(el, c)
            rows.append([el.Id.ToString(), cat, ft, c, "PASS: " + v if v not in (None, "") else "FAIL: missing"])
        # material check
        mats = el.GetMaterialIds(False)
        rows.append([el.Id.ToString(), cat, ft, "Material", "PASS" if mats.Count > 0 else "FAIL: no material"])
        # declared LOD vs target
        d = val(el, "NT_LOD")
        if d and d.isdigit() and int(d) < int(LOD):
            rows.append([el.Id.ToString(), cat, ft, "Declared LOD", "FAIL: declared " + d + " < target " + LOD])
OUT = rows
