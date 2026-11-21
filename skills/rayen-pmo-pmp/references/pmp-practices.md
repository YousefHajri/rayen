# PMP practice for Newtech projects

Framework: PMI PMBOK Guide 7th ed. (principles + 8 performance domains) and the process-group view still used in the PMP exam (Initiating, Planning, Executing, Monitoring & Controlling, Closing). RAYEN applies it; it does not hold or grant PMP certification.

## Performance domains → what RAYEN produces

| Domain | Artefact in the workbook |
|---|---|
| Stakeholders | Stakeholder register (power/interest, current → desired engagement, communication) |
| Team | RACI (exactly one A per activity, at least one R) |
| Development approach & life cycle | Predictive (waterfall) by default for signage/fit-out; stage gates in `pmo-governance.md` |
| Planning | Charter, WBS, CPM schedule, budget per task (from BOQ/BOM) |
| Project work | Issue log, change log, procurement lead times as tasks |
| Delivery | Scope in/out, acceptance (success) criteria, milestones |
| Measurement | EVM, RAG, KPIs |
| Uncertainty | Risk register (P × I, response, owner, trigger) |

## Charter (minimum content)

Project name & code, sponsor, PM, client, business case / objective (SMART), scope in / out, key milestones, budget (BAC), constraints, assumptions, high-level risks, success criteria, approval line.

## WBS

Deliverable-oriented, 100% rule, typically 3 levels for a signage job: 1 Management & approvals · 2 Design & shop drawings · 3 Procurement · 4 Fabrication · 5 Installation · 6 Testing, handover & closeout. Work packages of 1–10 working days are easiest to track.

## CPM

- ES = max(EF of predecessors + lag); EF = ES + duration.
- LF = min(LS of successors − lag); LS = LF − duration.
- Total float = LS − ES. Critical path = tasks with float 0.
- Working days with Friday + Saturday weekend unless the contract says otherwise; holidays removed.
- Milestones have duration 0.

## Earned value (status date)

| Metric | Formula | Read |
|---|---|---|
| PV | Σ budget × planned % at status date | planned value |
| EV | Σ budget × physical % complete | earned value |
| AC | Σ actual cost | actual cost |
| CV / SV | EV − AC / EV − PV | negative = over cost / behind |
| CPI / SPI | EV / AC, EV / PV | < 1 = poor |
| EAC | BAC / CPI (typical) · AC + (BAC − EV) (atypical) · AC + (BAC − EV)/(CPI × SPI) (both) | forecast at completion |
| ETC | EAC − AC | to complete |
| VAC | BAC − EAC | negative = overrun |
| TCPI | (BAC − EV) / (BAC − AC) | > 1.1 = recovery unlikely without change |

The engine plans value linearly between ES and EF. State this if the S-curve is front- or back-loaded.

## Risk register

ID, description (cause → event → effect), category, probability 1–5, impact 1–5, score, rating, response (Threats: Avoid / Mitigate / Transfer / Accept / Escalate · Opportunities: Exploit / Enhance / Share / Accept), action, owner, due, trigger, status. Typical Newtech risks: late Shop Drawing approval, imported LED/acrylic lead time, municipality permit, site access/crane, structural calculation not issued, colour/RAL mismatch, power availability on site.

## Change control

Request → impact analysis (scope, cost, days, critical path, risk) → decision (CCB / sponsor / client) → update baseline → communicate. Approved variations also update the BOQ and the contract value.

## Close-out

Final acceptance certificate, as-built drawings, O&M manual, warranty, final account, lessons learned (what worked, what to change, owner of the change), archive.
