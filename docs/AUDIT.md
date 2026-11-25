# Audit: infrastructure as found (Nov 2026, Apple M4, 32 GB, macOS)

## Inventory of the 10 integrations (all kept, all working)
| # | Integration | Runtime | Size | Status |
|---|---|---|---|---|
| 1 | yt-dlp + ffmpeg 9.0.2 | brew | n/a | works; ffmpeg lacks `drawtext` and libass |
| 2 | Whisper (openai-whisper 20250625) | `whisper-venv` py3.11 | 0.8 GB | works; `medium.pt` cached, `tiny`/`base` download on first use |
| 3 | FFmpeg skill (kajisho5/ffmpeg-skill) | python stdlib | small | works |
| 4 | Ghost Editor | `media-venv` py3.11 + HyperFrames pin 0.8.159 | 0.14 GB + 130 MB library | works; needs GEMINI_API_KEY for B-roll check |
| 5 | Claude Shorts | `shorts-venv` py3.11 + Remotion project | 1.3 GB | works |
| 6 | Three.js skills | markdown | small | works (13 skills) |
| 7 | Motion skills | markdown, 19 packs | small | works (56 skills) |
| 8 | MotionClone | Node 24+, pnpm 10, Playwright Chromium | 0.6 GB | works; CLI + MCP |
| 9 | HyperFrames | plugin 0.9.69 + 9 copied skills | small | works |
| 10 | Awesome list | reference only | small | cloned |
Added in this pass: official Remotion skills (14), `video-studio` hub, `igo-director`, `igo` CLI, Remotion promo template.

## Duplicated or overlapping capability (resolved by routing, nothing removed)
| Overlap | Resolution |
|---|---|
| ghost-editor / shorts / ffmpeg-skill all cut and caption | ghost-editor = talking-head reels; shorts = long→short clips; ffmpeg-skill = any file operation |
| HyperFrames vs Remotion | HTML/GSAP + quick edits vs React + data + 3D; both documented in pipelines |
| `remotion-video` (iart) vs `remotion-best-practices` (official) | official skills are the router; iart pack kept for recipes |
| `lower-thirds` vs `lower-thirds-tiktok`, `threejs-animation` vs `threejs-animation-iart` | same frontmatter name from two packs; second linked under `-tiktok`/`-iart` folder; dashboard flags them |
| Whisper in 3 places (whisper-venv, shorts faster-whisper, ghost uses `whisper`) | kept separate (different APIs); `igo subs` uses `whisper-venv` |

## Incompatibilities and installation problems found
| Problem | Effect | Handling |
|---|---|---|
| ffmpeg has no drawtext/libass | no ffmpeg text burn-in, no ASS captions | text via Remotion; subtitles as soft `mov_text` + SRT; documented; `igo hw` reports it |
| Default `python3` is 3.15 | torch/mediapipe wheels unavailable | every tool gets its own 3.11 venv via uv |
| pnpm latest ignores `onlyBuiltDependencies` | MotionClone install aborted | pin `pnpm@10`, `CI=true` |
| Ghost Editor pins HyperFrames 0.8.159, plugin is 0.9.69 | two versions side by side | left as is (ghost's pin is deliberate for reproducible renders) |
| `~/.cache` and tools live on external SSD | installer fails if unmounted | preflight checks volume, free space (≥12 GB) |
| Duplicate skill names across packs | one shadows the other | suffix link + dashboard warning |
| No Blender, no motion tracking, no voice API configured | advanced 3D / tracking / TTS APIs unavailable | Blender via `--with-blender`; tracking not provided (see README limits); TTS optional |

## Resource profile
~4.2 GB tools + 2.2 GB caches. Whisper default `base` (32 GB RAM allows `small`; `medium` only for hard audio). Final renders libx264; VideoToolbox only for drafts and proxies.
