#!/usr/bin/env python3
"""IGO Master Video Studio CLI: project scaffold, hardware, probe, proxy, export, QC, audio, subtitles, brand.
Stdlib only. Uses ffmpeg/ffprobe on PATH. Never writes over source media.
  python3 studio/igo.py <command> --help
"""
import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRESETS = json.loads((HERE / "presets.json").read_text())
TOOLS = next((Path(p) for p in (os.environ.get("VIDEO_TOOLS"), "/Volumes/Disk 1 SSD/claude-video-tools",
              str(Path.home() / "claude-video-tools")) if p and Path(p).is_dir()), Path.home() / "claude-video-tools")
DIRS = ["brief", "scripts", "storyboards", "footage", "audio", "images", "graphics", "subtitles",
        "previews", "renders", "exports", "reports", "logs"]


def sh(cmd, check=True, log=None):
    """Run a command, log it, return CompletedProcess (text)."""
    cmd = [str(c) for c in cmd]
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as f:
            f.write(f"[{time.strftime('%F %T')}] {' '.join(cmd)}\n")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(cmd[:4])}...\n{r.stderr[-600:]}")
    return r


WIN = platform.system() == "Windows"
HOWTO = {"Darwin": "brew install ffmpeg", "Linux": "sudo apt install ffmpeg  (or your distro's package manager)",
         "Windows": "winget install Gyan.FFmpeg  (or use WSL2, see docs/PLATFORMS.md)"}


def need(tool):
    if not shutil.which(tool):
        raise SystemExit(f"missing {tool}: {HOWTO.get(platform.system(), 'install ffmpeg')}")


def venv_bin(venv, exe):
    """Path of an executable inside a tools venv (bin/ on macOS+Linux, Scripts\\ on Windows)."""
    return TOOLS / venv / ("Scripts" if WIN else "bin") / (exe + (".exe" if WIN else ""))


def encoders():
    return sh(["ffmpeg", "-hide_banner", "-encoders"], False).stdout if shutil.which("ffmpeg") else ""


HW_ENCODERS = ["h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf", "h264_vaapi"]


_HW = {}


def hw_encoder(enc=None):
    """First hardware H.264 encoder that actually encodes a test frame on this machine, else None."""
    if "v" in _HW:
        return _HW["v"]
    enc = enc if enc is not None else encoders()
    for e in HW_ENCODERS:
        if e in enc:
            dev = ["-init_hw_device", "vaapi=va:/dev/dri/renderD128", "-vf", "format=nv12,hwupload", "-filter_hw_device", "va"] if e == "h264_vaapi" else []
            r = sh(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2", *dev, "-frames:v", "2", "-c:v", e, "-f", "null", "-"], False)
            if r.returncode == 0:
                _HW["v"] = e
                return e
    _HW["v"] = None
    return None


def hw_args(codec, bitrate):
    if codec == "h264_vaapi":  # needs a device + upload filter; use libx264 path instead of half-configuring it
        return ["-c:v", "libx264", "-preset", "veryfast", "-b:v", bitrate]
    extra = {"h264_vaapi": [], "h264_nvenc": ["-preset", "p4"], "h264_qsv": [], "h264_amf": [], "h264_videotoolbox": []}[codec]
    return ["-c:v", codec, "-b:v", bitrate, *extra]


def mem_gb():
    try:
        if platform.system() == "Darwin":
            return int(sh(["sysctl", "-n", "hw.memsize"], False).stdout.strip()) / 2**30
        if platform.system() == "Linux":
            return int(re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text()).group(1)) / 2**20
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                        ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
        ms = MS(); ms.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        return ms.tp / 2**30
    except Exception:
        return 0


def cpu_name():
    try:
        if platform.system() == "Darwin":
            return sh(["sysctl", "-n", "machdep.cpu.brand_string"], False).stdout.strip()
        if platform.system() == "Linux":
            m = re.search(r"model name\s*:\s*(.+)", Path("/proc/cpuinfo").read_text())
            return m.group(1) if m else platform.machine()
    except Exception:
        pass
    return platform.processor() or platform.machine()


