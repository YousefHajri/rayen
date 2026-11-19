# RAYEN · رايان

**Newtech Technical Office Agent** — a Claude plugin that works as a senior architectural & technical-office engineer for Newtech (signage, LED displays, interior fit-out) in Riyadh.

وكيل ذكي للمكتب الفني في نيوتك: مخططات تنفيذية (DXF)، جداول كميات قابلة للتتبع (Excel)، تقارير حالة المشاريع (Word)، طلبات RFI والاعتمادات و Method Statements — بالعربية والإنجليزية.

---

## ما الذي يقدّمه RAYEN (v0.2)

| المهارة | ماذا تفعل | المخرج |
|---|---|---|
| `rayen` | العقل الرئيسي: مراجعة المخططات، التصنيع، التنسيق، QA/QC، Value Engineering، مشاكل الموقع — وفق أولويات السلامة والكود السعودي | رد هندسي مصنّف (VERIFIED / ASSUMED / TBC) |
| `rayen-architectural-design` **جديد** | تصميم معماري من الفكرة إلى DD: برنامج مساحات، Zoning، واجهات، مناخ الرياض، الهوية النجدية/السلمانية، Egress و Accessibility، مراجعة التصاميم | `XLSX` برنامج مساحات + Occupant Load، تقرير مراجعة |
| `rayen-interior-design` **جديد** | تصميم داخلي وفت أوت: توزيع، RCP، حساب إضاءة (Lumen method)، جداول تشطيبات و FF&E، نجارة وأسقف وقواطع، مجالس، محلات، مطاعم | `XLSX` إضاءة + جداول، تفاصيل |
| `rayen-bim` **جديد** | BIM Manager: ISO 19650، BEP، Clash Matrix، تدقيق IFC، كميات من الموديل — **LOD 300 & 400**: بناء موديل تنسيقي LOD 300 وموديل تصنيعي LOD 400 من مواصفات الشوب دروينج، فحص أي IFC مقابل متطلبات LOD، باراميترات Revit و Dynamo | `IFC` LOD 300/400 + `XLSX` فحص LOD + Parts list |
| `rayen-render` **جديد** | رندر واقعي بـ Blender (Cycles): مشاهد JSON، مكتبة خامات، إضاءة نهارية/ليلية للوحات، استيراد IFC/GLB/OBJ/FBX/SVG | `PNG` + `.blend` + `.glb` |
| `rayen-fabrication` **جديد** | مخططات تصنيع: ملفات CNC/ليزر لكل قطعة (طبقات CUT/DRILL/BEND)، فرد الصاج بالـ Bend Allowance و K-factor، أطوال Returns للحروف، Parts list | `DXF` لكل قطعة + Parts sheet + `XLSX` |
| `rayen-newtech-template` **جديد** | يضع أي مخرج داخل **قالب نيوتك الأصلي المعتمد**: الغلاف، اللوحات بالشعار وشريط العنوان و DWG الذهبي ولوحات (تعديلات التصميم / تفاصيل أمر العمل / تفاصيل التصميم / عدد الجونت)، صفحة الختام | `PDF` + `PNG` + إطار `DXF` |
| `rayen-shop-drawing` | مولّد مخططات تنفيذية بارامتري: Lightbox، Pylon، Graphic Frame | `DXF` بطبقات + `PDF` + `PNG` + ملف كميات |
| `rayen-boq-qto` | حصر كميات: أوزان الحديد، Nesting، الهدر منفصل، معادلات Excel حية | `XLSX` |
| `rayen-reports` | تقرير أسبوعي من Drive و Gmail و Calendar و Notion | `DOCX` |
| `rayen-rfi-submittal` | RFI، اعتماد مواد، Method Statement، رد NCR، Transmittal | `DOCX` + سجل |
| Agent `rayen` | ينادي المهارة المناسبة تلقائياً عند مخاطبة "RAYEN" أو "رايان" | — |

### السلسلة المترابطة
```
Brief ─▶ Program (XLSX) ─▶ Concept + Render (PNG) ─▶ Layout / RCP / Lighting (XLSX)
   ─▶ BIM / IFC audit ─▶ Shop Drawing (DXF) ─▶ Fabrication CNC parts (DXF) ─▶ BOQ (XLSX)
   ─▶ Newtech Drawing Set (PDF بقالب نيوتك الأصلي) ─▶ RFI / Submittal ─▶ Weekly Report
```

---

## التثبيت

### من GitHub داخل Claude Code (الأسرع)
```
/plugin marketplace add YousefHajri/rayen
/plugin install rayen@rayen
```

### 1) داخل تطبيق Claude (claude.ai / Desktop)
1. حمّل ملف `rayen.plugin` من صفحة **Releases** أو من المحادثة.
2. افتحه في Claude واضغط **Install / Accept**.
3. اكتب: `RAYEN، جهّز Shop Drawing لـ Lightbox 2400×800×150`.

### 2) Claude Code (سطر الأوامر)
```bash
git clone https://github.com/Qadoora249/rayen-agent.git
claude plugin install ./rayen-agent
```

