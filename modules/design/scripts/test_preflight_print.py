"""CPU CLI regression using synthetic images only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageCms

SCRIPT = Path(os.environ.get("PREFLIGHT_SCRIPT", str(Path(__file__).with_name("preflight_print.py"))))


class PrintPreflightExitTests(unittest.TestCase):
    def check_case(self, status, code, width_mm=101.6, height_mm=101.6, icc=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "synthetic.png"
            report = root / "report.json"
            options = {}
            if icc:
                options["icc_profile"] = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            Image.new("RGB", (400, 400), (80, 120, 160)).save(source, **options)
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            result = subprocess.run([
                sys.executable, "-B", str(SCRIPT), "--input", str(source),
                "--width-mm", str(width_mm), "--height-mm", str(height_mm),
                "--target-ppi", "100", "--output", str(report),
            ], capture_output=True, text=True, timeout=30)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], status, result.stderr)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), payload)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertEqual(result.returncode, code, payload)

    def test_pass_returns_zero(self):
        self.check_case("PASS", 0)

    def test_missing_icc_remains_nonblocking(self):
        self.check_case("PASS_WITH_CONDITIONS", 0, icc=False)

    def test_moderate_resolution_remains_nonblocking(self):
        self.check_case("PASS_WITH_CONDITIONS", 0, width_mm=135.4667, height_mm=135.4667)

    def test_low_resolution_blocks_exit(self):
        self.check_case("BLOCKED", 1, width_mm=254, height_mm=254)

    def test_aspect_mismatch_blocks_exit(self):
        self.check_case("BLOCKED", 1, width_mm=101.6, height_mm=50.8)


if __name__ == "__main__":
    unittest.main()