def probe(path):
    need("ffprobe")
    r = sh(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    fr = lambda s: (lambda n, d: n / d if d else 0)(*map(float, s.split("/"))) if s else 0
    return {
        "file": str(path), "duration": float(j["format"].get("duration", 0)), "bytes": int(j["format"].get("size", 0)),
        "bitrate": int(j["format"].get("bit_rate", 0) or 0),
        "video": v and {"codec": v["codec_name"], "w": v["width"], "h": v["height"], "fps": round(fr(v.get("avg_frame_rate", "0/1")), 3),
                        "pix_fmt": v.get("pix_fmt"), "dur": float(v.get("duration", 0) or 0)},
        "audio": a and {"codec": a["codec_name"], "rate": int(a["sample_rate"]), "ch": a["channels"], "dur": float(a.get("duration", 0) or 0)},
    }


def project_root(args):
    p = Path(getattr(args, "project", None) or ".")
    return p if (p / "project.json").exists() else None


def logfile(args):
    p = project_root(args)
    return (p / "logs/studio.log") if p else None


# ---------------- hw
def cmd_hw(a):
    enc = encoders()
    mem = mem_gb()
    free = shutil.disk_usage(TOOLS if TOOLS.exists() else Path.home()).free / 2**30
    hwe = hw_encoder(enc)
    filt = sh(["ffmpeg", "-hide_banner", "-filters"], False).stdout if shutil.which("ffmpeg") else ""
    rec = {"os": platform.system(), "chip": cpu_name(), "cpus": os.cpu_count(), "mem_gb": round(mem), "tools_dir": str(TOOLS),
           "disk_free_gb": round(free), "hw_encoder": hwe, "videotoolbox": hwe == "h264_videotoolbox",
           "prores": "prores_ks" in enc, "libx264": "libx264" in enc, "drawtext": "drawtext" in filt,
           "recommend": {"render_concurrency": max(2, (os.cpu_count() or 4) // 2),
                         "whisper_model": "small" if mem >= 24 else "base" if mem >= 12 else "tiny",
                         "final_encoder": "libx264 (quality, deterministic)",
                         "preview_encoder": hwe or "libx264 -preset veryfast",
                         "proxy_for_inputs_over": "3840x2160 or >1GB"}}
    print(json.dumps(rec, indent=1))


# ---------------- project
def cmd_new(a):
    root = Path(a.root) / a.name
    if root.exists():
        raise SystemExit(f"{root} exists; refusing to overwrite")
    for d in DIRS:
        (root / d).mkdir(parents=True)
    cfg = {"name": a.name, "created": time.strftime("%FT%T"), "brand": a.brand, "platform": a.platform, "style": a.style,
           "assets": [], "notes": "Source media in footage/ is never modified; outputs go to renders/ and exports/."}
    (root / "project.json").write_text(json.dumps(cfg, indent=1))
    for t in sorted((HERE.parent / "templates").glob("*.md")):
        shutil.copy(t, root / "brief" / t.name)
    print(root)


# ---------------- proxy
def cmd_proxy(a):
    src = Path(a.input)
    out = Path(a.out or (project_root(a) / "previews" if project_root(a) else src.parent / "proxies")) / f"{src.stem}_proxy.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.resolve() == src.resolve():
        raise SystemExit("refusing to overwrite source")
    hwe = hw_encoder() if a.hw else None
    enc = hw_args(hwe, "4M") if hwe else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26"]
    sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", f"scale=-2:{a.height}", *enc, "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out], log=logfile(a))
    print(out)


