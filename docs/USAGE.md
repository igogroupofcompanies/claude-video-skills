# Usage guide

Restart Claude Code after install. Then describe the video in plain words: `igo-director` plans and produces it, and the `video-studio` hub routes to the right skills. You can also name a skill directly ("use ghost-editor").

## Ask for a video

| You say | What happens |
|---|---|
| "Create a premium 60-second promotional film for IGO Group." | director: brief, script, Remotion scenes, music and voice mix, exports, QC |
| "Edit ~/Movies/take.mov into a reel in Clean OS." | `ghost-editor` |
| "Make 5 shorts from podcast.mp4 for TikTok and Reels." | `shorts` skill, then platform exports |
| "Trim intro.mp4 to 0:05–0:40, normalize loudness, export 1080x1920." | `ffmpeg-skill` and `igo export` |
| "LinkedIn video with animated statistics from sales.csv." | Remotion `stats` scenes, `linkedin` or `linkedin45` preset |
| "Build a 3D lyric video for song.mp3, 4K." | Remotion + Three.js, lyrics timed from the audio |
| "Make my cards animate like https://example.com and verify it." | `motionclone` |
| "Make a transparent lower third for OBS." | `lower-thirds` |
| "Download this video at 360p for study: URL." | `yt-dlp` |

## Pick an engine

- **Footage in hand:** `ffmpeg-skill` (any file), `ghost-editor` (talking-head reels), `shorts` (long to short).
- **Building from nothing:** HyperFrames (HTML scenes, quick edits) or Remotion (React, data, 3D).
- **3D:** Remotion with the `threejs-*` skills. Blender is optional.
- **Exact motion copy:** `motionclone`.

### HyperFrames vs Remotion

- **HyperFrames:** HTML + GSAP timeline to MP4. Fast to write, editable in its desktop app, about 450 ready blocks.
- **Remotion:** React components to MP4. Best for data-driven batches, reusable components, 3D, and captions.
- Both: audio is the clock, frame-driven animation only, verify before delivery.

## The `igo` CLI

```bash
python3 studio/igo.py hw                                   # machine and recommendations
python3 studio/igo.py new my-film --brand igo --platform youtube --style cinematic
python3 studio/igo.py export master.mp4 --platform reels --fit blur --normalize --project projects/my-film
python3 studio/igo.py qc exports/master_reels.mp4 --platform reels --project projects/my-film
python3 studio/igo.py frames exports/master_reels.mp4 --count 6   # then look at them
python3 studio/igo.py subs interview.mp4 --model base --lang en
python3 studio/igo.py mix voice.m4a music.m4a mixed.m4a           # music ducks under the voice
```

Platform presets: `youtube`, `youtube4k`, `shorts`, `reels`, `ig45`, `linkedin`, `linkedin45`, `corporate`.

## Quality control

Every export is checked for resolution, frame rate, codec, bitrate, audio and video length sync, clipping, loudness, black frames, frozen frames, subtitle timing, missing assets and decode errors. A pass is **technical**: visual quality counts as checked only after the extracted frames have been looked at.

## Keys and one-time setup

- `GEMINI_API_KEY` in `<tools>/ghost-editor/.env` enables Ghost Editor's B-roll check.
- `ELEVENLABS_API_KEY` is optional, for narration.
- Paid generation (HeyGen, ElevenLabs, image or video models) always needs your approval first.

## Troubleshooting

- **Skill not showing:** restart Claude Code, run `bash doctor.sh`.
- **Two skills with the same name:** `lower-thirds` / `lower-thirds-tiktok`, `threejs-animation` / `threejs-animation-iart`. Both are useful.
- **ASS caption burn-in fails:** the Homebrew ffmpeg has no libass; text goes through Remotion instead.
- **4K render slow:** run it in the background and lower `--concurrency` if the Mac is busy.

## Dashboard shortcuts

`1`–`4` switch sections · `/` search skills · `r` refresh · click a skill card to copy its name.
