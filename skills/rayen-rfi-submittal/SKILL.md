---
name: rayen-rfi-submittal
description: "RAYEN technical correspondence for Newtech projects. This skill should be used when the user asks to \"write an RFI\", \"prepare a submittal\", \"material submittal\", \"method statement\", \"reply to NCR\", \"transmittal\", \"ITP\", \"technical query\", \"اكتب RFI\", \"طلب اعتماد مواد\", \"ميثود ستيتمنت\", \"رد على ملاحظات الاستشاري\", or when a conflict between drawings, BOQ and specs is found. Produces formal, numbered documents in Word with references and required responses.\n"
metadata:
  version: "0.2.0"
---

# RAYEN — RFIs, Submittals, Method Statements

Formal documents that a consultant can answer or approve in one pass. Read `../rayen/references/rfi-conflicts-revisions.md` and, for method statements/ITPs, `../rayen/references/site-qaqc-docs.md`. Templates are in `references/templates.md`.

## Rules

- One RFI = one question (or one tightly related set). State: reference documents (no. + rev), what they say, the conflict/gap, technical impact (cost, time, safety), the specific clarification requested, and a proposed resolution when justified. Ask for a response date.
- Numbering: `<PROJECT>-RFI-###`, `<PROJECT>-SUB-###`, `<PROJECT>-MS-###`, revisions R0, R1…
- Submittals: list item, manufacturer, product, spec clause it complies with, attached data (datasheet, sample, test report, warranty), deviations declared explicitly. Never declare compliance that the datasheet does not show — write "compliance TO BE CONFIRMED by consultant".
- Method statements follow the 16-part structure in the reference file and include an HSE risk table; lifting/work-at-height steps reference the lifting plan and permits.
- NCR replies: root cause → immediate correction → corrective action → preventive action → evidence; no blame language.
- Produce the document as DOCX (read the docx skill first), in Arabic or English as the recipient needs; bilingual titles are fine.
- Keep a register: append each RFI/submittal to the project's register (xlsx) with date sent, to, status, days open.
- Draft emails to consultants only as drafts; sending is the user's decision.
