# Tool routing and fidelity

| Need | Preferred route | Verification |
| --- | --- | --- |
| Read ordinary DOCX | Word skill / python-docx | inspect full content and tables |
| Edit/create DOCX | Word skill | render every page to PNG |
| Read formulas and displayed values | spreadsheet skill / openpyxl (`data_only` both ways) | inspect formulas and cached values |
| Edit/create XLSX | spreadsheet skill | formula scan, recalculate, render every sheet |
| PDF table extraction | Docling TableFormer; pdfplumber as a cross-check | compare against the rendered page |
| PDF text extraction | Docling; pypdf/pdfplumber for quick reads | keep page/section provenance |
| Scanned PDF, photo or image of a document | VLM OCR (e.g. PaddleOCR-VL); Tesseract/OS OCR as a fallback | verify OCR against the page image |
| Mixed PDF (some scanned pages) | page-by-page routing and merge | check page markers in the merged Markdown |
| Office/PDF to Markdown context | MarkItDown | structure check; no layout claim |
| DOCX/XLSX to PDF | format skill + LibreOffice headless | render and inspect the final PDF |
| PDF to DOCX | text/layout recovery only | disclose fidelity limits; render the DOCX |

Avoid one universal converter. Choose the path from the requested output and from what must survive: formulas,
comments, tracked changes, fields, page geometry, charts, signatures or table structure.

Never overwrite a signed source. A converted copy is a new artifact and does not inherit the original signature.

Licences of the named components: Docling (MIT), PaddleOCR / PaddleOCR-VL (Apache-2.0), MarkItDown (MIT),
pdfplumber (MIT), pypdf (BSD-3-Clause), Tesseract (Apache-2.0).
