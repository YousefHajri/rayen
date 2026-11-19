#!/usr/bin/env python3
"""RAYEN space program — brief -> net areas -> gross (grossing factor) -> occupant load -> plumbing estimate.

  python3 space_program.py program.json [-o Program.xlsx]
  python3 space_program.py --example

Occupant load factors (m2/person) are TYPICAL IBC/SBC 201 Table 1004-style values: VERIFY against the SBC 201
edition adopted for the project and the authority (Balady / Civil Defense) before use.
"""
import argparse, json, math

OLF = {  # function: (m2 per occupant, basis)
    "business": (14.0, "gross"), "assembly_unfixed": (1.4, "net"), "assembly_standing": (0.65, "net"),
    "assembly_tables": (1.4, "net"), "mercantile": (5.6, "gross"), "storage": (28.0, "gross"),
    "education_class": (1.9, "net"), "kitchen_commercial": (18.6, "gross"), "residential": (18.6, "gross"),
    "exhibit": (2.8, "net"), "industrial": (9.3, "gross"), "accessory": (28.0, "gross"),
}

EXAMPLE = {"project": "Newtech HQ — fit-out brief", "grossing_factor": 1.30,
           "spaces": [
               {"zone": "Public", "name": "Reception & waiting", "qty": 1, "area": 60, "use": "assembly_unfixed"},
               {"zone": "Public", "name": "Showroom", "qty": 1, "area": 180, "use": "exhibit"},
               {"zone": "Work", "name": "Open office workstation", "qty": 40, "area": 6.5, "use": "business"},
               {"zone": "Work", "name": "Manager office", "qty": 6, "area": 14, "use": "business"},
               {"zone": "Work", "name": "Meeting room (8p)", "qty": 3, "area": 22, "use": "assembly_tables"},
               {"zone": "Work", "name": "Board room (16p)", "qty": 1, "area": 45, "use": "assembly_tables"},
               {"zone": "Support", "name": "Pantry", "qty": 2, "area": 12, "use": "accessory"},
               {"zone": "Support", "name": "Prayer room (M)", "qty": 1, "area": 25, "use": "assembly_unfixed"},
               {"zone": "Support", "name": "Prayer room (F)", "qty": 1, "area": 15, "use": "assembly_unfixed"},
               {"zone": "Support", "name": "Server / IT", "qty": 1, "area": 10, "use": "accessory"},
               {"zone": "Support", "name": "Storage", "qty": 2, "area": 15, "use": "storage"}]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", nargs="?"); ap.add_argument("-o", "--out"); ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False)); return
    d = json.load(open(a.json, encoding="utf-8"))
    gf = d.get("grossing_factor", 1.3)
    rows, net, occ = [], 0, 0
    for s in d["spaces"]:
        tot = s["qty"] * s["area"]
        f, basis = OLF.get(s.get("use", "business"), (14.0, "gross"))
        load_area = tot * (gf if basis == "gross" else 1)
        o = math.ceil(load_area / f) if s.get("occupants") is None else s["occupants"]
        rows.append([s.get("zone", ""), s["name"], s["qty"], s["area"], tot, s.get("use", ""), f, basis, o])
        net += tot; occ += o
    gross = net * gf
    print(f"{d.get('project','')}\n NET {net:.1f} m2 · grossing {gf} · GROSS {gross:.1f} m2 · occupant load ~{occ} (CALCULATED, verify OLF)")
    zones = {}
    for r in rows: zones[r[0]] = zones.get(r[0], 0) + r[4]
    for z, v in zones.items(): print(f"   {z:10s} {v:8.1f} m2  {v/net*100:5.1f}%")
    print(" Egress, plumbing fixture count and exit widths: derive from occupant load per SBC 201 ch.10 / SBC 701 — TO BE CONFIRMED.")
    if a.out:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        wb = Workbook(); ws = wb.active; ws.title = "Program"
        ws.append([d.get("project", "")]); ws.append(["Zone", "Space", "Qty", "Unit area m2", "Total net m2", "Use", "OLF m2/p", "OLF basis", "Occupants"])
        for c in ws[2]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3864")
        first = 3
        for r in rows:
            i = ws.max_row + 1
            r[4] = f"=C{i}*D{i}"
            ws.append(r)
        last = ws.max_row
        ws.append([]); ws.append(["", "TOTAL NET", "", "", f"=SUM(E{first}:E{last})", "", "", "", f"=SUM(I{first}:I{last})"])
        t = ws.max_row
        ws.append(["", "Grossing factor", "", "", gf])
        ws.append(["", "GROSS AREA", "", "", f"=E{t}*E{t+1}"])
        ws.append([]); ws.append(["Status: CALCULATED. OLF values typical — verify against adopted SBC 201 edition & authority."])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 16
        wb.save(a.out); print(" saved", a.out)


if __name__ == "__main__":
    main()
