"""Acceptance tests. Real ffmpeg media, real renders. Run:  python3 studio/tests/test_studio.py"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent
IGO = [sys.executable, str(HERE / "igo.py")]
SKILLS = Path.home() / ".claude/skills"
TMP = Path(tempfile.mkdtemp(prefix="igo-test-"))


def igo(*a, ok=True):
    r = subprocess.run([*IGO, *map(str, a)], capture_output=True, text=True, env={**os.environ, "IGO_BRANDS": str(TMP / "brands")})
    if ok:
        assert r.returncode == 0, f"igo {a} failed: {r.stdout}{r.stderr}"
    return r


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *map(str, a)], check=True)


def make_clip(name, dur=3, w=1280, h=720, vol=0.3, black=False, audio=True):
    p = TMP / name
    src = f"color=c=black:s={w}x{h}:r=30:d={dur}" if black else f"testsrc2=s={w}x{h}:r=30:d={dur}"
    args = ["-f", "lavfi", "-i", src]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=f=440:d={dur}"]
    ff(*args, "-af", f"volume={vol}" if audio else "anull", *(["-c:a", "aac"] if audio else ["-an"]), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", p) if audio else \
        ff(*args, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", p)
    return p


class Dependencies(unittest.TestCase):
    def test_tools_and_filters(self):
        for t in ("ffmpeg", "ffprobe"):
            self.assertTrue(shutil.which(t), t)
        f = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        for flt in ("loudnorm", "blackdetect", "freezedetect", "sidechaincompress", "astats", "xfade"):
            self.assertIn(flt, f)

    def test_hw_report(self):
        j = json.loads(igo("hw").stdout)
        self.assertGreaterEqual(j["cpus"], 1)
        self.assertIn("recommend", j)


class SkillDiscovery(unittest.TestCase):
    def test_repo_skill_frontmatter(self):
        for sk in (REPO / "skills").glob("*/SKILL.md"):
            t = sk.read_text()
            self.assertTrue(t.startswith("---"), sk)
            self.assertIn(f"name: {sk.parent.name}", t)
            self.assertIn("description:", t)

    @unittest.skipUnless((SKILLS / "video-studio").exists(), "skills not installed on this machine")
    def test_catalog_skills_installed(self):
        cat = json.loads((REPO / "skills/video-studio/catalog.json").read_text())
        names = {s for d in cat.values() for s in d}
        hf = list((Path.home() / ".claude/plugins/cache/hyperframes").glob("*/*/skills/*"))
        have = {p.name for p in SKILLS.iterdir()} | {p.name for p in hf}
        missing = sorted(names - have)
        self.assertEqual(missing, [], f"catalog lists skills that are not installed: {missing}")

    def test_no_broken_links(self):
        broken = [p.name for p in SKILLS.iterdir() if p.is_symlink() and not p.exists()] if SKILLS.exists() else []
        self.assertEqual(broken, [])


class Media(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clip = make_clip("src.mp4")

    def test_probe(self):
        j = json.loads(igo("probe", self.clip).stdout)
        self.assertEqual((j["video"]["w"], j["video"]["h"]), (1280, 720))
        self.assertAlmostEqual(j["duration"], 3, delta=0.2)

    def test_project_scaffold_and_no_overwrite(self):
        igo("new", "p1", "--root", TMP / "projects")
        self.assertTrue((TMP / "projects/p1/exports").is_dir())
        self.assertNotEqual(igo("new", "p1", "--root", TMP / "projects", ok=False).returncode, 0)

    def test_export_all_platforms_and_qc(self):
        igo("new", "p2", "--root", TMP / "projects")
        proj = TMP / "projects/p2"
        for plat in ("youtube", "shorts", "reels", "ig45", "linkedin", "linkedin45", "corporate"):
            out = igo("export", self.clip, "--platform", plat, "--project", proj, "--normalize", "--fit", "blur" if plat in ("shorts", "reels") else "pad").stdout.strip()
            r = igo("qc", out, "--platform", plat, "--project", proj, ok=False)
            self.assertIn("VERDICT", r.stdout)
            self.assertNotIn("FAIL  resolution", r.stdout, f"{plat}\n{r.stdout}")
            self.assertNotIn("FAIL  frame rate", r.stdout, plat)
            self.assertNotEqual(r.returncode, 1, f"{plat} FAILED QC\n{r.stdout}")
        self.assertTrue(list((proj / "reports").glob("qc-*.json")))
        self.assertTrue((proj / "logs/studio.log").exists())

    def test_source_never_overwritten(self):
        before = self.clip.read_bytes()
        r = igo("export", self.clip, "--platform", "youtube", "--out", self.clip.parent, ok=False)
        igo("proxy", self.clip, "--out", TMP / "px")
        self.assertEqual(before, self.clip.read_bytes())

    def test_qc_detects_problems(self):
        black = make_clip("black.mp4", black=True)
        self.assertIn("WARN  black frames", igo("qc", black, ok=False).stdout)
        hot = make_clip("hot.mp4", vol=30)
        self.assertIn("FAIL  audio clipping", igo("qc", hot, ok=False).stdout)
        silent = make_clip("silent.mp4", audio=False)
        self.assertIn("FAIL  audio", igo("qc", silent, ok=False).stdout)
        self.assertIn("FAIL  resolution", igo("qc", self.clip, "--platform", "shorts", ok=False).stdout)

    def test_subtitle_timing_checks(self):
        good, bad = TMP / "g.srt", TMP / "b.srt"
        good.write_text("1\n00:00:00,500 --> 00:00:01,500\nhello\n\n2\n00:00:01,600 --> 00:00:02,500\nworld\n")
        bad.write_text("1\n00:00:00,500 --> 00:00:02,000\nhello\n\n2\n00:00:01,000 --> 00:00:02,500\nworld\n")
        self.assertIn("PASS  subtitles", igo("qc", self.clip, "--srt", good, ok=False).stdout)
        self.assertIn("FAIL  subtitles", igo("qc", self.clip, "--srt", bad, ok=False).stdout)

    def test_loudnorm(self):
        out = TMP / "norm.m4a"
        igo("loudnorm", self.clip, out, "--lufs", "-16")
        r = subprocess.run(["ffmpeg", "-i", out, "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
        import re
        lu = float(re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', r.stderr).group(1))
        self.assertAlmostEqual(lu, -16, delta=1.5)

    def test_mix_ducking(self):
        ff("-f", "lavfi", "-i", "sine=f=200:d=4", "-c:a", "aac", TMP / "voice.m4a")
        ff("-f", "lavfi", "-i", "sine=f=800:d=2", "-c:a", "aac", TMP / "music.m4a")
        igo("mix", TMP / "voice.m4a", TMP / "music.m4a", TMP / "mixed.m4a")
        self.assertAlmostEqual(json.loads(igo("probe", TMP / "mixed.m4a").stdout)["duration"], 4, delta=0.3)

    def test_frames(self):
        out = igo("frames", self.clip, "--count", "3", "--out", TMP / "fr").stdout.split()
        self.assertEqual(len(out), 3)
        self.assertTrue(all(Path(p).stat().st_size > 1000 for p in out))


class Brand(unittest.TestCase):
    def test_logo_lock_and_watermark(self):
        igo("brand", "new", "acme")
        logo = TMP / "brands/acme/assets/logo.png"
        self.assertNotEqual(igo("brand", "lock", "acme", ok=False).returncode, 0, "must refuse without a real logo")
        ff("-f", "lavfi", "-i", "color=c=red:s=200x100", "-frames:v", "1", logo)
        igo("brand", "lock", "acme")
        self.assertEqual(igo("brand", "check", "acme").returncode, 0)
        clip = make_clip("wm_src.mp4")
        igo("brand", "watermark", "acme", "--input", clip, "--out", TMP / "wm.mp4")
        self.assertTrue((TMP / "wm.mp4").exists())
        ff("-f", "lavfi", "-i", "color=c=blue:s=200x100", "-frames:v", "1", logo)  # tamper
        self.assertNotEqual(igo("brand", "check", "acme", ok=False).returncode, 0)
        self.assertNotEqual(igo("brand", "watermark", "acme", "--input", clip, "--out", TMP / "wm2.mp4", ok=False).returncode, 0)


def _whisper():
    t = Path(os.environ.get("VIDEO_TOOLS", "/Volumes/Disk 1 SSD/claude-video-tools"))
    return any((t / "whisper-venv" / d / n).exists() for d, n in (("bin", "whisper"), ("Scripts", "whisper.exe")))


@unittest.skipUnless(_whisper(), "needs the Whisper venv (install-all.sh)")
class Transcription(unittest.TestCase):
    def test_whisper_srt_roundtrip(self):
        wav = TMP / "speech.wav"
        r = igo("tts", "Agriculture feeds the nation. Healthy soil grows strong crops.", wav, ok=False)
        if r.returncode:
            self.skipTest("no OS speech engine")
        srt = igo("subs", wav, "--model", "tiny", "--lang", "en", "--out", TMP / "subs").stdout.strip().splitlines()[-1]
        text = Path(srt).read_text().lower()
        self.assertTrue("soil" in text or "agriculture" in text, text)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