### 3) تثبيت البرامج المطلوبة للتشغيل (مرة واحدة)
Windows (PowerShell):
```
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -WithBlender
```
macOS / Linux:
```bash
bash scripts/setup.sh --with-blender
```
يثبّت: ezdxf, openpyxl, python-docx, matplotlib, ifcopenshell, trimesh, arabic-reshaper, python-bidi, pymupdf — و bpy (Blender) للرندر (يتطلب Python 3.13، أو ثبّت Blender من blender.org). في النهاية يشغّل `scripts/selftest.py` ويختبر كل المولّدات.

### إضافات مكمّلة (موصى بها)
| الإضافة / الموصل | الاستخدام |
|---|---|
| **revit-bim** plugin | العمل داخل Revit/Dynamo و ACC (تدقيق موديل، جداول، باراميترات، IFC export) |
| **pdf-viewer** plugin | فتح وتعليم مخططات PDF |
| Trimble SketchUp · kernelCAD · Autodesk Product Help | نمذجة، أجزاء بارامترية، مساعدة برامج Autodesk |
| Canva · Gamma · Figma | لوحات المواد، العروض، صور المزاج |
| Google Drive · Gmail · Calendar · Notion | ملفات المشاريع وقوالب نيوتك والمراسلات |

---

## الموصلات (MCP)

ملف `.mcp.json` يربط RAYEN بـ:

| الموصل | الاستخدام |
|---|---|
| Google Drive | مجلدات المشاريع، المخططات، الـ BOQ |
| Gmail | مراسلات الاستشاري والعميل والموردين (قراءة + مسودات فقط) |
| Google Calendar | زيارات الموقع، الاجتماعات، مواعيد التسليم |
| Notion | متابعة المهام والمشاريع |
| Figma | عروض ولوحات تصميم الـ Signage |
| GitHub | تحديث RAYEN نفسه وسجل الإصدارات |

يعمل أيضاً مع الموصلات المفعّلة في حسابك مثل Trimble SketchUp و kernelCAD و Canva و Gamma للنمذجة والعروض.

---

## أمثلة

```bash
# اختبار شامل لكل الأدوات
python3 scripts/selftest.py
# رندر واقعي
python3 skills/rayen-render/scripts/render.py skills/rayen-render/examples/reception.json -o renders
# ملفات CNC للقطع + فرد الصاج
python3 skills/rayen-fabrication/scripts/fab_parts.py skills/rayen-fabrication/examples/lightbox-parts.json -o fab
# موديل LOD 400 من مواصفات الشوب دروينج + فحصه
python3 skills/rayen-bim/scripts/lod_build.py skills/rayen-shop-drawing/examples/pylon.json --lod 400 -o P01-LOD400.ifc
python3 skills/rayen-bim/scripts/lod_check.py P01-LOD400.ifc --lod 400 --overlap -o P01-LOD400-Check.xlsx
# تدقيق IFC + Clash
python3 skills/rayen-bim/scripts/ifc_audit.py model.ifc --clash IfcWall,IfcBeam IfcDuctSegment -o audit.xlsx
# حساب إضاءة / برنامج مساحات
python3 skills/rayen-interior-design/scripts/lighting_calc.py skills/rayen-interior-design/examples/rooms-lighting.json -o lighting.xlsx
python3 skills/rayen-architectural-design/scripts/space_program.py skills/rayen-architectural-design/examples/office-program.json -o program.xlsx
# تجميع المخططات بقالب نيوتك الأصلي
python3 skills/rayen-newtech-template/scripts/newtech_sheet.py package.json -o "WO Drawings.pdf" --png
# مخطط تنفيذي + ملف كميات
python3 skills/rayen-shop-drawing/scripts/shop_drawing.py skills/rayen-shop-drawing/examples/pylon.json -o NT-SD-P01-R0 --qto p01-qto.json
# BOQ من نفس الملف
python3 skills/rayen-boq-qto/scripts/qto.py p01-qto.json -o NT-P01-BOQ-R0.xlsx
# تقرير أسبوعي
python3 skills/rayen-reports/scripts/report.py skills/rayen-reports/examples/weekly-status.json -o Weekly-Report.docx
```

---

## حدود واضحة

- RAYEN لا يعتمد تصميماً إنشائياً: البايلونات واللوحات المرتفعة تحتاج حسابات مهندس إنشائي مؤهل (SBC 301).
- ملف DXF ليس جاهزاً للقص الآلي قبل التحقق من الأبعاد والوحدات والإغلاق والتفاوتات.
- الأسعار تقديرية ما لم يُذكر عرض سعر مورد.
- لا يرسل بريداً أو يعدّل أنظمة دون موافقتك.
- القيم الكودية في المراجع "نموذجية" (عائلة IBC التي بُني عليها SBC) ويجب التحقق منها من إصدار SBC المعتمد للمشروع.
- الرندر "CONCEPTUAL" وليس مستند تنفيذ؛ ملفات فرد الصاج "CALCULATED" وتُعتمد بعد تجربة ثني في الورشة.

---

**Author:** Abdelgadir Abdalla — Senior Architectural Engineer, Newtech, Riyadh · v0.3.0
