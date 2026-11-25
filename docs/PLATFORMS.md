# Platforms

| Platform | Status | Notes |
|---|---|---|
| macOS, Apple silicon | **Full, tested daily** | VideoToolbox drafts, macOS speech engine for draft narration |
| Linux (Ubuntu/Debian, x86-64 or arm64) | **Supported.** `igo` CLI and the 14 media tests pass on Ubuntu 24.04 (arm64 container). Installer result: see the section below. | needs sudo once for system packages |
| Windows 10/11 | **Use WSL2 (Ubuntu), run Claude Code inside it.** Same as Linux. Not tested on a real Windows machine. | native PowerShell is not supported by the installer |

## What differs by platform

- **Hardware encoding** (`--hw`, drafts and proxies only): VideoToolbox (Mac), NVENC / QSV / AMF (Windows/Linux GPUs). `igo` runs a one-frame test encode first and falls back to libx264, so a missing GPU never breaks an export. Final renders always use libx264.
- **Draft narration** (`igo tts`): macOS `say`, Windows speech (via PowerShell), Linux `espeak-ng`. For final audio use a real recording or an approved API.
- **Ghost Editor:** its caption check uses macOS text recognition, so that check is Mac-only. The rest works elsewhere.
- **Text on video:** Homebrew's ffmpeg has no `drawtext`; many Linux builds do. The studio renders text with Remotion on every platform, so results match.
- **Installer never runs `sudo`.** It prints the exact command for anything missing and stops.

## Linux setup (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y ffmpeg git curl rsync jq python3 python3-venv pipx espeak-ng
pipx install uv                      # then: pipx ensurepath
# Node 24+: install from https://nodejs.org or with nvm (nvm install 24)
git clone https://github.com/igogroupofcompanies/claude-video-skills && cd claude-video-skills
bash install-all.sh --check
bash install-all.sh
python3 studio/tests/test_studio.py
```
MotionClone's browser may need system libraries: `sudo npx playwright install-deps chromium`.

## Windows setup (WSL2)

1. In PowerShell as administrator: `wsl --install -d Ubuntu`, then restart and create the Ubuntu user.
2. Open the Ubuntu terminal and follow the Linux steps above.
3. Install Claude Code **inside Ubuntu** so skills land in Ubuntu's `~/.claude/skills`, and keep projects under `~/` (not `/mnt/c`, which is slow).
4. Open the dashboard from Windows at http://localhost:8792 (WSL forwards the port).
5. GPU encoding in WSL needs the NVIDIA CUDA-on-WSL driver; without it everything still works on the CPU.

## Report a problem

Run `bash doctor.sh` and `python3 studio/igo.py hw` and send both outputs to the maintainer.
