"""Central dashboard for the video toolkit. Read-only, local only.
Run:  python3 dashboard/server.py        then open http://localhost:8792
Shows: tool health (live checks), every installed skill (link status, category), docs.
"""
import glob, json, os, re, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = Path.home() / ".claude/skills"
CATALOG = json.loads((REPO / "skills/video-studio/catalog.json").read_text(encoding="utf-8"))
HOME = Path.home()
TOOLS = next((Path(p) for p in (os.environ.get("VIDEO_TOOLS"), "/Volumes/Disk 1 SSD/claude-video-tools",
              str(HOME / "claude-video-tools")) if p and Path(p).is_dir()), HOME / "claude-video-tools")
DOCS = {"audit": REPO / "docs/AUDIT.md", "director": REPO / "skills/igo-director/SKILL.md", "usage": REPO / "docs/USAGE.md", "pipelines": REPO / "skills/video-studio/references/pipelines.md",
        "hub": REPO / "skills/video-studio/SKILL.md"}
CACHE = {"t": 0, "v": None}
LOCK = threading.Lock()


def run(cmd, timeout=25):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout + r.stderr).strip().splitlines()
        return r.returncode == 0, (out[0][:90] if out else "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)[:90]


def hf_cli():
    g = sorted(glob.glob(str(HOME / ".claude/plugins/cache/hyperframes/hyperframes/*/skills/hyperframes/scripts/plugin-cli.mjs")))
    return g[-1] if g else None


def checks():
    py = lambda venv: str(TOOLS / venv / "bin/python")
    c = [
        ("yt-dlp", ["yt-dlp", "--version"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
        ("node", ["node", "-v"]),
        ("Whisper", [py("whisper-venv"), "-c", "import importlib.metadata as m;print('openai-whisper', m.version('openai-whisper'))"]),
        ("FFmpeg skill", ["python3", str(TOOLS / "ffmpeg-skill/scripts/probe.py"), "--help"]),
        ("Ghost Editor deps", [py("media-venv"), "-c", "import cv2,numpy,PIL,google.genai;print('opencv/numpy/pillow/genai ok')"]),
        ("Claude Shorts", [py("shorts-venv"), "-c", "import faster_whisper,cv2,mediapipe;print('faster-whisper/mediapipe ok')"]),
        ("MotionClone", ["motionclone", "--version"]),
    ]
    rd = Path(os.environ.get("REMOTION_DIR") or REPO / "templates/remotion-promo")
    rb = rd / "node_modules/.bin/remotion"
    c.append(("Remotion", ["sh", "-c", f"cd '{rd}' && ./node_modules/.bin/remotion versions 2>&1 | grep -m1 'On version'"] if rb.exists() else ["echo", "no project: set REMOTION_DIR=/path/to/remotion-project"]))
    h = hf_cli()
    c.append(("HyperFrames", ["node", h, "--version"] if h else ["false"]))
    return c


def status():
    with LOCK:
        if time.time() - CACHE["t"] < 30 and CACHE["v"]:
            return CACHE["v"]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda x: (x[0],) + run(x[1]), checks()))
    v = {"tools_dir": str(TOOLS), "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in res],
         "time": time.strftime("%H:%M:%S")}
    with LOCK:
        CACHE.update(t=time.time(), v=v)
    return v


def frontmatter(p):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return "", ""
    m = re.search(r"^---\s*\n(.*?)\n---", t, re.S)
    fm = m.group(1) if m else ""
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    d = re.search(r"^description:\s*(>-?\s*\n(?:[ \t]+.*\n?)+|.+)$", fm, re.M)
    desc = re.sub(r"\s+", " ", re.sub(r"^>-?", "", d.group(1))).strip() if d else ""
    return (name.group(1).strip().strip("'\"") if name else ""), desc


def skills():
    cat_of = {s: c for c, d in CATALOG.items() for s in d}
    out = []
    plug = [Path(x).parent for x in glob.glob(str(HOME / ".claude/plugins/cache/hyperframes/hyperframes/*/skills/*/SKILL.md"))]
    seen = {p.name for p in SKILLS.iterdir()}
    for p in sorted(list(SKILLS.iterdir()) + [q for q in plug if q.name not in seen]):
        sk = p / "SKILL.md"
        link = p.is_symlink()
        broken = link and not p.exists()
        name, desc = frontmatter(sk) if not broken else ("", "")
        out.append({"folder": p.name, "name": name or p.name, "desc": desc, "link": link, "broken": broken,
                    "target": os.readlink(p) if link else ("plugin" if "plugins/cache" in str(p) else ""), "category": cat_of.get(p.name, "Other"),
                    "hint": next((d[p.name] for d in CATALOG.values() if p.name in d), "")})
    names = [s["name"] for s in out]
    for s in out:
        s["dupe"] = names.count(s["name"]) > 1
    return out


def studio():
    hw = subprocess.run([sys.executable, str(REPO / "studio/igo.py"), "hw"], capture_output=True, text=True).stdout
    projs = []
    for pj in sorted((REPO / "projects").glob("*/project.json")):
        d = pj.parent
        qcs = []
        for q in sorted((d / "reports").glob("qc-*.json")):
            j = json.loads(q.read_text())
            qcs.append({"file": Path(j["file"]).name, "verdict": j["verdict"], "warn": [c["check"] for c in j["checks"] if c["status"] == "WARN"],
                        "fail": [c["check"] for c in j["checks"] if c["status"] == "FAIL"],
                        "checks": j["checks"], "meta": j.get("meta", {})})
        projs.append({"name": d.name, "style": json.loads(pj.read_text()).get("style"), "qc": qcs,
                      "exports": [{"name": e.name, "url": f"/media/{d.name}/{e.name}", "mb": round(e.stat().st_size / 1e6, 1)}
                                  for e in sorted((d / "exports").glob("*.mp4"))]})
    return {"hw": json.loads(hw or "{}"), "projects": projs}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype, code=200):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            self.send((Path(__file__).parent / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif p == "/api/status":
            self.send(json.dumps(status()), "application/json")
        elif p.startswith("/media/"):
            parts = p.split("/")
            f = (REPO / "projects" / parts[2] / "exports" / parts[3]) if len(parts) == 4 and ".." not in p else None
            if not f or f.suffix != ".mp4" or not f.is_file():
                return self.send("not found", "text/plain", 404)
            size = f.stat().st_size
            m = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
            a, b = (int(m.group(1)), int(m.group(2)) if m.group(2) else size - 1) if m else (0, size - 1)
            b = min(b, size - 1)
            with open(f, "rb") as fh:
                fh.seek(a)
                body = fh.read(b - a + 1)
            self.send_response(206 if m else 200)
            for k, v in (("Content-Type", "video/mp4"), ("Content-Length", str(len(body))), ("Accept-Ranges", "bytes"),
                         ("Content-Range", f"bytes {a}-{b}/{size}")):
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        elif p == "/api/studio":
            self.send(json.dumps(studio()), "application/json")
        elif p == "/api/skills":
            self.send(json.dumps({"skills": skills(), "categories": list(CATALOG) + ["Other"]}), "application/json")
        elif p.startswith("/api/doc/") and p[9:] in DOCS:
            self.send(DOCS[p[9:]].read_text(encoding="utf-8"), "text/plain; charset=utf-8")
        else:
            self.send("not found", "text/plain", 404)


if __name__ == "__main__":
    print("video dashboard on http://localhost:8792  (tools:", TOOLS, ")")
    ThreadingHTTPServer(("127.0.0.1", 8792), H).serve_forever()
