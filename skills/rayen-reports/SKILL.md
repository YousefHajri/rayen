---
name: rayen-reports
description: "RAYEN project reporting for Newtech's technical office. This skill should be used when the user asks for a \"weekly report\", \"status report\", \"project report\", \"what's pending\", \"where are my projects\", \"progress report\", \"تقرير أسبوعي\", \"تقرير المشاريع\", \"وين وصلت المشاريع\", \"ايش المعلق\", or when a scheduled task asks RAYEN to report. Gathers facts from connected sources (Google Drive, Gmail, Google Calendar, Notion, memory, past chats) and produces a decision-oriented Word report with RAG status, open RFIs/submittals, actions and risks.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — Project Reports

A report exists to get decisions and unblock work. Lead with what is late, why, and what is needed from whom by when.

## 1. Gather (read-only)

Search the connected sources for the reporting period; cite every fact with its source.

| Source | Look for |
|---|---|
| Past chats & memory | Active projects, decisions, open questions the user discussed with Claude |
| Google Drive | Project folders, latest drawing revisions, BOQs, transmittals, meeting minutes |
| Gmail | Client/consultant/supplier threads: approvals, comments, RFIs, delivery dates |
| Google Calendar | Site visits, meetings, handovers, deadlines in the period |
| Notion | Project trackers, task lists |

Only report what a source shows. If progress % is not stated anywhere, ask once or mark it NOT VERIFIED — never estimate silently. Do not send, reply, or change anything in these tools while reporting.

## 2. Structure the data

Write a JSON in the shape of `examples/weekly-status.json` (or `python3 scripts/report.py --example`): `title`, `period`, `to`, `headline` (one sentence: count of projects, what is red and why), `projects[]` (name, stage, progress, planned, rag, status, next, due, owner, source), `open_items[]` (RFIs/submittals with days open), `actions[]`, `risks[]`, `unverified[]`. Use `lang: "ar"` (default) or `"en"`.

RAG rules: RED = critical path late or blocked by an external approval past due; AMBER = slipping < 1 week or waiting on input; GREEN = on plan.

## 3. Produce

```
python3 scripts/report.py status.json -o "<YYYY-MM-DD> RAYEN Weekly Report.docx"
```
The script adds KPI tiles, an actual-vs-planned chart, coloured RAG cells, and a sources list. Convert to PDF when the user wants to forward it. Render page 1 to an image and check it before delivering.

## 4. Deliver

In chat: the headline, the red items with the single action that unblocks each, and the file. Offer to draft (not send) a follow-up email for overdue RFIs.

For a recurring report, propose a scheduled task (e.g. Sunday 08:30 Riyadh) whose prompt asks RAYEN to run this skill for the past week and save the report to Drive.
