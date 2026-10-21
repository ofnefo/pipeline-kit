#!/usr/bin/env python3
"""Automate Photoshop's local Select Subject and export a transparent PNG."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time



def find_photoshop() -> Path | None:
    """Find Photoshop without assuming a release year or a fixed drive."""
    explicit = os.environ.get("PHOTOSHOP_EXE")
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    executable = shutil.which("Photoshop.exe") or shutil.which("photoshop")
    if executable:
        return Path(executable)
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env_name)
        if not root:
            continue
        candidates = sorted(
            Path(root).glob("Adobe/Adobe Photoshop */Photoshop.exe"),
            key=lambda path: path.parent.name.casefold(),
            reverse=True,
        )
        if candidates:
            return candidates[0]
    return None


def jsx_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace('"', '\\"')


def build_jsx(source: Path, output: Path) -> str:
    return f'''#target photoshop

(function () {{
    app.displayDialogs = DialogModes.NO;
    var inputFile = new File("{jsx_path(source)}");
    var outputFile = new File("{jsx_path(output)}");
    if (!inputFile.exists) throw new Error("Input file not found: " + inputFile.fsName);

    var documentRef = app.open(inputFile);
    if (documentRef.activeLayer.isBackgroundLayer) documentRef.activeLayer.isBackgroundLayer = false;
    var s2t = function (value) {{ return app.stringIDToTypeID(value); }};

    var setDescriptor = new ActionDescriptor();
    var prefsDescriptor = new ActionDescriptor();
    var appReference = new ActionReference();
    appReference.putProperty(s2t("property"), s2t("imageProcessingPrefs"));
    appReference.putEnumerated(s2t("application"), s2t("ordinal"), s2t("targetEnum"));
    setDescriptor.putReference(s2t("null"), appReference);
    prefsDescriptor.putEnumerated(
        s2t("imageProcessingSelectSubjectPrefs"),
        s2t("imageProcessingSelectSubjectPrefs"),
        s2t("imageProcessingModeDevice")
    );
    setDescriptor.putObject(s2t("to"), s2t("imageProcessingPrefs"), prefsDescriptor);
    executeAction(s2t("set"), setDescriptor, DialogModes.NO);

    var selectDescriptor = new ActionDescriptor();
    selectDescriptor.putBoolean(s2t("sampleAllLayers"), false);
    executeAction(s2t("autoCutout"), selectDescriptor, DialogModes.NO);

    var maskDescriptor = new ActionDescriptor();
    var maskReference = new ActionReference();
    maskDescriptor.putClass(s2t("new"), s2t("channel"));
    maskReference.putEnumerated(s2t("channel"), s2t("channel"), s2t("mask"));
    maskDescriptor.putReference(s2t("at"), maskReference);
    maskDescriptor.putEnumerated(s2t("using"), s2t("userMaskEnabled"), s2t("revealSelection"));
    executeAction(s2t("make"), maskDescriptor, DialogModes.NO);

    var exportOptions = new ExportOptionsSaveForWeb();
    exportOptions.format = SaveDocumentType.PNG;
    exportOptions.PNG8 = false;
    exportOptions.transparency = true;
    exportOptions.interlaced = false;
    documentRef.exportDocument(outputFile, ExportType.SAVEFORWEB, exportOptions);
    documentRef.close(SaveOptions.DONOTSAVECHANGES);
}}());
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--photoshop", type=Path, help="Photoshop executable; defaults to PHOTOSHOP_EXE or auto-detection")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    photoshop = args.photoshop or find_photoshop()
    if not photoshop or not photoshop.is_file():
        raise FileNotFoundError("Photoshop executable not found; pass --photoshop or set PHOTOSHOP_EXE")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        args.output.unlink()

    script_text = build_jsx(args.input, args.output)
    script_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".jsx", encoding="utf-8-sig", delete=False) as stream:
            stream.write(script_text)
            script_path = Path(stream.name)
        subprocess.Popen([str(photoshop), str(script_path)])
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if args.output.is_file() and args.output.stat().st_size > 0:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(errors="backslashreplace")
                print(str(args.output.resolve()))
                return 0
            time.sleep(0.5)
        raise TimeoutError(f"Photoshop did not create output within {args.timeout:g}s: {args.output}")
    finally:
        if script_path and script_path.exists():
            try:
                script_path.unlink()
            except PermissionError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
