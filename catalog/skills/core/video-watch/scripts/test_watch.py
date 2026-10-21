"""Unit tests for watch.py helpers (stdlib, no FFmpeg needed): python -m unittest test_watch -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watch  # noqa: E402


class TimeTests(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(watch.parse_time("90"), 90)
        self.assertEqual(watch.parse_time("1:30"), 90)
        self.assertEqual(watch.parse_time("01:02:03.5"), 3723.5)
        self.assertIsNone(watch.parse_time(None))
        with self.assertRaises(ValueError):
            watch.parse_time("1:2:3:4")

    def test_fmt_and_srt(self):
        self.assertEqual(watch.fmt_time(12.46), "00:12.5")
        self.assertEqual(watch.fmt_time(3723.5), "1:02:03.5")
        self.assertEqual(watch.srt_time(3723.5), "01:02:03,500")


class SelectTests(unittest.TestCase):
    def test_cap_and_coverage(self):
        scenes = [(t * 0.7, 0.5) for t in range(1, 400)]  # 400 cuts in 280 s
        picks = watch.select_frames(280, scenes, 14, 40)
        self.assertLessEqual(len(picks), 40)
        self.assertEqual(picks[0]["t"], 0.0)
        self.assertGreater(picks[-1]["t"], 250)  # tail of the video is covered
        self.assertEqual([p["t"] for p in picks], sorted(p["t"] for p in picks))

    def test_scene_beats_interval_nearby(self):
        picks = watch.select_frames(20, [(10.1, 0.6)], 10, 40)
        reasons = {p["t"]: p["reason"] for p in picks}
        self.assertIn(10.1, reasons)
        self.assertNotIn(10.0, reasons)  # merged into the stronger scene cut

    def test_short_video(self):
        picks = watch.select_frames(1.5, [], 5, 40)
        self.assertEqual(len(picks), 1)


class IndexTests(unittest.TestCase):
    def test_windows_and_lines(self):
        windows = watch.frame_windows([0, 10, 20], 30)
        self.assertEqual(windows, [(0.0, 5.0), (5.0, 15.0), (15.0, 30)])
        segs = [{"start": 0, "end": 4, "text": "a"}, {"start": 4, "end": 8, "text": "b"},
                {"start": 22, "end": 29, "text": "c"}]
        got = [[s["text"] for s in watch.lines_in_window(segs, lo, hi)] for lo, hi in windows]
        self.assertEqual(got, [["a"], ["b"], ["c"]])

    def test_parse_scenes(self):
        err = ("[Parsed_metadata_2 @ 1] frame:0    pts:12  pts_time:0.5\n"
               "[Parsed_metadata_2 @ 1] lavfi.scene_score=0.412\n"
               "[Parsed_showinfo_3 @ 2] n:   0 pts:  12 pts_time:0.5   duration:1\n")
        self.assertEqual(watch.parse_scenes(err), [(0.5, 0.412)])

    def test_split_lines(self):
        segs = [{"start": 0, "end": 20, "text": "x"}]
        words = [{"start": 0, "end": 1, "word": "Привет."}, {"start": 2, "end": 3, "word": "Как"},
                 {"start": 3, "end": 4, "word": "дела?"}, {"start": 15, "end": 16, "word": "Хорошо"}]
        lines = watch.split_lines(segs, words)
        self.assertEqual([l["text"] for l in lines], ["Привет.", "Как дела?", "Хорошо"])
        self.assertEqual(watch.split_lines([{"start": 0, "end": 3, "text": "y"}], words)[0]["text"], "y")

    def test_layout(self):
        self.assertEqual(watch.sheet_layout(1920, 1080)[:2], (4, 4))
        self.assertEqual(watch.sheet_layout(1080, 1920)[:2], (6, 2))

    def test_forbidden_out(self):
        import tempfile
        root = Path(tempfile.gettempdir()) / "video-watch-forbidden-root"
        saved = watch.FORBIDDEN_OUT
        watch.FORBIDDEN_OUT = [root]
        try:
            with self.assertRaises(watch.WatchError):
                watch.check_out(root / "tmp-watch")
            watch.check_out(root.parent / "video-watch-allowed")  # outside: no error
        finally:
            watch.FORBIDDEN_OUT = saved


if __name__ == "__main__":
    unittest.main()
