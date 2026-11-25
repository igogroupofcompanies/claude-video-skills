# IGO Master Video Studio

An autonomous video production system for Claude Code (macOS, Apple silicon): 10 integrations, ~100 skills, a master director, a Python CLI (`igo`) for projects/export/QC/audio/subtitles/brand, a Remotion template, a dashboard, automated tests and three rendered sample projects.

```
claude-video-skills/
  install-all.sh        installer: install | --upgrade | --check | --uninstall [--purge] | --with-blender | --validate-keys | --dry-run
  doctor.sh             health check (exit 1 on problems)
  skills/igo-director/  master director skill (plan, produce, render, inspect, repair, deliver)
  skills/video-studio/  hub skill: routes any request to the right engine/craft skills, catalog.json, pipelines
  studio/igo.py         CLI: hw new probe proxy export qc frames loudnorm mix subs brand
  studio/presets.json   platform presets (YouTube, Shorts, Reels, IG 4:5, LinkedIn 16:9/4:5, Corporate)
  studio/tests/         acceptance tests (real ffmpeg/Whisper/render)
  studio/samples.py     builds the 3 sample projects end to end
  templates/            10 creative-pack templates + remotion-promo (Remotion composition driven by JSON props)
  projects/             isolated project dirs (samples included; large media git-ignored)
  brands/               brand kits (logo locked by SHA-256)
  dashboard/            http://localhost:8792 : health, Studio & QC, skills, guides
  docs/                 USAGE.md, PLATFORMS.md, AUDIT.md, ARCHITECTURE.md
```

## Install
```bash
git clone https://github.com/igogroupofcompanies/claude-video-skills && cd claude-video-skills
bash install-all.sh --check        # diagnose first (optional)
bash install-all.sh                # install or safely upgrade; non-zero exit if any step fails
python3 studio/tests/test_studio.py
python3 dashboard/server.py        # then open http://localhost:8792
```
Requires git, Node 22+ (24+ for MotionClone), uv, 12 GB free, plus Homebrew on macOS. **Platforms:** macOS (full), Linux (supported), Windows via WSL2: see `docs/PLATFORMS.md`. Restart Claude Code afterwards. Remove everything it linked with `bash install-all.sh --uninstall` (`--purge` also deletes the tools folder).

## Use (natural language)
"Create a premium 60-second IGO Group promotional film." · "Edit this raw footage into a cinematic documentary." · "Create a LinkedIn video with animated statistics." · "Turn this interview into 10 short videos." · "Premium 3D product ad." · "Multilingual agricultural awareness video."
`igo-director` sizes the job, builds the creative pack, picks engines, renders, runs QC, **views frames**, repairs and delivers.

## CLI quick reference
```bash
python3 studio/igo.py hw                                     # chip, memory, encoders, recommendations
python3 studio/igo.py new my-film --brand igo --platform youtube --style cinematic
python3 studio/igo.py proxy footage/big.mov --height 540 --hw
python3 studio/igo.py export renders/master.mp4 --platform reels --fit blur --normalize --project projects/my-film
python3 studio/igo.py qc exports/master_reels.mp4 --platform reels --srt subs.srt --project projects/my-film
python3 studio/igo.py frames exports/master_reels.mp4 --count 6   # then LOOK at them
python3 studio/igo.py subs interview.mp4 --model base --lang en
python3 studio/igo.py loudnorm in.wav out.m4a --platform linkedin
python3 studio/igo.py mix voice.m4a music.m4a mixed.m4a --music-db -14   # ducking
python3 studio/igo.py brand new acme   # add REAL logo, then: brand lock acme | brand check acme | brand watermark acme --input in.mp4 --out out.mp4
```

## Verified vs not verified (honest status)
- Verified by running: 16 automated tests pass (media analysis, 7 platform exports, QC detecting black/clipping/silence/wrong-size/bad subtitles, loudness, ducking, Whisper round-trip, brand logo lock, skill discovery); 3 sample projects rendered and passed QC; frames of each sample were viewed.
- Samples use placeholder content (generated imagery, synthetic music, macOS `say`, text wordmark). The agriculture sample demonstrates the grade/letterbox/zoom/crossfade/VO/subtitle pipeline but its imagery is flat placeholder, not documentary quality: real footage is required for that.
- Not provided: motion tracking (no tracker integrated), Blender scenes (optional install, no workflow tested), paid voice/stock APIs (optional, not configured), `drawtext`/ASS captions (ffmpeg build lacks them; text goes through Remotion).
- QC is technical validation. Visual quality is only claimed after frames are viewed.
