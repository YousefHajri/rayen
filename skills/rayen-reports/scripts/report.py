#!/usr/bin/env python3
"""
RAYEN project status report generator (DOCX + progress chart PNG).

Input: JSON gathered by RAYEN from the user's connected sources (Drive, Gmail,
Calendar, Notion, chat history) — every fact carries its source.
Output: a decision-oriented weekly/project report in Word, Arabic (RTL) or English.

Usage:
  python3 report.py status.json -o Weekly-Report.docx
  python3 report.py --example > status.json
"""
import argparse
import json
import sys
from datetime import date

EXAMPLE = {
    "lang": "ar",
    "title": "تقرير الحالة الأسبوعي — المكتب الفني",
    "period": "2026-11-15 → 2026-11-19",
    "prepared_by": "RAYEN / عبدالقادر عبدالله",
    "to": "المدير التنفيذي للمبيعات والمشاريع",
    "headline": "3 مشاريع نشطة: مشروع واحد متأخر بسبب اعتماد Shop Drawing، وطلب RFI معلق منذ 6 أيام.",
    "projects": [
        {"name": "جامعة المعرفة — لوحات داخلية", "stage": "Fabrication", "progress": 65, "planned": 75,
         "rag": "AMBER", "status": "تصنيع الإطارات 30×30 جارٍ؛ الأكريليك بانتظار التوريد.",
         "next": "استلام الأكريليك واعتماد عيّنة المغناطيس", "due": "2026-11-24", "owner": "المصنع / المشتريات",
         "source": "Gmail: supplier thread 2026-11-16"},
        {"name": "Retail Park — Pylon P-01", "stage": "Shop Drawing", "progress": 30, "planned": 50,
         "rag": "RED", "status": "بانتظار الحسابات الإنشائية والأساسات قبل إصدار الـ Shop Drawing النهائي.",
         "next": "استلام Structural calc من الاستشاري", "due": "2026-11-20", "owner": "الاستشاري الإنشائي",
         "source": "Drive: P-01 folder, RFI-001"},
        {"name": "Lightbox LB-01", "stage": "Installation", "progress": 90, "planned": 90,
         "rag": "GREEN", "status": "التركيب مكتمل؛ متبقٍّ الفحص الكهربائي والتسليم.",
         "next": "Snag & handover", "due": "2026-11-21", "owner": "فريق الموقع",
         "source": "Calendar: site visit 2026-11-18"}
    ],
    "open_items": [
        {"ref": "RFI-001", "type": "RFI", "subject": "ارتفاع البايلون 4200 مقابل 4000 في الـ BOQ", "sent": "2026-11-11",
         "days_open": 6, "with": "الاستشاري", "impact": "HIGH"},
        {"ref": "SUB-014", "type": "Submittal", "subject": "عينة أكريليك 3mm شفاف", "sent": "2026-11-14",
         "days_open": 3, "with": "العميل", "impact": "MEDIUM"}
    ],
    "actions": [
        {"action": "متابعة RFI-001 هاتفياً مع الاستشاري", "owner": "عبدالقادر", "due": "2026-11-18"},
        {"action": "طلب عرض سعر ثانٍ للأكريليك لتقليل مدة التوريد", "owner": "المشتريات", "due": "2026-11-19"}
    ],
    "risks": [
        {"risk": "تأخر الحسابات الإنشائية للبايلون", "impact": "تأخير التسليم أسبوعين", "level": "HIGH",
         "mitigation": "تجهيز Shop Drawing بالمقاطع الأولية بالتوازي، والإصدار فور الاعتماد"}
    ],
    "unverified": ["نسبة الإنجاز في LB-01 من آخر زيارة موقع، لم تُحدَّث بعد 18/11."]
}

