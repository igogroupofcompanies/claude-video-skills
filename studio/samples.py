#!/usr/bin/env python3
"""Builds the three sample projects end to end (real renders), then runs QC on every export.
Content is PLACEHOLDER: generated imagery, synthetic music, OS speech-engine narration, text wordmark (no logo supplied).
  python3 studio/samples.py [corporate|agri|social|all]
"""
import json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
IGO = [sys.executable, str(REPO / "studio/igo.py")]
TPL = REPO / "templates/remotion-promo"
ROOT = REPO / "projects"
W = "Placeholder content: generated visuals and synthetic audio, not real footage."


def run(*c, cwd=None, env=None):
    r = subprocess.run([str(x) for x in c], cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})
    if r.returncode:
        sys.exit(f"FAILED: {' '.join(map(str, c))[:200]}\n{r.stderr[-800:]}{r.stdout[-400:]}")
    return r.stdout


def igo(*a):
    return run(*IGO, *a)


def project(name, **kw):
    p = ROOT / name
    if not p.exists():
        extra = sum(([f"--{k}", v] for k, v in kw.items()), [])
        igo("new", name, "--root", ROOT, *extra)
    return p


def remotion(proj, props, out, comp="Promo"):
    pf = proj / "graphics/props.json"
    pf.write_text(json.dumps(props, indent=1))
    run("npx", "remotion", "render", "src/index.ts", comp, out, f"--props={pf}", "--gl=angle", "--crf=16", "--codec=h264", cwd=TPL,
        env={"npm_config_cache": os.environ.get("npm_config_cache", "")})


def pad_music(out, dur, base=110):
    """Synthetic ambient pad (A minor-ish chord) with slow tremolo, fade in/out."""
    fr = [base, base * 1.5, base * 1.8, base * 2.25]
    ins = sum((["-f", "lavfi", "-i", f"sine=f={f}:d={dur}"] for f in fr), [])
    flt = "".join(f"[{i}:a]volume=0.25[a{i}];" for i in range(4)) + "".join(f"[a{i}]" for i in range(4)) + \
          f"amix=inputs=4:normalize=0,tremolo=f=0.25:d=0.4,lowpass=f=900,afade=t=in:d=2,afade=t=out:st={dur-2}:d=2"
    run("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", flt, "-c:a", "aac", out)


def say(text, out, voice=None, rate=165):
    """Draft narration through the OS speech engine (igo tts); output converted to AAC."""
    wav = Path(str(out) + ".wav")
    igo("tts", text, wav, *(["--voice", voice] if voice and sys.platform == "darwin" else []), "--rate", rate)
    run("ffmpeg", "-y", "-v", "error", "-i", wav, "-c:a", "aac", "-b:a", "192k", out)
    wav.unlink()


def dur(f):
    return float(json.loads(igo("probe", f))["duration"])


