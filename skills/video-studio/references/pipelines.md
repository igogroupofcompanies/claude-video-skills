# Pipelines: which skills run in which order

Legend: ENGINE = does the rendering/editing. CRAFT = guidance read before building.

## 1. Talking-head recording → vertical reel
ghost-editor (ENGINE: best takes, trims, captions, SFX) → caption-animation / short-form-video (CRAFT, only if customizing) → video-delivery-specs → ffmpeg-skill (loudness -14 LUFS, export check).
Needs GEMINI_API_KEY in ghost-editor/.env for the B-roll check.

## 2. Long video → short clips
yt-dlp (if from a link) → shorts (ENGINE: transcribe, score, pick, render captions in Remotion) → caption-animation (style tweaks) → ffmpeg-skill (export per platform).

## 3. Edit an existing file (trim, resize, audio, subtitles, convert)
ffmpeg-skill only: probe → edit tool (cut, fit, silence, loudness, caption, export) → check. Add video-delivery-specs for target numbers.

## 4. Motion graphics / explainer / launch video
Brief (creative-brief) → motion-art-direction + animation-principles + shot-composition (CRAFT) → format skill (launch-video, explainer-video, promo-video…) → build in **HyperFrames** (HTML→MP4: hyperframes → hyperframes-registry blocks → media-use for music/SFX/voice → hyperframes-cli check/snapshot/render) **or Remotion** (remotion-best-practices → remotion-create → remotion-markup → remotion-studio preview → remotion-render). Pick HyperFrames for HTML/GSAP-style scenes and quick edits in its desktop app; pick Remotion for React components, data-driven batches and @remotion/three 3D.

## 5. 3D video (3D text, scenes, particles)
Remotion + @remotion/three + react-three-fiber. Read threejs-fundamentals, threejs-geometry (extruded text), threejs-materials, threejs-lighting, threejs-postprocessing; particles: particle-system; shaders: shader-glsl/threejs-shaders. Render with `npx remotion render <Comp> --gl=angle --concurrency=N --crf=14`. Drive animation from frame number only (no Date.now/Math.random; use random(seed)).

## 6. Lyric video (Tamil / Indic script, 3D or flat)
1. Audio is the master clock. Keep original audio untouched.
2. Timings from evidence: Whisper for text anchors; **demucs vocal stem** energy for when singing actually happens; snap line boundaries to breaths. Mark instrumental stretches (no text). Never invent timings.
3. Lyrics verbatim from the user's sheet. Never translate or rewrite.
4. Indic shaping: shape each line/word offline with HarfBuzz (uharfbuzz + fontTools) into SVG paths → three SVGLoader → ExtrudeGeometry. Three's built-in text cannot shape Tamil.
5. Data-driven timeline JSON (sections, cues, hidden flags) → Remotion Film component; export lyrics.srt from the same JSON.
6. Preview stills at section starts, then full 4K render in background, then verify (probe, black-frame scan, audio level equals source).
Skills: kinetic-typography, caption-animation, threejs-geometry, threejs-materials, soundtrack, beat-sync-editing, remotion-*.

## 7. Clone a web animation exactly
motionclone: `capture <url>` → `spec <dir>` → build your version → `capture` your clone → `verify <spec> <cloneDir>` → fix rows that are off → repeat → `side-by-side` / `report`. Pair with gsap-web, micro-interaction, 60fps-animation, accessible-animation.

## 8. Rebuild or port an existing video
reverse-any-video (any video → editable HyperFrames project, checked frame by frame). remotion-to-hyperframes (Remotion/Lottie/p5/Manim/AE output → HyperFrames).

## 9. Transparent overlays for OBS / Premiere
lower-thirds (+ lower-thirds-tiktok for design) → WebM alpha or ProRes 4444 → ffmpeg-skill check.

## 10. Data / chart / map / math video
chart-animation, diagram-animation, animated-infographic, map-animation, manim → build in HyperFrames or Remotion → delivery.

## 11. Slideshow / photo montage / countdown / audiogram
photo-slideshow (+ beat-sync-editing), countdown-video, audiogram, wrapped-video, youtube-intro-outro. Music: soundtrack or media-use.

## 12. Client job wrapper
creative-brief → motion-pricing → (work) → client-revisions → brand-motion-guidelines.

## Always finish with
video-delivery-specs → ffmpeg-skill: loudness, export, check. Report: resolution, fps, duration, audio present and level, file size.