RAG_COLOR = {"GREEN": "C6EFCE", "AMBER": "FFEB9C", "RED": "FFC7CE"}
LBL = {
    "ar": dict(summary="الخلاصة", to="إلى", by="إعداد", period="الفترة", date="التاريخ", proj="حالة المشاريع",
               cols=["المشروع", "المرحلة", "الإنجاز", "المخطط", "الحالة", "الملاحظة", "الخطوة التالية", "الموعد", "المسؤول"],
               open="البنود المفتوحة (RFI / Submittals)", ocols=["المرجع", "النوع", "الموضوع", "تاريخ الإرسال", "أيام", "لدى", "الأثر"],
               act="الإجراءات المطلوبة", acols=["الإجراء", "المسؤول", "الموعد"],
               risk="المخاطر", rcols=["الخطر", "الأثر", "المستوى", "المعالجة"],
               unv="معلومات غير مؤكدة", src="المصادر", chart="الإنجاز الفعلي مقابل المخطط"),
    "en": dict(summary="Summary", to="To", by="Prepared by", period="Period", date="Date", proj="Project status",
               cols=["Project", "Stage", "Actual", "Planned", "RAG", "Status", "Next step", "Due", "Owner"],
               open="Open items (RFIs / Submittals)", ocols=["Ref", "Type", "Subject", "Sent", "Days", "With", "Impact"],
               act="Actions required", acols=["Action", "Owner", "Due"],
               risk="Risks", rcols=["Risk", "Impact", "Level", "Mitigation"],
               unv="Not verified", src="Sources", chart="Actual vs planned progress"),
}