# ---------------- export
def fit_filter(p, fit):
    w, h = p["w"], p["h"]
    if fit == "crop":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    if fit == "blur":  # blurred backdrop, sharp centered foreground (no cropping of content)
        return (f"split[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=30:5[bg];"
                f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")
    return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"


def cmd_export(a):
    need("ffmpeg")
    p = PRESETS[a.platform]
    src = Path(a.input)
    outdir = Path(a.out or (project_root(a) / "exports" if project_root(a) else src.parent / "exports"))
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{src.stem}_{a.platform}.mp4"
    if out.resolve() == src.resolve():
        raise SystemExit("refusing to overwrite source")
    af = []
    if a.normalize:
        af = ["-af", f"loudnorm=I={p['lufs']}:TP=-1.5:LRA=11"]
    hwe = hw_encoder() if a.hw else None
    if a.hw and not hwe:
        print("note: no hardware H.264 encoder in this ffmpeg; using libx264", file=sys.stderr)
    vcodec = (hw_args(hwe, p["vmax"]) if hwe else
              ["-c:v", "libx264", "-preset", a.preset, "-crf", str(p["crf"]), "-maxrate", p["vmax"], "-bufsize", str(int(p["vmax"][:-1]) * 2) + "M"])
    sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", fit_filter(p, a.fit), "-r", str(p["fps"]), *vcodec, "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", p["abr"], "-ar", "48000", *af, "-movflags", "+faststart", out], log=logfile(a))
    print(out)


# ---------------- qc
def parse_srt(path):
    cues, blocks = [], re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8").strip())
    t = lambda s: sum(float(x) * m for x, m in zip(re.split("[:,]", s), (3600, 60, 1, .001)))
    for b in blocks:
        m = re.search(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", b)
        if m:
            cues.append((t(m.group(1)), t(m.group(2)), b.splitlines()[-1] if b.splitlines() else ""))
    return cues


def cmd_qc(a):
    need("ffmpeg")
    f = Path(a.input)
    checks, meta = [], probe(f)
    add = lambda name, status, detail: checks.append({"check": name, "status": status, "detail": detail})
    v, au = meta["video"], meta["audio"]
    if not f.exists() or meta["duration"] <= 0:
        add("file", "FAIL", "missing or zero duration")
    if not v:
        add("video stream", "FAIL", "none")
    else:
        add("codec", "PASS" if v["codec"] == "h264" else "WARN", f"{v['codec']} {v['pix_fmt']}")
        if a.platform:
            p = PRESETS[a.platform]
            add("resolution", "PASS" if (v["w"], v["h"]) == (p["w"], p["h"]) else "FAIL", f"{v['w']}x{v['h']} (want {p['w']}x{p['h']})")
            add("frame rate", "PASS" if abs(v["fps"] - p["fps"]) < 0.05 else "FAIL", f"{v['fps']} (want {p['fps']})")
            lim = int(p["vmax"][:-1]) * 1_000_000 * 1.25
            add("bitrate", "PASS" if meta["bitrate"] <= lim else "WARN", f"{meta['bitrate']/1e6:.1f} Mb/s (cap {p['vmax']})")
        else:
            add("resolution/fps", "PASS", f"{v['w']}x{v['h']} @ {v['fps']}")
    if a.expect_duration:
        add("duration", "PASS" if abs(meta["duration"] - a.expect_duration) <= 0.5 else "FAIL", f"{meta['duration']:.2f}s (want {a.expect_duration}s)")
    else:
        add("duration", "PASS", f"{meta['duration']:.2f}s")
    if not au:
        add("audio", "FAIL" if not a.silent_ok else "WARN", "no audio stream")
    else:
        d = abs((v or {}).get("dur", 0) - au["dur"]) if v else 0
        add("a/v sync (stream length)", "PASS" if d < 0.15 else "WARN", f"video-audio length diff {d*1000:.0f} ms")
        r = sh(["ffmpeg", "-v", "info", "-i", f, "-vn", "-af", "astats=metadata=0,loudnorm=print_format=json", "-f", "null", "-"], False)
        pk = re.findall(r"Peak level dB:\s*(-?[\d.inf]+)", r.stderr)
        peak = max((float(x) for x in pk if x not in ("-inf",)), default=-99)
        add("audio clipping", "PASS" if peak < -0.1 else "FAIL", f"peak {peak:.1f} dBFS")
        m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+)"', r.stderr)
        if m:
            lu = float(m.group(1))
            tgt = PRESETS[a.platform]["lufs"] if a.platform else None
            add("loudness", "PASS" if tgt is None or abs(lu - tgt) <= 2.5 else "WARN", f"{lu:.1f} LUFS" + (f" (target {tgt})" if tgt is not None else ""))
    if v:
        r = sh(["ffmpeg", "-v", "info", "-i", f, "-vf", "blackdetect=d=0.4:pix_th=0.10", "-an", "-f", "null", "-"], False)
        bl = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
        add("black frames", "PASS" if not bl else "WARN", "none" if not bl else "; ".join(f"{s}-{e}s" for s, e in bl[:5]))
        r = sh(["ffmpeg", "-v", "info", "-i", f, "-vf", "freezedetect=n=-60dB:d=2.5", "-an", "-f", "null", "-"], False)
        fz = re.findall(r"freeze_start: ([\d.]+)", r.stderr)
        add("frozen frames", "PASS" if not fz else "WARN", "none" if not fz else f"freeze starts at {', '.join(fz[:5])}s (ok for intentional holds)")
    if a.srt:
        try:
            cues = parse_srt(a.srt)
            bad = [i for i, (s, e, _) in enumerate(cues, 1) if e <= s or s < 0 or e > meta["duration"] + 0.5]
            ov = [i for i, (x, y) in enumerate(zip(cues, cues[1:]), 1) if y[0] < x[1] - 1e-3]
            add("subtitles", "PASS" if cues and not bad and not ov else "FAIL",
                f"{len(cues)} cues; bad timing {bad[:5]}; overlaps {ov[:5]}")
        except (OSError, ValueError) as e:
            add("subtitles", "FAIL", str(e))
    pr = project_root(a)
    if pr:
        miss = [x for x in json.loads((pr / "project.json").read_text()).get("assets", []) if not (pr / x).exists()]
        add("assets", "PASS" if not miss else "FAIL", "all present" if not miss else f"missing: {miss[:5]}")
    r = sh(["ffmpeg", "-v", "error", "-i", f, "-f", "null", "-"], False)
    add("decode errors", "PASS" if not r.stderr.strip() else "FAIL", r.stderr.strip()[:120] or "clean decode")
    verdict = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "WARN" if any(c["status"] == "WARN" for c in checks) else "PASS"
    rep = {"file": str(f), "verdict": verdict, "meta": meta, "checks": checks, "time": time.strftime("%FT%T"),
           "note": "Technical validation only. Visual quality is NOT verified until frames are inspected (use `igo frames`)."}
    outdir = Path(a.report or (pr / "reports" if pr else f.parent))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"qc-{f.stem}.json").write_text(json.dumps(rep, indent=1))
    for c in checks:
        print(f"  {c['status']:4}  {c['check']:26} {c['detail']}")
    print(f"VERDICT: {verdict}  (report: {outdir / ('qc-' + f.stem + '.json')})")
    sys.exit(1 if verdict == "FAIL" else 0)


