# Architecture

```
User request ──► igo-director (sizes job, creative pack, picks engines)
                    │
        ┌───────────┼──────────────────────────────┐
        ▼           ▼                              ▼
 video-studio hub   igo CLI (studio/igo.py)        Engines
 (skill routing,    hw · new · proxy · export ·    FFmpeg · Remotion (templates/remotion-promo)
  catalog.json,     qc · frames · loudnorm · mix · HyperFrames · Three.js · ghost-editor · shorts
  pipelines)        subs · brand                   motionclone · Whisper · (Blender optional)
                    │
                    ▼
        projects/<name>/{brief,scripts,storyboards,footage,audio,images,graphics,subtitles,previews,renders,exports,reports,logs}
                    │  QC reports (JSON) ─► dashboard (localhost:8792)
```

Design rules: modular (each command independent, stdlib only); source media read-only; reproducible (project.json, logs/studio.log records every ffmpeg call, props JSON drives Remotion); optional external services; presets in one JSON; each tool isolated in its own venv; safe installer (links never overwrite, uninstall removes only what it created).

Add a platform: add an entry to `studio/presets.json`. Add a Remotion scene type: extend `templates/remotion-promo/src/Promo.tsx`. Add a skill to the hub: add it to `skills/video-studio/catalog.json` (the test suite fails if a catalog skill is not installed).