def chart(projects, path, lang):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fix = lambda t: t  # matplotlib >= 3.8 shapes Arabic itself; do not pre-reshape
    names = [fix(p["name"][:32]) for p in projects]
    act = [p.get("progress", 0) for p in projects]
    plan = [p.get("planned", p.get("progress", 0)) for p in projects]
    cols = {"GREEN": "#3A9D5D", "AMBER": "#E3A008", "RED": "#D64545"}
    fig, ax = plt.subplots(figsize=(7.5, 0.6 + 0.55 * len(projects)))
    y = range(len(projects))
    ax.barh(list(y), plan, color="#D9DEE7", height=0.55, label="Planned")
    ax.barh(list(y), act, color=[cols.get(p.get("rag", "GREEN"), "#1F2A44") for p in projects], height=0.3, label="Actual")
    for i, (a, pl) in enumerate(zip(act, plan)):
        ax.text(max(a, pl) + 1.5, i, f"{a}% / {pl}%", va="center", fontsize=8)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 115)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel("%")
    ax.legend(loc="lower right", fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def build(data, out):
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    lang = data.get("lang", "ar")
    L = LBL[lang]
    rtl = lang == "ar"
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    if rtl:
        sec._sectPr.append(OxmlElement("w:bidi"))
    st = doc.styles["Normal"]
    st.font.name = "Arial"
    st.font.size = Pt(10)
    st.element.rPr.rFonts.set(qn("w:cs"), "Arial")

    def para(text="", bold=False, size=None, color=None, align=None, space_after=4):
        p = doc.add_paragraph()
        if rtl:
            p.paragraph_format.element.get_or_add_pPr().append(OxmlElement("w:bidi"))
        r = p.add_run(text)
        r.bold = bold
        if rtl:
            rp = r._element.get_or_add_rPr()
            rp.append(OxmlElement("w:rtl"))
            if bold:
                rp.append(OxmlElement("w:bCs"))
        if size:
            r.font.size = Pt(size)
            r._element.get_or_add_rPr().append(_sz_cs(size))
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        if align:
            p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        return p

    def _sz_cs(size):
        e = OxmlElement("w:szCs")
        e.set(qn("w:val"), str(int(size * 2)))
        return e

    def shade(cell, hexcolor):
        tcPr = cell._element.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hexcolor)
        tcPr.append(shd)

    def table(headers, rows, widths=None, rag_col=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        if rtl:
            tblPr = t._element.tblPr
            bv = OxmlElement("w:bidiVisual")
            tblPr.append(bv)
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            c.text = ""
            r = c.paragraphs[0].add_run(h)
            r.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            shade(c, "1F2A44")
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                p = cells[i].paragraphs[0]
                if rtl:
                    p.paragraph_format.element.get_or_add_pPr().append(OxmlElement("w:bidi"))
                rr = p.add_run(str(v))
                rr.font.size = Pt(8.5)
                if rag_col is not None and i == rag_col and str(v).upper() in RAG_COLOR:
                    shade(cells[i], RAG_COLOR[str(v).upper()])
        if widths:
            t.autofit = False
            for i, w in enumerate(widths):
                t.columns[i].width = Cm(w)
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    # ---- header
    para("NEWTECH — TECHNICAL OFFICE", bold=True, size=9, color="7F8899")
    para(data.get("title", "Status report"), bold=True, size=17, color="1F2A44", space_after=2)
    para(f"{L['period']}: {data.get('period','')}   |   {L['date']}: {date.today().isoformat()}", size=9, color="555555", space_after=1)
    para(f"{L['to']}: {data.get('to','')}   |   {L['by']}: {data.get('prepared_by','RAYEN')}", size=9, color="555555")

    # ---- summary
    projects = data.get("projects", [])
    reds = sum(1 for p in projects if p.get("rag") == "RED")
    ambers = sum(1 for p in projects if p.get("rag") == "AMBER")
    para(L["summary"], bold=True, size=12, color="1F2A44")
    para(data.get("headline", ""), size=10.5)
    kpi = doc.add_table(rows=2, cols=4)
    kpi.style = "Table Grid"
    if rtl:
        kpi._element.tblPr.append(OxmlElement("w:bidiVisual"))
    labels = (["المشاريع", "متأخر (RED)", "تحت المراقبة", "بنود مفتوحة"] if rtl else ["Projects", "Red", "Amber", "Open items"])
    vals = [len(projects), reds, ambers, len(data.get("open_items", []))]
    fills = ["DDEBF7", "FFC7CE", "FFEB9C", "E4DFEC"]
    for i in range(4):
        kpi.rows[0].cells[i].text = labels[i]
        c = kpi.rows[1].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(vals[i]))
        r.bold = True
        r.font.size = Pt(18)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        shade(c, fills[i])
    doc.add_paragraph()

    # ---- chart + project table
    if projects:
        png = out.rsplit(".", 1)[0] + "-progress.png"
        chart(projects, png, lang)
        para(L["proj"], bold=True, size=12, color="1F2A44")
        doc.add_picture(png, width=Cm(16))
        table(L["cols"], [[p["name"], p.get("stage", ""), f"{p.get('progress',0)}%", f"{p.get('planned','-')}%",
                           p.get("rag", ""), p.get("status", ""), p.get("next", ""), p.get("due", ""), p.get("owner", "")]
                          for p in projects], widths=[2.5, 2.0, 1.3, 1.3, 1.7, 3.3, 2.3, 2.0, 1.8], rag_col=4)
    if data.get("open_items"):
        para(L["open"], bold=True, size=12, color="1F2A44")
        table(L["ocols"], [[o["ref"], o["type"], o["subject"], o["sent"], o["days_open"], o["with"], o["impact"]]
                           for o in data["open_items"]], widths=[1.7, 1.9, 5.0, 2.2, 1.0, 2.2, 1.6])
    if data.get("actions"):
        para(L["act"], bold=True, size=12, color="1F2A44")
        table(L["acols"], [[a["action"], a["owner"], a["due"]] for a in data["actions"]], widths=[10, 4, 3])
    if data.get("risks"):
        para(L["risk"], bold=True, size=12, color="1F2A44")
        table(L["rcols"], [[r["risk"], r["impact"], r["level"], r["mitigation"]] for r in data["risks"]], widths=[4.5, 4, 1.6, 7])
    if data.get("unverified"):
        para(L["unv"], bold=True, size=11, color="9C5700")
        for u in data["unverified"]:
            para("• " + u, size=9)
    srcs = sorted({p.get("source", "") for p in projects if p.get("source")})
    if srcs:
        para(L["src"], bold=True, size=10, color="7F8899")
        for s in srcs:
            para("• " + s, size=8, color="7F8899", space_after=0)
    doc.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--out", default="Status-Report.docx")
    ap.add_argument("--example", action="store_true")
    a = ap.parse_args()
    if a.example:
        json.dump(EXAMPLE, sys.stdout, indent=2, ensure_ascii=False)
        return
    if not a.input:
        ap.error("input JSON required (or --example)")
    data = json.load(open(a.input, encoding="utf-8"))
    build(data, a.out)
    print(f"Report written: {a.out}")


if __name__ == "__main__":
    main()
