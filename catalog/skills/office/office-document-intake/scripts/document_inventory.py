#!/usr/bin/env python3
"""Read-only office document inventory with optional SHA-256 hashing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

SUPPORTED = {
    ".pdf", ".docx", ".docm", ".xlsx", ".xlsm", ".xls", ".pptx", ".pptm",
    ".csv", ".tsv", ".txt", ".md", ".json", ".xml", ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".zip", ".epub",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}
CATEGORIES = {
    "estimate": ("смет", "estimate", "budget", "бюджет", "калькуляц"),
    "price-list": ("прайс", "price", "rate", "тариф"),
    "contract": ("договор", "contract", "соглашен", "appendix", "приложен"),
    "act": ("акт", "acceptance"),
    "invoice": ("счет", "счёт", "invoice", "payment"),
    "proposal": ("кп", "предлож", "proposal", "quote"),
    "report": ("отчет", "отчёт", "report"),
    "tender": ("тендер", "tender", "тз", "техническ", "закуп"),
    "letter": ("письм", "letter"),
}


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(name: str) -> str:
    folded = name.casefold()
    for category, hints in CATEGORIES.items():
        if any(hint in folded for hint in hints):
            return category
    return "other"


def zip_details(path: Path, warnings: list[str]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            macro = any(name.casefold().endswith("vbaproject.bin") for name in names)
            if macro:
                warnings.append("OOXML package contains VBA; macros were not executed.")
            suffix = path.suffix.casefold()
            if suffix in {".docx", ".docm"}:
                if "word/document.xml" not in names:
                    warnings.append("DOCX container is missing word/document.xml.")
                else:
                    root = ElementTree.fromstring(archive.read("word/document.xml"))
                    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                    details["paragraphs_approx"] = len(root.findall(f".//{ns}p"))
                    details["tables"] = len(root.findall(f".//{ns}tbl"))
            elif suffix in {".xlsx", ".xlsm"}:
                if "xl/workbook.xml" not in names:
                    warnings.append("XLSX container is missing xl/workbook.xml.")
                else:
                    root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
                    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                    details["sheets"] = [node.attrib.get("name", "") for node in root.findall(f".//{ns}sheet")]
            elif suffix in {".pptx", ".pptm"}:
                details["slides"] = len([name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")])
            details["macro_enabled"] = macro
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        warnings.append(f"Invalid or unreadable OOXML/ZIP container: {exc}")
    return details


def inspect(path: Path, root: Path, include_hash: bool) -> dict[str, Any]:
    stat = path.stat()
    suffix = path.suffix.casefold()
    warnings: list[str] = []
    details: dict[str, Any] = {}
    if suffix in {".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm"}:
        details.update(zip_details(path, warnings))
    elif suffix == ".pdf":
        try:
            with path.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    warnings.append("File extension is PDF but signature is not %PDF-.")
        except OSError as exc:
            warnings.append(f"Cannot read PDF signature: {exc}")
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "name": path.name,
        "extension": suffix,
        "category": classify(path.name),
        "bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "sha256": sha256(path) if include_hash else None,
        "details": details,
        "warnings": warnings,
    }


def inventory(root: Path, *, include_hash: bool, max_files: int) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")
    files: list[dict[str, Any]] = []
    skipped = 0
    truncated = False
    for current, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(names):
            path = Path(current) / name
            if path.suffix.casefold() not in SUPPORTED:
                skipped += 1
                continue
            if len(files) >= max_files:
                truncated = True
                break
            try:
                files.append(inspect(path, root, include_hash))
            except OSError as exc:
                files.append({"relative_path": path.relative_to(root).as_posix(), "name": name, "extension": path.suffix.casefold(), "category": classify(name), "bytes": None, "modified_utc": None, "sha256": None, "details": {}, "warnings": [str(exc)]})
        if truncated:
            break
    categories: dict[str, int] = {}
    for item in files:
        categories[item["category"]] = categories.get(item["category"], 0) + 1
    return {
        "schema_version": 1,
        "root": str(root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hashes_included": include_hash,
        "file_count": len(files),
        "unsupported_skipped": skipped,
        "truncated": truncated,
        "categories": categories,
        "files": files,
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Document inventory",
        "",
        f"- Root: `{result['root']}`",
        f"- Supported files: {result['file_count']}",
        f"- Unsupported files skipped: {result['unsupported_skipped']}",
        f"- SHA-256 included: {'yes' if result['hashes_included'] else 'no'}",
        f"- Truncated: {'yes' if result['truncated'] else 'no'}",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in sorted(result["categories"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "| File | Type | Category | Bytes | Warnings |", "| --- | --- | --- | ---: | --- |"])
    for item in result["files"]:
        warning = "; ".join(item["warnings"]).replace("|", "\\|")
        lines.append(f"| `{item['relative_path']}` | {item['extension']} | {item['category']} | {item['bytes'] or 0} | {warning} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="Inventory office documents without modifying them.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--hash", action="store_true", dest="include_hash")
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.max_files < 1:
            raise ValueError("--max-files must be positive")
        result = inventory(args.root, include_hash=args.include_hash, max_files=args.max_files)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else markdown_report(result)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(rendered)
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
