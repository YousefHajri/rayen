#!/usr/bin/env python3
"""
RAYEN PMO / PMP engine.

Project mode   : python3 pmo.py plan.json -o PM-Workbook.xlsx
Portfolio mode : python3 pmo.py a.json b.json c.json --portfolio -o PMO-Dashboard.xlsx
Starter input  : python3 pmo.py --example > plan.json

Project workbook sheets:
  Dashboard  - live EVM formulas (BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, VAC, TCPI), RAG + reasons
  Charter    - objectives, scope in/out, milestones, constraints, assumptions, success criteria
  Schedule   - WBS + CPM (ES/EF/LS/LF, total float, critical path), dates, PV/EV/AC per task
  Gantt      - weekly bars, critical path in red
  Risks      - P x I score and rating as formulas, response, owner
  RACI, Stakeholders, Changes, Issues, Lessons

Scheduling: working days, finish-to-start links. A predecessor is "2.1", "2.1+3" (lag),
"2.1-1" (lead) or {"id": "2.1", "lag": 3}. Default weekend Friday+Saturday (Saudi);
override with project.weekend (Python weekday numbers, Mon=0) and project.holidays.
PV is planned linearly between ES and EF. EAC = BAC / CPI (typical variance).
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta

EXAMPLE = {
    "project": {
        "name": "Retail Park — Pylon Sign P-01",
        "code": "NT-P01",
        "client": "Client name",
        "sponsor": "Projects Manager",
        "pm": "PM name",
        "currency": "SAR",
        "start": "2026-11-01",
        "contract_end": "2026-12-31",
        "status_date": "2026-11-21",
        "weekend": [4, 5],
        "holidays": [],
        "objectives": ["Supply and install pylon P-01 per approved shop drawings by 31-Dec-2026 within budget"],
        "scope_in": ["Shop drawings + structural calc", "Fabrication", "Foundation", "Installation", "Testing & handover"],
        "scope_out": ["Power supply to the sign location (by client)", "Municipality fees"],
        "constraints": ["Crane access only Fri night (ASSUMED — confirm with mall management)"],
        "assumptions": ["Consultant reviews shop drawings within 7 working days"],
        "success_criteria": ["Acceptance certificate signed", "Zero lost-time incidents", "CPI ≥ 0.95"],
        "source": "LOA ref (TO BE CONFIRMED); BOQ NT-QTO-0001 R0"
    },
    "tasks": [
        {"id": "1.1", "name": "Award / LOA", "duration_d": 0, "owner": "Client", "pct_complete": 100},
        {"id": "1.2", "name": "Charter & kick-off", "duration_d": 1, "predecessors": ["1.1"], "owner": "PM", "budget": 1500, "pct_complete": 100, "actual_cost": 1500},
        {"id": "2.1", "name": "Site survey", "duration_d": 2, "predecessors": ["1.2"], "owner": "Design", "budget": 2500, "pct_complete": 100, "actual_cost": 2600},
        {"id": "2.2", "name": "Shop drawings", "duration_d": 5, "predecessors": ["2.1"], "owner": "Design", "budget": 6000, "pct_complete": 100, "actual_cost": 7000},
        {"id": "2.3", "name": "Structural calculation (consultant)", "duration_d": 6, "predecessors": ["2.1"], "owner": "Structural consultant", "budget": 4000, "pct_complete": 50, "actual_cost": 2500},
        {"id": "2.4", "name": "Shop drawing approval", "duration_d": 7, "predecessors": ["2.2", "2.3"], "owner": "Consultant", "pct_complete": 20},
        {"id": "3.1", "name": "Material submittal & approval", "duration_d": 5, "predecessors": ["2.2"], "owner": "Procurement", "budget": 1000, "pct_complete": 60, "actual_cost": 800},
        {"id": "3.2", "name": "LED & acrylic procurement (imported)", "duration_d": 15, "predecessors": ["3.1", "2.4"], "owner": "Procurement", "budget": 22000, "pct_complete": 0},
        {"id": "4.1", "name": "Steel frame fabrication", "duration_d": 8, "predecessors": ["2.4"], "owner": "Factory", "budget": 18000, "pct_complete": 0},
        {"id": "4.2", "name": "Cladding & faces fabrication", "duration_d": 6, "predecessors": ["3.2", "4.1"], "owner": "Factory", "budget": 14000, "pct_complete": 0},
        {"id": "4.3", "name": "Factory QC & sample approval", "duration_d": 2, "predecessors": ["4.2"], "owner": "QA/QC", "budget": 1500, "pct_complete": 0},
        {"id": "5.1", "name": "Municipality permit (Balady)", "duration_d": 10, "predecessors": ["2.4"], "owner": "Client", "budget": 2000, "pct_complete": 0},
        {"id": "5.2", "name": "Foundation & anchor bolts", "duration_d": 4, "predecessors": ["5.1", "2.3"], "owner": "Site", "budget": 9000, "pct_complete": 0},
        {"id": "5.3", "name": "Installation (crane)", "duration_d": 3, "predecessors": ["4.3", "5.2+2"], "owner": "Site", "budget": 7000, "pct_complete": 0},
        {"id": "6.1", "name": "Testing & commissioning", "duration_d": 1, "predecessors": ["5.3"], "owner": "Electrical", "budget": 1000, "pct_complete": 0},
        {"id": "6.2", "name": "Snag list close-out", "duration_d": 2, "predecessors": ["6.1"], "owner": "Site", "budget": 1000, "pct_complete": 0},
        {"id": "6.3", "name": "Handover / acceptance", "duration_d": 0, "predecessors": ["6.2"], "owner": "Client", "pct_complete": 0}
    ],
    "risks": [
        {"id": "R-01", "description": "Consultant delays shop drawing approval → fabrication cannot start → end date slips",
         "category": "Schedule", "probability": 4, "impact": 4, "response": "Mitigate",
         "action": "Pre-submission meeting; daily follow-up; partial approval for steel", "owner": "PM", "due": "2026-11-25", "status": "Open"},
        {"id": "R-02", "description": "Imported LED/acrylic arrives late → cladding fabrication delayed",
         "category": "Procurement", "probability": 3, "impact": 4, "response": "Mitigate",
         "action": "Order on submittal approval; local alternative quoted", "owner": "Procurement", "due": "2026-11-30", "status": "Open"},
        {"id": "R-03", "description": "Foundation design not issued → anchor bolts and installation delayed",
         "category": "Structural", "probability": 3, "impact": 5, "response": "Escalate",
         "action": "Escalate to client; RFI-001", "owner": "Structural consultant", "due": "2026-11-24", "status": "Open"},
        {"id": "R-04", "description": "Crane lift over public area",
         "category": "Safety", "probability": 2, "impact": 5, "response": "Mitigate",
         "action": "Lifting plan, barricades, certified operator, permit to work", "owner": "HSE", "due": "2026-12-15", "status": "Open"}
    ],
    "stakeholders": [
        {"name": "Client", "role": "Owner / approver", "power": "High", "interest": "High", "current": "Supportive", "desired": "Leading", "communication": "Weekly report + meeting"},
        {"name": "Consultant", "role": "Shop drawing reviewer", "power": "High", "interest": "Medium", "current": "Neutral", "desired": "Supportive", "communication": "Transmittals, follow-up calls"},
        {"name": "Mall management", "role": "Site access, crane permit", "power": "Medium", "interest": "Medium", "current": "Unaware", "desired": "Supportive", "communication": "Letter + site meeting"},
        {"name": "Newtech factory", "role": "Fabrication", "power": "Medium", "interest": "High", "current": "Supportive", "desired": "Supportive", "communication": "Daily production meeting"}
    ],
    "raci": {
        "roles": ["PM", "Design", "Factory", "Procurement", "Client/Consultant"],
        "rows": [
            {"activity": "Shop drawings", "assign": {"PM": "A", "Design": "R", "Client/Consultant": "C", "Factory": "C"}},
            {"activity": "Shop drawing approval", "assign": {"PM": "R", "Client/Consultant": "A", "Design": "C"}},
            {"activity": "Procurement", "assign": {"PM": "A", "Procurement": "R", "Factory": "C"}},
            {"activity": "Fabrication & QC", "assign": {"PM": "A", "Factory": "R", "Design": "C", "Client/Consultant": "I"}},
            {"activity": "Installation & handover", "assign": {"PM": "A", "Factory": "R", "Client/Consultant": "C"}}
        ]
    },
    "changes": [
        {"id": "CR-01", "date": "2026-11-18", "description": "Client requests dimmable night lighting", "requested_by": "Client",
         "cost_impact": 3500, "schedule_impact_d": 2, "status": "Pending"}
    ],
    "issues": [
        {"id": "I-01", "description": "Structural calc 50% — consultant awaiting soil report", "owner": "Client", "priority": "High", "due": "2026-11-24", "status": "Open"}
    ],
    "lessons": []
}

TAG_FILL = {"GREEN": "C6EFCE", "AMBER": "FFEB9C", "RED": "FF9999"}
RATING_FILL = {"HIGH": "FF9999", "MEDIUM": "FFEB9C", "LOW": "C6EFCE"}


# ---------------------------------------------------------------- calendar
class Calendar:
    def __init__(self, start, weekend=(4, 5), holidays=()):
        self.weekend = set(weekend)
        self.hol = {d if isinstance(d, date) else date.fromisoformat(d) for d in holidays}
        self.days = []
        self._cur = start

    def _work(self, d):
        return d.weekday() not in self.weekend and d not in self.hol

    def date_of(self, i):
        """Date of working day index i (0 = first working day on/after start)."""
        while len(self.days) <= i:
            while not self._work(self._cur):
                self._cur += timedelta(1)
            self.days.append(self._cur)
            self._cur += timedelta(1)
        return self.days[i]

    def done_by(self, d):
        """Number of working days completed by the end of day d."""
        n = 0
        while self.date_of(n) <= d:
            n += 1
        return n


# ---------------------------------------------------------------- CPM
def parse_pred(p):
    if isinstance(p, dict):
        return str(p["id"]), int(p.get("lag", 0))
    m = re.fullmatch(r"\s*(.+?)\s*(?:([+-])\s*(\d+))?\s*", str(p))
    pid, sign, n = m.group(1), m.group(2), m.group(3)
    lag = int(n) * (-1 if sign == "-" else 1) if n else 0
    return pid, lag


def cpm(tasks):
    by_id = {}
    for t in tasks:
        tid = str(t["id"])
        if tid in by_id:
            raise ValueError(f"Duplicate task id {tid}")
        by_id[tid] = t
        t["_preds"] = [parse_pred(p) for p in t.get("predecessors", [])]
        for pid, _ in t["_preds"]:
            if pid not in by_id and pid not in {str(x["id"]) for x in tasks}:
                raise ValueError(f"Task {tid}: unknown predecessor {pid!r}")
    succs = {tid: [] for tid in by_id}
    indeg = {tid: 0 for tid in by_id}
    for tid, t in by_id.items():
        for pid, lag in t["_preds"]:
            succs[pid].append((tid, lag))
            indeg[tid] += 1
    order, queue = [], [tid for tid in by_id if indeg[tid] == 0]
    while queue:
        tid = queue.pop(0)
        order.append(tid)
        for sid, _ in succs[tid]:
            indeg[sid] -= 1
            if indeg[sid] == 0:
                queue.append(sid)
    if len(order) != len(by_id):
        raise ValueError("Circular dependency among: " + ", ".join(sorted(set(by_id) - set(order))))
    for tid in order:
        t = by_id[tid]
        dur = int(t.get("duration_d", 0))
        es = max([by_id[pid]["_ef"] + lag for pid, lag in t["_preds"]] or [0])
        t["_dur"], t["_es"], t["_ef"] = dur, max(es, 0), max(es, 0) + dur
    end = max(t["_ef"] for t in by_id.values())
    for tid in reversed(order):
        t = by_id[tid]
        lf = min([by_id[sid]["_ls"] - lag for sid, lag in succs[tid]] or [end])
        t["_lf"], t["_ls"] = lf, lf - t["_dur"]
        t["_float"] = t["_ls"] - t["_es"]
        t["_critical"] = t["_float"] == 0
    return order, end


# ---------------------------------------------------------------- analysis
def analyse(data):
    p = data["project"]
    start = date.fromisoformat(p["start"])
    status = date.fromisoformat(p.get("status_date", date.today().isoformat()))
    cal = Calendar(start, p.get("weekend", [4, 5]), p.get("holidays", []))
    tasks = data["tasks"]
    order, end = cpm(tasks)
    elapsed = cal.done_by(status)
    warnings = []
    for t in tasks:
        t["_start"] = cal.date_of(t["_es"])
        t["_finish"] = cal.date_of(t["_ef"] - 1) if t["_dur"] > 0 else cal.date_of(max(t["_es"] - 1, 0))
        if t["_dur"] > 0:
            t["_planned"] = min(max((elapsed - t["_es"]) / t["_dur"], 0.0), 1.0)
        else:
            t["_planned"] = 1.0 if elapsed >= t["_es"] else 0.0
        if t.get("budget") and t["_planned"] > 0 and t.get("pct_complete") is None:
            warnings.append(f"Task {t['id']}: planned {t['_planned']:.0%} but pct_complete not reported (NOT VERIFIED, EV=0)")
    budgeted = [t for t in tasks if t.get("budget")]
    bac = sum(float(t["budget"]) for t in budgeted)
    pv = sum(float(t["budget"]) * t["_planned"] for t in budgeted)
    ev = sum(float(t["budget"]) * float(t.get("pct_complete") or 0) / 100 for t in budgeted)
    ac = sum(float(t.get("actual_cost") or 0) for t in tasks)
    cpi = ev / ac if ac else None
    spi = ev / pv if pv else None
    eac = bac / cpi if cpi else None
    tcpi = (bac - ev) / (bac - ac) if bac and bac != ac else None
    planned_finish = cal.date_of(end - 1) if end > 0 else start
    forecast_finish = cal.date_of(max(int(round(end / spi)) - 1, 0)) if spi else planned_finish
    contract_end = date.fromisoformat(p["contract_end"]) if p.get("contract_end") else None
    slip = (cal.done_by(forecast_finish) - cal.done_by(contract_end)) if contract_end else None
    critical = [str(t["id"]) for t in sorted(tasks, key=lambda x: (x["_es"], x["_ef"])) if t["_critical"]]

    risks = data.get("risks", [])
    for r in risks:
        r["_score"] = int(r.get("probability", 0)) * int(r.get("impact", 0))
        r["_rating"] = "HIGH" if r["_score"] >= 15 else "MEDIUM" if r["_score"] >= 8 else "LOW"
    open_high = [r for r in risks if r["_rating"] == "HIGH" and str(r.get("status", "Open")).lower() != "closed"]

    raci = data.get("raci", {})
    for row in raci.get("rows", []):
        vals = [v.upper() for v in row.get("assign", {}).values()]
        if vals.count("A") != 1:
            warnings.append(f"RACI '{row['activity']}': needs exactly one A (has {vals.count('A')})")
        if "R" not in vals:
            warnings.append(f"RACI '{row['activity']}': no R assigned")

    pending = [c for c in data.get("changes", []) if str(c.get("status", "")).lower() in ("pending", "submitted", "under review")]

    # RAG per pmo-governance.md
    red, amber = [], []
    if cpi is not None:
        (red if cpi < 0.90 else amber if cpi < 0.95 else []).append(f"CPI {cpi:.2f}")
    if spi is not None:
        (red if spi < 0.90 else amber if spi < 0.95 else []).append(f"SPI {spi:.2f}")
    if slip is not None and slip > 0:
        (red if slip > 5 else amber).append(f"forecast {slip} working day(s) beyond contract end")
    for r in open_high:
        if str(r.get("category", "")).lower() in ("safety", "structural") and not r.get("action"):
            red.append(f"{r['id']} {r['category']} risk without mitigation")
        elif not r.get("response") or not r.get("owner"):
            amber.append(f"{r['id']} HIGH risk without response/owner")
    for i in data.get("issues", []):
        if str(i.get("status", "")).lower() != "closed" and str(i.get("priority", "")).lower() == "critical":
            red.append(f"critical issue {i['id']} open")
    if cpi is None and spi is None:
        amber.append("EVM not available (no budget or progress)")
    rag = "RED" if red else "AMBER" if amber else "GREEN"
    reasons = red or amber or ["on plan"]

    return dict(cal=cal, order=order, end=end, bac=bac, pv=pv, ev=ev, ac=ac, cpi=cpi, spi=spi, eac=eac,
                tcpi=tcpi, planned_finish=planned_finish, forecast_finish=forecast_finish,
                contract_end=contract_end, slip=slip, critical=critical, open_high=open_high,
                pending=pending, rag=rag, reasons=reasons, warnings=warnings, status=status)


# ---------------------------------------------------------------- excel helpers
def _styles():
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    thin = Side(style="thin", color="BFBFBF")
    return dict(border=Border(left=thin, right=thin, top=thin, bottom=thin),
                head_fill=PatternFill("solid", fgColor="1F2A44"), head_font=Font(bold=True, color="FFFFFF"),
                bold=Font(bold=True), Alignment=Alignment, PatternFill=PatternFill, Font=Font)


def _table(ws, headers, rows, widths, S, wrap=()):
    from openpyxl.utils import get_column_letter
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.fill, cell.font, cell.border = S["head_fill"], S["head_font"], S["border"]
        cell.alignment = S["Alignment"](horizontal="center", vertical="center", wrap_text=True)
    for r, row in enumerate(rows, 2):
        for c, v in enumerate(row, 1):
            cell = ws.cell(r, c, v)
            cell.border = S["border"]
            cell.alignment = S["Alignment"](vertical="top", wrap_text=c in wrap)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "B2"


def _fill(cell, color, S):
    cell.fill = S["PatternFill"]("solid", fgColor=color)


# ---------------------------------------------------------------- project workbook
def write_project(data, A, out):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    S = _styles()
    p = data["project"]
    cur = p.get("currency", "SAR")
    tasks = sorted(data["tasks"], key=lambda t: [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in re.split(r"[.\-]", str(t["id"]))])
    wb = Workbook()

    # Schedule first (Dashboard formulas reference it)
    sc = wb.active
    sc.title = "Schedule"
    hdr = ["WBS", "Task", "Owner", "Dur (wd)", "Predecessors", "ES", "EF", "LS", "LF", "Total float",
           "Critical", "Start", "Finish", f"Budget ({cur})", "Planned %", f"PV ({cur})", "% complete",
           f"EV ({cur})", f"AC ({cur})", "Status"]
    rows = []
    for t in tasks:
        rows.append([str(t["id"]), t["name"], t.get("owner", ""), t["_dur"], ", ".join(map(str, t.get("predecessors", []))),
                     t["_es"], t["_ef"], t["_ls"], t["_lf"], None, None, t["_start"], t["_finish"],
                     t.get("budget"), round(t["_planned"], 4), None,
                     (t["pct_complete"] / 100 if t.get("pct_complete") is not None else None), None,
                     t.get("actual_cost"), t.get("status", "")])
    _table(sc, hdr, rows, [7, 34, 18, 8, 16, 6, 6, 6, 6, 9, 9, 11, 11, 12, 9, 12, 10, 12, 12, 14], S, wrap=(2,))
    n = len(rows) + 1
    for r in range(2, n + 1):
        sc.cell(r, 10, f"=H{r}-F{r}")
        sc.cell(r, 11, f'=IF(J{r}=0,"YES","")')
        sc.cell(r, 16, f"=IF(N{r}=\"\",\"\",N{r}*O{r})")
        sc.cell(r, 18, f"=IF(OR(N{r}=\"\",Q{r}=\"\"),\"\",N{r}*Q{r})")
        for c in (12, 13):
            sc.cell(r, c).number_format = "dd-mmm-yy"
        for c in (14, 16, 18, 19):
            sc.cell(r, c).number_format = "#,##0"
        for c in (15, 17):
            sc.cell(r, c).number_format = "0%"
        if tasks[r - 2]["_critical"]:
            for c in (1, 2, 11):
                _fill(sc.cell(r, c), "F8CBAD", S)
    sc.cell(n + 1, 13, "TOTAL").font = S["bold"]
    for c, L in ((14, "N"), (16, "P"), (18, "R"), (19, "S")):
        sc.cell(n + 1, c, f"=SUM({L}2:{L}{n})").font = S["bold"]
        sc.cell(n + 1, c).number_format = "#,##0"
    sc.cell(n + 3, 1, "CPM: working days, finish-to-start; ES/EF/LS/LF are working-day indexes from project start. "
                      "PV planned linearly between ES and EF. Critical = total float 0.")

    # Dashboard
    d = wb.create_sheet("Dashboard", 0)
    d["A1"] = f"PROJECT DASHBOARD — {p.get('name', '')}"
    d["A1"].font = S["Font"](bold=True, size=15, color="1F2A44")
    info = [("Code", p.get("code")), ("Client", p.get("client")), ("Sponsor", p.get("sponsor")), ("PM", p.get("pm")),
            ("Status date", A["status"]), ("Start", date.fromisoformat(p["start"])),
            ("Planned finish (CPM)", A["planned_finish"]), ("Forecast finish (SPI-adjusted)", A["forecast_finish"]),
            ("Contract end", A["contract_end"]), ("Forecast slip (wd)", A["slip"]),
            ("Critical path", " → ".join(A["critical"]))]
    for i, (k, v) in enumerate(info, 3):
        d.cell(i, 1, k).font = S["bold"]
        c = d.cell(i, 2, v)
        if isinstance(v, date):
            c.number_format = "dd-mmm-yyyy"
    tot = n + 1
    evm = [("BAC", f"=Schedule!N{tot}"), ("PV", f"=Schedule!P{tot}"), ("EV", f"=Schedule!R{tot}"),
           ("AC", f"=Schedule!S{tot}"), ("CV = EV − AC", "=B17-B18"), ("SV = EV − PV", "=B17-B16"),
           ("CPI = EV / AC", '=IF(B18=0,"",B17/B18)'), ("SPI = EV / PV", '=IF(B16=0,"",B17/B16)'),
           ("EAC = BAC / CPI", '=IF(B21="","",B15/B21)'), ("ETC = EAC − AC", '=IF(B23="","",B23-B18)'),
           ("VAC = BAC − EAC", '=IF(B23="","",B15-B23)'), ("TCPI = (BAC−EV)/(BAC−AC)", '=IF(B15=B18,"",(B15-B17)/(B15-B18))')]
    d.cell(14, 1, f"Earned value ({cur})").font = S["bold"]
    for i, (k, f) in enumerate(evm, 15):
        d.cell(i, 1, k)
        d.cell(i, 2, f).number_format = "0.00" if k.split()[0] in ("CPI", "SPI", "TCPI") else "#,##0"
    d.cell(28, 1, "RAG").font = S["bold"]
    rc = d.cell(28, 2, A["rag"])
    _fill(rc, TAG_FILL[A["rag"]], S)
    d.cell(29, 1, "Reason")
    d.cell(29, 2, "; ".join(A["reasons"]))
    d.cell(30, 1, "Open HIGH risks")
    d.cell(30, 2, ", ".join(r["id"] for r in A["open_high"]) or "none")
    d.cell(31, 1, "Changes pending")
    d.cell(31, 2, f"{len(A['pending'])} — {sum(float(c.get('cost_impact') or 0) for c in A['pending']):,.0f} {cur}, "
                  f"{sum(int(c.get('schedule_impact_d') or 0) for c in A['pending'])} wd")
    if A["warnings"]:
        d.cell(33, 1, "Warnings").font = S["bold"]
        for i, w in enumerate(A["warnings"], 34):
            d.cell(i, 2, w)
    d.column_dimensions["A"].width = 30
    d.column_dimensions["B"].width = 70

    # Charter
    ch = wb.create_sheet("Charter", 1)
    ch["A1"] = "PROJECT CHARTER"
    ch["A1"].font = S["Font"](bold=True, size=14, color="1F2A44")
    r = 3
    for k in ("name", "code", "client", "sponsor", "pm", "start", "contract_end", "currency", "source"):
        if p.get(k) is not None:
            ch.cell(r, 1, k.replace("_", " ").title()).font = S["bold"]
            ch.cell(r, 2, str(p[k]))
            r += 1
    ch.cell(r, 1, "Budget (BAC)").font = S["bold"]
    ch.cell(r, 2, f"{A['bac']:,.0f} {cur}")
    r += 2
    for k in ("objectives", "scope_in", "scope_out", "constraints", "assumptions", "success_criteria"):
        ch.cell(r, 1, k.replace("_", " ").title()).font = S["bold"]
        for v in p.get(k, []) or ["—"]:
            ch.cell(r, 2, "• " + str(v))
            r += 1
        r += 1
    ch.cell(r, 1, "Milestones").font = S["bold"]
    for t in tasks:
        if t["_dur"] == 0:
            ch.cell(r, 2, f"{t['id']}  {t['name']} — {t['_finish'].isoformat()}")
            r += 1
    r += 1
    ch.cell(r, 1, "Approval").font = S["bold"]
    ch.cell(r, 2, "Sponsor: ____________________   Date: __________")
    ch.column_dimensions["A"].width = 22
    ch.column_dimensions["B"].width = 90

    # Gantt (weekly)
    g = wb.create_sheet("Gantt")
    start = date.fromisoformat(p["start"])
    wk0 = start - timedelta(days=(start.weekday() + 1) % 7)  # Sunday
    last = max(t["_finish"] for t in tasks)
    weeks = min(((last - wk0).days // 7) + 1, 104)
    g.cell(1, 1, "WBS").font = S["bold"]
    g.cell(1, 2, "Task").font = S["bold"]
    for w in range(weeks):
        c = g.cell(1, 3 + w, (wk0 + timedelta(weeks=w)).strftime("%d-%b"))
        c.font = S["Font"](bold=True, size=8)
        c.alignment = S["Alignment"](text_rotation=90)
        g.column_dimensions[get_column_letter(3 + w)].width = 3.2
    status_col = 3 + (A["status"] - wk0).days // 7
    for i, t in enumerate(tasks, 2):
        g.cell(i, 1, str(t["id"]))
        g.cell(i, 2, t["name"])
        s, f = t["_start"], t["_finish"]
        for w in range(weeks):
            ws_, we_ = wk0 + timedelta(weeks=w), wk0 + timedelta(weeks=w, days=6)
            if s <= we_ and f >= ws_:
                _fill(g.cell(i, 3 + w), ("C00000" if t["_critical"] else "4472C4") if t["_dur"] else "000000", S)
    if 3 <= status_col < 3 + weeks:
        g.cell(len(tasks) + 2, status_col, "▲ status").font = S["Font"](bold=True, color="C00000", size=8)
    g.cell(len(tasks) + 4, 1, "Red = critical path, blue = non-critical, black = milestone.")
    g.column_dimensions["A"].width = 6
    g.column_dimensions["B"].width = 34
    g.freeze_panes = "C2"

    # Risks
    rk = wb.create_sheet("Risks")
    risks = data.get("risks", [])
    _table(rk, ["ID", "Risk (cause → event → effect)", "Category", "P (1-5)", "I (1-5)", "Score", "Rating",
                "Response", "Action", "Owner", "Due", "Status"],
           [[x["id"], x["description"], x.get("category", ""), x.get("probability"), x.get("impact"), None, None,
             x.get("response", ""), x.get("action", ""), x.get("owner", ""), x.get("due", ""), x.get("status", "Open")]
            for x in risks],
           [7, 48, 13, 7, 7, 7, 9, 11, 40, 16, 11, 9], S, wrap=(2, 9))
    for i, x in enumerate(risks, 2):
        rk.cell(i, 6, f"=D{i}*E{i}")
        rk.cell(i, 7, f'=IF(F{i}>=15,"HIGH",IF(F{i}>=8,"MEDIUM","LOW"))')
        _fill(rk.cell(i, 7), RATING_FILL[x["_rating"]], S)
    rk.cell(len(risks) + 3, 1, "Score = P × I. HIGH 15–25, MEDIUM 8–14, LOW 1–7.")

    # RACI
    rc_ = data.get("raci", {})
    roles = rc_.get("roles", [])
    ra = wb.create_sheet("RACI")
    _table(ra, ["Activity"] + roles, [[row["activity"]] + [row.get("assign", {}).get(rl, "") for rl in roles]
                                      for row in rc_.get("rows", [])], [32] + [14] * len(roles), S)
    ra.cell(len(rc_.get("rows", [])) + 3, 1, "R = Responsible, A = Accountable (exactly one), C = Consulted, I = Informed")

    # Stakeholders, Changes, Issues, Lessons
    st = wb.create_sheet("Stakeholders")
    _table(st, ["Stakeholder", "Role", "Power", "Interest", "Current engagement", "Desired engagement", "Communication"],
           [[x.get(k, "") for k in ("name", "role", "power", "interest", "current", "desired", "communication")]
            for x in data.get("stakeholders", [])], [20, 28, 9, 9, 16, 16, 34], S, wrap=(2, 7))
    cg = wb.create_sheet("Changes")
    _table(cg, ["ID", "Date", "Description", "Requested by", f"Cost impact ({cur})", "Schedule impact (wd)", "Status", "Decision by"],
           [[x.get(k, "") for k in ("id", "date", "description", "requested_by", "cost_impact", "schedule_impact_d", "status", "decision_by")]
            for x in data.get("changes", [])], [8, 11, 44, 14, 14, 12, 12, 16], S, wrap=(3,))
    iss = wb.create_sheet("Issues")
    _table(iss, ["ID", "Issue", "Owner", "Priority", "Due", "Status"],
           [[x.get(k, "") for k in ("id", "description", "owner", "priority", "due", "status")]
            for x in data.get("issues", [])], [8, 52, 18, 10, 11, 10], S, wrap=(2,))
    ls = wb.create_sheet("Lessons")
    _table(ls, ["#", "What happened", "Impact", "Recommendation", "Owner of change"],
           [[i, x.get("what", ""), x.get("impact", ""), x.get("recommendation", ""), x.get("owner", "")]
            for i, x in enumerate(data.get("lessons", []), 1)], [5, 40, 26, 40, 18], S, wrap=(2, 3, 4))
    wb.save(out)


# ---------------------------------------------------------------- portfolio
def write_portfolio(items, out):
    from openpyxl import Workbook
    S = _styles()
    wb = Workbook()
    ws = wb.active
    ws.title = "Portfolio"
    hdr = ["Project", "Code", "PM", "BAC", "PV", "EV", "AC", "CPI", "SPI", "EAC", "VAC",
           "Contract end", "Forecast finish", "Slip (wd)", "Critical path", "Open HIGH risks", "Changes pending", "RAG", "Reason"]
    rows = []
    for data, A in items:
        p = data["project"]
        rows.append([p.get("name"), p.get("code"), p.get("pm"), A["bac"], A["pv"], A["ev"], A["ac"], None, None, None, None,
                     A["contract_end"], A["forecast_finish"], A["slip"], " → ".join(A["critical"]),
                     len(A["open_high"]), len(A["pending"]), A["rag"], "; ".join(A["reasons"])])
    _table(ws, hdr, rows, [30, 10, 16, 11, 11, 11, 11, 7, 7, 11, 11, 12, 12, 8, 36, 9, 9, 8, 46], S, wrap=(15, 19))
    n = len(rows) + 1
    for r in range(2, n + 1):
        ws.cell(r, 8, f'=IF(G{r}=0,"",F{r}/G{r})').number_format = "0.00"
        ws.cell(r, 9, f'=IF(E{r}=0,"",F{r}/E{r})').number_format = "0.00"
        ws.cell(r, 10, f'=IF(H{r}="","",D{r}/H{r})').number_format = "#,##0"
        ws.cell(r, 11, f'=IF(J{r}="","",D{r}-J{r})').number_format = "#,##0"
        for c in (4, 5, 6, 7):
            ws.cell(r, c).number_format = "#,##0"
        for c in (12, 13):
            ws.cell(r, c).number_format = "dd-mmm-yy"
        _fill(ws.cell(r, 18), TAG_FILL[rows[r - 2][17]], S)
    t = n + 1
    ws.cell(t, 1, "PORTFOLIO").font = S["bold"]
    for c, L in ((4, "D"), (5, "E"), (6, "F"), (7, "G")):
        ws.cell(t, c, f"=SUM({L}2:{L}{n})").number_format = "#,##0"
    ws.cell(t, 8, f'=IF(G{t}=0,"",F{t}/G{t})').number_format = "0.00"
    ws.cell(t, 9, f'=IF(E{t}=0,"",F{t}/E{t})').number_format = "0.00"
    ws.cell(t + 2, 1, "Count by RAG").font = S["bold"]
    for i, k in enumerate(("RED", "AMBER", "GREEN")):
        ws.cell(t + 3 + i, 1, k)
        ws.cell(t + 3 + i, 2, f'=COUNTIF(R2:R{n},"{k}")')
        _fill(ws.cell(t + 3 + i, 1), TAG_FILL[k], S)

    rk = wb.create_sheet("HIGH risks")
    _table(rk, ["Project", "ID", "Risk", "Category", "Score", "Response", "Action", "Owner", "Due"],
           [[d["project"].get("code"), r["id"], r["description"], r.get("category", ""), r["_score"],
             r.get("response", ""), r.get("action", ""), r.get("owner", ""), r.get("due", "")]
            for d, A in items for r in A["open_high"]], [10, 7, 46, 12, 7, 11, 38, 16, 11], S, wrap=(3, 7))
    cg = wb.create_sheet("Changes pending")
    _table(cg, ["Project", "ID", "Date", "Description", "Cost impact", "Schedule impact (wd)", "Requested by"],
           [[d["project"].get("code"), c.get("id"), c.get("date"), c.get("description"), c.get("cost_impact"),
             c.get("schedule_impact_d"), c.get("requested_by")] for d, A in items for c in A["pending"]],
           [10, 8, 11, 46, 12, 12, 14], S, wrap=(4,))
    wb.save(out)


# ---------------------------------------------------------------- main
def _fmt(x, spec):
    return "n/a" if x is None else format(x, spec)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="RAYEN PMO/PMP engine")
    ap.add_argument("inputs", nargs="*", help="project JSON file(s)")
    ap.add_argument("-o", "--out", default="PM-Workbook.xlsx")
    ap.add_argument("--portfolio", action="store_true", help="build a multi-project PMO dashboard")
    ap.add_argument("--example", action="store_true", help="print an example project JSON")
    a = ap.parse_args()
    if a.example:
        json.dump(EXAMPLE, sys.stdout, indent=2, ensure_ascii=False)
        return
    if not a.inputs:
        ap.error("project JSON required (or --example)")
    if len(a.inputs) > 1 and not a.portfolio:
        ap.error("several inputs need --portfolio")
    items = []
    for f in a.inputs:
        data = json.load(open(f, encoding="utf-8-sig"))
        items.append((data, analyse(data)))
    if a.portfolio:
        write_portfolio(items, a.out)
    else:
        write_project(items[0][0], items[0][1], a.out)
    print(f"Written: {a.out}")
    for data, A in items:
        p = data["project"]
        cur = p.get("currency", "SAR")
        print(f"\n== {p.get('code', '')} {p.get('name', '')}  [{A['rag']}] {'; '.join(A['reasons'])}")
        print(f"Planned finish {A['planned_finish']}  forecast {A['forecast_finish']}  contract {A['contract_end']}  slip {A['slip']} wd")
        print(f"Critical path: {' -> '.join(A['critical'])}")
        print(f"BAC {A['bac']:,.0f}  PV {A['pv']:,.0f}  EV {A['ev']:,.0f}  AC {A['ac']:,.0f} {cur}")
        print(f"CPI {_fmt(A['cpi'], '.2f')}  SPI {_fmt(A['spi'], '.2f')}  EAC {_fmt(A['eac'], ',.0f')}  TCPI {_fmt(A['tcpi'], '.2f')}")
        print(f"Open HIGH risks: {', '.join(r['id'] for r in A['open_high']) or 'none'}; changes pending: {len(A['pending'])}")
        for w in A["warnings"]:
            print("WARNING:", w)


if __name__ == "__main__":
    main()