def cmd_frames(a):
    """Extract representative frames (evenly spaced) so they can be looked at."""
    f = Path(a.input)
    d = probe(f)["duration"]
    out = Path(a.out or (project_root(a) / "previews" if project_root(a) else f.parent / "frames"))
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(a.count):
        t = d * (i + 0.5) / a.count
        o = out / f"{f.stem}_f{i+1:02d}_{t:05.1f}s.jpg"
        sh(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", f, "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "3", o])
        paths.append(str(o))
    print("\n".join(paths))


# ---------------- audio
def cmd_loudnorm(a):
    p = PRESETS.get(a.platform or "", {})
    target = a.lufs if a.lufs is not None else p.get("lufs", -14)
    r = sh(["ffmpeg", "-hide_banner", "-i", a.input, "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], False)
    m = json.loads(re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S).group(0))
    flt = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    out = Path(a.out)
    if out.resolve() == Path(a.input).resolve():
        raise SystemExit("refusing to overwrite source")
    vid = ["-c:v", "copy"] if Path(a.input).suffix.lower() in (".mp4", ".mov", ".mkv") else ["-vn"]
    sh(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-af", flt, *vid, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out])
    print(f"{out}  ({m['input_i']} LUFS -> {target})")


def cmd_mix(a):
    """Voice over music with ducking: music drops when the voice speaks. Output = single audio file."""
    flt = (f"[1:a]volume={a.music_db}dB[m];[0:a]asplit=2[v][vs];[m][vs]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[d];"
           "[v][d]amix=inputs=2:duration=first:normalize=0[o]")
    out = Path(a.out)
    sh(["ffmpeg", "-y", "-v", "error", "-i", a.voice, "-stream_loop", "-1", "-i", a.music, "-filter_complex", flt, "-map", "[o]",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out])
    print(out)


# ---------------- subtitles
def cmd_subs(a):
    wh = venv_bin("whisper-venv", "whisper")
    if not wh.exists():
        raise SystemExit(f"whisper not found at {wh}; run install-all.sh")
    src = Path(a.input)
    out = Path(a.out or (project_root(a) / "subtitles" if project_root(a) else src.parent))
    out.mkdir(parents=True, exist_ok=True)
    cmd = [wh, src, "--model", a.model, "--output_format", "srt", "--output_dir", out, "--fp16", "False", "--verbose", "False"]
    if a.lang:
        cmd += ["--language", a.lang]
    if a.task == "translate":
        cmd += ["--task", "translate"]
    sh(cmd, log=logfile(a))
    print(out / f"{src.stem}.srt")


# ---------------- tts (draft narration only)
def cmd_tts(a):
    """Draft voice-over from the OS speech engine. Use a real recording or an approved API for final audio."""
    out = Path(a.out)
    tmp = out.with_suffix(".tmp.wav")
    sysname = platform.system()
    if sysname == "Darwin" and shutil.which("say"):
        aiff = out.with_suffix(".tmp.aiff")
        sh(["say", "-v", a.voice or "Samantha", "-r", str(a.rate), "-o", aiff, a.text])
        sh(["ffmpeg", "-y", "-v", "error", "-i", aiff, "-ar", "48000", "-ac", "1", out]); aiff.unlink()
    elif sysname == "Windows":
        ps = ("Add-Type -AssemblyName System.Speech;$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
              f"$s.SetOutputToWaveFile('{tmp}');$s.Speak('{a.text.replace(chr(39), chr(39) * 2)}');$s.Dispose()")
        sh(["powershell", "-NoProfile", "-Command", ps])
        sh(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-ar", "48000", "-ac", "1", out]); tmp.unlink()
    else:
        eng = shutil.which("espeak-ng") or shutil.which("espeak")
        if not eng:
            raise SystemExit("no speech engine: install espeak-ng (Linux), or supply a recorded voice-over")
        sh([eng, "-w", tmp, a.text])
        sh(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-ar", "48000", "-ac", "1", out]); tmp.unlink()
    print(out)


# ---------------- brand
def brand_dir(name):
    return Path(os.environ.get("IGO_BRANDS", HERE.parent / "brands")) / name


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmd_brand(a):
    d = brand_dir(a.name)
    if a.action == "new":
        if d.exists():
            raise SystemExit(f"{d} exists")
        (d / "assets").mkdir(parents=True)
        (d / "brand.json").write_text(json.dumps({
            "name": a.name, "colors": {"primary": "#0B5D3B", "secondary": "#E8C77A", "ink": "#101820", "paper": "#FFFFFF"},
            "fonts": {"heading": "Inter", "body": "Inter"}, "logo": "assets/logo.png", "logo_sha256": None,
            "watermark": {"file": "assets/logo.png", "position": "bottom-right", "scale": 0.12, "opacity": 0.8, "margin": 40},
            "intro": None, "outro": None,
            "motion": {"ease": "cubic-bezier(.2,.8,.2,1)", "enter_ms": 500, "hold_title_s": 2.5, "rules": ["Logo is never stretched, recolored or animated except fade/slide"]},
            "rules": ["Use only the supplied logo file. Never recreate or redraw the logo."]}, indent=1))
        print(f"{d}\nPut your REAL logo at {d}/assets/logo.png (or .svg), then: igo brand lock {a.name}")
    cfg = json.loads((d / "brand.json").read_text()) if (d / "brand.json").exists() else None
    if a.action in ("lock", "check"):
        if not cfg:
            raise SystemExit("unknown brand")
        logo = d / cfg["logo"]
        if not logo.exists():
            raise SystemExit(f"LOGO MISSING: {logo}. Supply the official file; it will not be invented.")
        if a.action == "lock":
            cfg["logo_sha256"] = sha(logo)
            (d / "brand.json").write_text(json.dumps(cfg, indent=1))
            print("locked", cfg["logo_sha256"][:12])
        else:
            ok = cfg.get("logo_sha256") == sha(logo)
            print("logo", "OK (unchanged)" if ok else "CHANGED or not locked")
            sys.exit(0 if ok else 1)
    if a.action == "watermark":
        logo = d / cfg["logo"]
        if cfg.get("logo_sha256") and cfg["logo_sha256"] != sha(logo):
            raise SystemExit("logo changed since lock; refusing")
        wm, v = cfg["watermark"], probe(a.input)["video"]
        pos = {"bottom-right": "W-w-{m}:H-h-{m}", "bottom-left": "{m}:H-h-{m}", "top-right": "W-w-{m}:{m}", "top-left": "{m}:{m}"}[wm["position"]].format(m=wm["margin"])
        lw = int(v["w"] * wm["scale"])
        flt = f"[1:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={wm['opacity']}[l];[0:v][l]overlay={pos}"
        sh(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-i", logo, "-filter_complex", flt, "-c:v", "libx264", "-crf", "17", "-c:a", "copy", a.out])
        print(a.out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    pr = argparse.ArgumentParser(add_help=False)
    pr.add_argument("--project", help="project directory (enables logging/report paths)")
    s = sp.add_parser("hw", help="detect hardware + recommendations"); s.set_defaults(f=cmd_hw)
    s = sp.add_parser("new", help="scaffold a project"); s.add_argument("name"); s.add_argument("--root", default="projects")
    s.add_argument("--brand"); s.add_argument("--platform", default="youtube", choices=PRESETS); s.add_argument("--style", default="corporate"); s.set_defaults(f=cmd_new)
    s = sp.add_parser("probe", help="media info as JSON"); s.add_argument("input"); s.set_defaults(f=lambda a: print(json.dumps(probe(a.input), indent=1)))
    s = sp.add_parser("proxy", parents=[pr], help="make an editing proxy"); s.add_argument("input"); s.add_argument("--height", type=int, default=540)
    s.add_argument("--out"); s.add_argument("--hw", action="store_true"); s.set_defaults(f=cmd_proxy)
    s = sp.add_parser("export", parents=[pr], help="platform export"); s.add_argument("input"); s.add_argument("--platform", required=True, choices=PRESETS)
    s.add_argument("--fit", choices=["pad", "crop", "blur"], default="pad"); s.add_argument("--normalize", action="store_true")
    s.add_argument("--hw", action="store_true", help="hardware H.264 encoder if available (VideoToolbox/NVENC/QSV/AMF/VAAPI), for drafts"); s.add_argument("--preset", default="medium"); s.add_argument("--out"); s.set_defaults(f=cmd_export)
    s = sp.add_parser("qc", parents=[pr], help="technical validation"); s.add_argument("input"); s.add_argument("--platform", choices=PRESETS)
    s.add_argument("--srt"); s.add_argument("--expect-duration", type=float); s.add_argument("--silent-ok", action="store_true"); s.add_argument("--report"); s.set_defaults(f=cmd_qc)
    s = sp.add_parser("frames", parents=[pr], help="extract frames to inspect"); s.add_argument("input"); s.add_argument("--count", type=int, default=6); s.add_argument("--out"); s.set_defaults(f=cmd_frames)
    s = sp.add_parser("loudnorm", help="two-pass loudness normalization"); s.add_argument("input"); s.add_argument("out"); s.add_argument("--platform", choices=PRESETS); s.add_argument("--lufs", type=float); s.set_defaults(f=cmd_loudnorm)
    s = sp.add_parser("mix", help="voice + music with ducking"); s.add_argument("voice"); s.add_argument("music"); s.add_argument("out"); s.add_argument("--music-db", type=float, default=-14); s.set_defaults(f=cmd_mix)
    s = sp.add_parser("subs", parents=[pr], help="Whisper to SRT"); s.add_argument("input"); s.add_argument("--model", default="base"); s.add_argument("--lang")
    s.add_argument("--task", choices=["transcribe", "translate"], default="transcribe"); s.add_argument("--out"); s.set_defaults(f=cmd_subs)
    s = sp.add_parser("tts", help="draft narration via the OS speech engine"); s.add_argument("text"); s.add_argument("out")
    s.add_argument("--voice"); s.add_argument("--rate", type=int, default=165); s.set_defaults(f=cmd_tts)
    s = sp.add_parser("brand", help="brand kit: new | lock | check | watermark"); s.add_argument("action", choices=["new", "lock", "check", "watermark"])
    s.add_argument("name"); s.add_argument("--input"); s.add_argument("--out"); s.set_defaults(f=cmd_brand)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
