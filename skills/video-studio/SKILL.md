---
name: video-studio
description: Hub for all installed video, motion and animation skills. Use FIRST whenever the user wants to make, edit, animate, caption, clip, convert, clone or deliver any video, reel, short, lyric video, motion graphic, 3D scene or animated UI. Routes the request to the right skills, chains them into a pipeline, and says which tool to run. Triggers include "make a video", "edit this footage", "reel", "shorts", "lyric video", "captions", "animate", "clone this animation", "render", "export for YouTube/TikTok/Instagram".
---

# video-studio: the hub

You have ~90 video skills installed. Do not guess among them. Follow this file: pick the **engine**, then the **craft skills**, then the **delivery skill**, and chain them.

## Step 1. Classify the request

| The user has / wants | Engine (does the work) | Read first |
|---|---|---|
| A raw talking-head phone recording → finished reel | `ghost-editor` | its SKILL.md; then `video-delivery-specs` |
| A long video → several short clips with captions | `shorts` | then `caption-animation`, `video-delivery-specs` |
| Any existing file: trim, join, resize, reframe, speed, audio fix, loudness, subtitles burn-in, convert, export | `ffmpeg-skill` | always probe first, verify last |
| A video made from code/HTML (titles, explainers, charts, overlays, music videos) | **HyperFrames**: `hyperframes` → `hyperframes-registry` → `media-use` → `hyperframes-cli` &nbsp;or&nbsp; **Remotion**: `remotion-best-practices` → `remotion-create` → `remotion-markup` → `remotion-studio` → `remotion-render` | `references/pipelines.md` §4 |
| 3D scenes, 3D text, particles, shaders in a video | Remotion (`remotion-best-practices`) + `threejs-*` via @remotion/three | `threejs-fundamentals`, `threejs-geometry`, `threejs-materials`, `threejs-lighting` |
| Copy an existing web animation / prove a rebuild matches | `motionclone` (CLI or MCP) | `references/pipelines.md` §Clone |
| Transparent overlays (lower thirds, bugs, stingers) | `lower-thirds` | `kinetic-typography` |
| Rebuild an existing video as editable code | `reverse-any-video` (HyperFrames) | |
| Port Remotion/Lottie/p5 work into HyperFrames | `remotion-to-hyperframes` | |
| Download a reference video / audio | `yt-dlp` (CLI) | then `ffmpeg-skill probe` |
| Transcribe / word timings | Whisper CLI in `whisper-venv` | feeds `caption-animation` |
| Business side of a motion job | `creative-brief`, `motion-pricing`, `client-revisions`, `brand-motion-guidelines` | |

## Step 2. Add craft skills by what the picture needs

- **Motion quality:** `animation-principles` (timing/easing), `motion-art-direction` (tone, restraint), `shot-composition` (frame, safe areas), `color-motion` (palettes, grading), `60fps-animation`, `accessible-animation`.
- **Text:** `kinetic-typography`, `caption-animation`, `logo-animation`, `svg-animation`.
- **Data and diagrams:** `chart-animation`, `diagram-animation`, `animated-infographic`, `map-animation`, `manim` (math).
- **Backgrounds and FX:** `motion-background`, `particle-system`, `shader-glsl`, `glassmorphism`, `isometric-animation`, `ascii-animation`, `lottie-animation`, `generative-illustration`, `javascript-animation`, `whiteboard-animation`.
- **Sound and rhythm:** `soundtrack`, `beat-sync-editing`, `audiogram`.
- **Format templates:** `launch-video`, `promo-video`, `ad-creative-video`, `product-demo-video`, `explainer-video`, `presentation-video`, `testimonial-video`, `text-message-animation`, `short-form-video`, `youtube-intro-outro`, `wrapped-video`, `photo-slideshow`, `countdown-video`, `talking-head`, `talking-head-b-roll`.
- **Always last:** `video-delivery-specs` (platform specs) then `ffmpeg-skill` check/loudness/export.

Full catalog with "use when" and "pairs with": `references/catalog.md`.

## Step 3. Run the standard loop

1. **Brief**: purpose, platform, length, aspect, language, music, brand. Missing → ask one round (`creative-brief`).
2. **Probe inputs**: `ffmpeg-skill` probe.py (duration, fps, audio). Never trust a filename.
3. **Master timeline**: if there is audio, the audio is the clock. Take timings from it (Whisper word times; for sung lyrics separate vocals first, see pipelines §Lyrics). Never invent timings.
4. **Build the smallest preview first** (one scene or 5 s still), look at it, then render all.
5. **Render** with the engine's own CLI. Heavy 4K renders: run in background, tell the user the ETA.
6. **Verify**: probe the output (resolution, fps, duration, audio present and same level), check for black frames, view 3 stills. Report numbers, not adjectives.
7. **Deliver** per `video-delivery-specs`; keep the source project and an SRT.

## Rules

- Do not overwrite the user's source files; write outputs to a new folder.
- Preserve the user's text exactly (lyrics, names, Tamil/Indic script). Never translate or "fix" it. Indic scripts need real shaping (HarfBuzz) when turned into 3D geometry.
- Paid generation (HeyGen, ElevenLabs, image/video models) only with the user's approval of the cost.
- Keys live in each tool's own `.env`; never print them.
- If two skills conflict, the engine's skill wins over a craft skill; the user's brief wins over both.
- Duplicate-named skills: `lower-thirds` (broadcast/WebM alpha) vs `lower-thirds-tiktok` (design guidance); `threejs-animation` (API reference) vs `threejs-animation-iart` (hero/R3F/performance recipes). Use both when building.

## Where things live

Remotion extras: `remotion-captions`, `remotion-multimedia` (Mediabunny), `remotion-maps`, `remotion-elements`, `remotion-docs`, `remotion-upgrade`, `remotion-license`, `remotion-saas`, `remotion-interactivity`. HyperFrames extras: `reverse-any-video`, `remotion-to-hyperframes`, `style-sampling`, `slideshow`, `figma`. Dashboard: `python3 <repo>/dashboard/server.py` → http://localhost:8792.

Tools folder (default `~/claude-video-tools` or the SSD): `whisper-venv/`, `media-venv/`, `shorts-venv/`, `ghost-editor/`, `ffmpeg-skill/`, `motionclone/`, `motion-packs/`, `threejs-skills/`. Health check: `bash <repo>/doctor.sh`.
