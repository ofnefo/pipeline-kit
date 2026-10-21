# Scribus 1.6 (InDesign alternative)

- Licence GPL-2.0-or-later. Print checks (CMYK, bleed, dimensions) still need a separate preflight.

## Verified (Scribus 1.6.6, Windows)
- `Scribus --version` → `Scribus 1.6.6`, exit 0.
- `Scribus -g -ns -py /path/scribus_pdf.py /path/out.pdf` → exit 0, ~9 s; A4 PDF plus `out.sla`, Cyrillic text OK.

`scribus_pdf.py`:
```python
import sys, scribus
out = sys.argv[1] if len(sys.argv) > 1 else "scribus_out.pdf"
scribus.newDocument(scribus.PAPER_A4, (15,15,15,15), scribus.PORTRAIT, 1, scribus.UNIT_MILLIMETERS, scribus.PAGE_1, 0, 1)
f = scribus.createText(20, 20, 170, 40)
scribus.setText("Scribus headless PDF test / Проверка кириллицы", f)
scribus.setFontSize(18, f)
pdf = scribus.PDFfile(); pdf.file = out; pdf.save()
scribus.saveDocAs(out[:-4] + ".sla"); scribus.closeDoc()
```
To export an existing layout: `scribus.openDoc(path)` instead of `newDocument`, then the same `PDFfile()` block (not verified).

## Caveats
- Script arguments go **directly after** the script path. `-py script.py -- out.pdf` fails with "file does not exist, aborting" (exit 1).
- `-g` = no GUI, `-ns` = no splash. Script API reference: Scribus GUI Help → Scripter.