def finish(proj, video, audio, name, platforms, srt=None, fit="pad"):
    master = proj / "renders" / f"{name}_master.mp4"
    run("ffmpeg", "-y", "-v", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", master)
    for plat in platforms:
        out = igo("export", master, "--platform", plat, "--project", proj, "--normalize", "--fit", fit).strip()
        args = ["qc", out, "--platform", plat, "--project", proj] + (["--srt", srt] if srt else [])
        r = subprocess.run([*IGO, *args], capture_output=True, text=True)
        print(f"[{name}/{plat}]\n{r.stdout}")
        if r.returncode:
            sys.exit(f"QC FAILED for {out}")


def corporate():
    p = project("corporate-promo", platform="linkedin", style="corporate")
    brand = {"primary": "#0B5D3B", "secondary": "#E8C77A", "ink": "#08140E", "paper": "#FFFFFF", "wordmark": "IGO GROUP"}
    props = {"width": 1920, "height": 1080, "fps": 30, "sceneSeconds": 3.5, "brand": brand, "scenes": [
        {"type": "title", "text": "Growing together, from the ground up", "sub": "Corporate promotional film (sample)"},
        {"type": "stats", "heading": "Sample figures, replace with approved data", "items": [
            {"value": 25, "suffix": "+", "label": "Years of experience"}, {"value": 12000, "suffix": "+", "label": "Farmers served"}, {"value": 8, "label": "Business verticals"}]},
        {"type": "quote", "text": "Technology and trust, delivered to every farm.", "by": "Leadership message (placeholder)"},
        {"type": "title", "text": "One group. Many ways to grow.", "sub": "Partnerships built on trust"},
        {"type": "outro", "text": "Thank you", "sub": "www.example.com"}]}
    remotion(p, props, p / "renders/silent.mp4")
    d = dur(p / "renders/silent.mp4")
    pad_music(p / "audio/music.m4a", d)
    say("Growing together, from the ground up. A sample corporate film. Technology and trust, delivered to every farm. Thank you.", p / "audio/vo.m4a")
    igo("mix", p / "audio/vo.m4a", p / "audio/music.m4a", p / "audio/mix.m4a", "--music-db", "-12")
    run("ffmpeg", "-y", "-v", "error", "-i", p / "audio/mix.m4a", "-af", f"apad=whole_dur={d}", "-t", d, "-c:a", "aac", p / "audio/mix_full.m4a")
    (p / "reports/NOTE.txt").write_text(W + " Brand: text wordmark only; no logo supplied.\n")
    finish(p, p / "renders/silent.mp4", p / "audio/mix_full.m4a", "corporate-promo", ["linkedin", "youtube", "corporate"])


def agri():
    p = project("agriculture-documentary", platform="youtube", style="cinematic")
    img = p / "images"
    skies = [("0x1b2a49", "0xf2a65a", "0x2e5339", "0x0f2418"), ("0x2c3e50", "0xf7d794", "0x3d6b3a", "0x1c3a22"),
             ("0x0f2027", "0x8fb98b", "0x356b3c", "0x143020"), ("0x3a1c71", "0xffaf7b", "0x4b7a3a", "0x1a301a")]
    for i, (a, b, c, d) in enumerate(skies):  # sky gradient over banded field rows + soft noise
        run("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"gradients=s=3840x2160:c0={a}:c1={b}:x0=0:y0=0:x1=0:y1=1300:d=1:r=1",
            "-f", "lavfi", "-i", f"gradients=s=3840x2160:c0={c}:c1={d}:x0=0:y0=1100:x1=0:y1=2160:d=1:r=1",
            "-filter_complex", "[1:v]crop=3840:1060:0:1100[g];[0:v][g]overlay=0:1100,noise=alls=10:allf=t,format=yuv420p", "-frames:v", "1", img / f"field{i}.png")
    seg, xf, n = 5.0, 1.0, 4
    ins = sum((["-loop", "1", "-t", str(seg + xf), "-i", img / f"field{i}.png"] for i in range(n)), [])
    zp = "".join(f"[{i}:v]scale=3840:2160,zoompan=z='1+0.0009*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+{i*10}':d={int((seg+xf)*30)}:s=1920x1080:fps=30,format=yuv420p[z{i}];" for i in range(n))
    xs, prev = "", "z0"
    for i in range(1, n):
        xs += f"[{prev}][z{i}]xfade=transition=fade:duration={xf}:offset={i*seg}[x{i}];"
        prev = f"x{i}"
    grade = f"[{prev}]curves=preset=increase_contrast,eq=saturation=1.12:gamma=0.95,colorbalance=rs=0.05:bs=-0.04:rh=0.04,vignette=PI/5,noise=alls=6:allf=t,crop=1920:804,pad=1920:1080:0:138:black[v]"
    run("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", zp + xs + grade, "-map", "[v]", "-t", str(n * seg), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", p / "renders/picture.mp4")
    total = dur(p / "renders/picture.mp4")
    pad_music(p / "audio/music.m4a", total, base=82)
    narr = "Before the sun is up, the fields are already awake. Healthy soil is the quiet foundation of every harvest. Farmers read the land the way others read a book. And in every season, patience is the most valuable crop."
    say(narr, p / "audio/vo.m4a", voice="Daniel", rate=140)
    igo("mix", p / "audio/vo.m4a", p / "audio/music.m4a", p / "audio/mix.m4a", "--music-db", "-10")
    run("ffmpeg", "-y", "-v", "error", "-i", p / "audio/mix.m4a", "-af", f"apad=whole_dur={total}", "-t", total, "-c:a", "aac", p / "audio/mix_full.m4a")
    srt = igo("subs", p / "audio/vo.m4a", "--project", p, "--model", "base", "--lang", "en").strip().splitlines()[-1]
    master = p / "renders/agriculture-documentary_master.mp4"
    run("ffmpeg", "-y", "-v", "error", "-i", p / "renders/picture.mp4", "-i", p / "audio/mix_full.m4a", "-i", srt, "-map", "0:v", "-map", "1:a", "-map", "2:s",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-shortest", master)
    (p / "reports/NOTE.txt").write_text(W + " Narration is the OS speech engine (draft); subtitles are Whisper output, soft track + sidecar SRT.\n")
    out = igo("export", master, "--platform", "youtube", "--project", p, "--normalize").strip()
    r = subprocess.run([*IGO, "qc", out, "--platform", "youtube", "--project", p, "--srt", srt], capture_output=True, text=True)
    print("[agriculture-documentary/youtube]\n" + r.stdout)
    if r.returncode:
        sys.exit("QC FAILED agri")


def social():
    p = project("social-stats-video", platform="reels", style="social")
    brand = {"primary": "#0B5D3B", "secondary": "#FFD166", "ink": "#06140E", "paper": "#FFFFFF", "wordmark": "IGO GROUP"}
    scenes = [{"type": "title", "text": "Did you know?", "sub": "Sample social video"},
              {"type": "stats", "heading": "Placeholder statistics", "items": [
                  {"value": 70, "suffix": "%", "label": "Of rural families depend on farming"}, {"value": 3, "suffix": "x", "label": "Yield gain with better soil care"}]},
              {"type": "quote", "text": "Small changes in the soil make big changes in the harvest."},
              {"type": "outro", "text": "Follow for more", "sub": "@yourhandle"}]
    for tag, (w, h, plat) in {"reels": (1080, 1920, "reels"), "li45": (1080, 1350, "linkedin45")}.items():
        remotion(p, {"width": w, "height": h, "fps": 30, "sceneSeconds": 3, "brand": brand, "scenes": scenes}, p / f"renders/{tag}_silent.mp4")
        d = dur(p / f"renders/{tag}_silent.mp4")
        pad_music(p / f"audio/{tag}_music.m4a", d, base=130)
        finish(p, p / f"renders/{tag}_silent.mp4", p / f"audio/{tag}_music.m4a", f"social-{tag}", [plat])
    (p / "reports/NOTE.txt").write_text(W + " Statistics are placeholders.\n")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("corporate", corporate), ("agri", agri), ("social", social)):
        if which in (name, "all"):
            fn()
    print("ALL SAMPLES BUILT AND QC-CHECKED")
