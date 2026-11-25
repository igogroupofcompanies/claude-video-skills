#!/usr/bin/env bash
# IGO Master Video Studio installer (macOS, Apple silicon).
#   bash install-all.sh [options] [TOOLS_DIR]
#   (none)         install or safely upgrade everything
#   --check        run diagnostics only (no changes)
#   --upgrade      pull latest of every clone and re-run steps
#   --uninstall    remove the skill links/MCP/venv links this installer made (clones kept)
#   --purge        with --uninstall: also delete the tools folder
#   --with-blender install Blender (optional, large)
#   --validate-keys  test GEMINI_API_KEY if set (value never printed)
#   --dry-run      print what would run
# Exit code is non-zero if any step failed. Log: <TOOLS_DIR>/install.log
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE=install; BLENDER=0; KEYS=0; DRY=0; PURGE=0; B=""
for a in "$@"; do case "$a" in
  --check) MODE=check;; --upgrade) MODE=upgrade;; --uninstall) MODE=uninstall;; --purge) PURGE=1;;
  --with-blender) BLENDER=1;; --validate-keys) KEYS=1;; --dry-run) DRY=1;;
  -h|--help) sed -n 2,14p "$0"; exit 0;; -*) echo "unknown option $a"; exit 2;; *) B="$a";; esac; done
if [ -z "$B" ]; then [ -d "/Volumes/Disk 1 SSD" ] && B="/Volumes/Disk 1 SSD/claude-video-tools" || B="$HOME/claude-video-tools"; fi
S="$HOME/.claude/skills"; LOG="$B/install.log"
mkdir -p "$B/cache" "$B/motion-packs" "$S" 2>/dev/null || { echo "cannot create $B (is the volume mounted?)"; exit 1; }
export UV_CACHE_DIR="$B/cache/uv" PIP_CACHE_DIR="$B/cache/pip" npm_config_cache="$B/cache/npm" PLAYWRIGHT_BROWSERS_PATH="$B/playwright-browsers" CI=true
RESULTS=(); FAILS=0
say(){ echo "$*" | tee -a "$LOG"; }
ok(){ RESULTS+=("PASS  $1"); }
fail(){ RESULTS+=("FAIL  $1  ($2)"); FAILS=$((FAILS+1)); say "  !! $1 failed: $2 (see $LOG)"; }
run(){ if [ $DRY = 1 ]; then echo "  [dry-run] $*"; return 0; fi; echo "+ $*" >>"$LOG"; "$@" >>"$LOG" 2>&1; }
step(){ say ""; say "== $*"; }

# ---------- platform + dependency detection
OS="$(uname -s)"
pkg_hint(){ # tool -> install command for this OS
  case "$OS:$1" in
    Darwin:uv) echo "brew install uv";; Darwin:node|Darwin:npm) echo "brew install node";; Darwin:git) echo "xcode-select --install";; Darwin:brew) echo "install from https://brew.sh";;
    Darwin:*) echo "brew install $1";;
    Linux:node|Linux:npm) echo "install Node 24+ (https://nodejs.org or nvm), then re-run";;
    Linux:uv) echo "pipx install uv   (or https://docs.astral.sh/uv/getting-started/installation/)";;
    Linux:*) echo "sudo apt install -y $1   (or your distro's package manager)";;
  esac; }
preflight(){
  step "Preflight ($OS $(uname -m))"
  case "$OS" in Darwin|Linux) ;; *) say "  Unsupported shell environment ($OS). On Windows use WSL2: see docs/PLATFORMS.md"; exit 1;; esac
  [ "$OS" = Linux ] && grep -qi microsoft /proc/version 2>/dev/null && say "  running inside WSL2"
  [ "$OS" = Darwin ] && [ "$(uname -m)" != arm64 ] && say "  warn: Apple silicon expected (found $(uname -m))"
  need="git curl rsync jq node npm uv python3"; [ "$OS" = Darwin ] && need="brew $need"; [ "$OS" = Linux ] && need="$need ffmpeg"
  for t in $need; do command -v $t >/dev/null 2>&1 || { say "  MISSING $t -> $(pkg_hint $t)"; FAILS=$((FAILS+1)); }; done
  [ $FAILS -gt 0 ] && { say "Install the missing tools above (this installer never runs sudo for you) and re-run."; exit 1; }
  NV=$(node -p 'process.versions.node.split(".")[0]')
  [ "$NV" -ge 22 ] || { say "  Node $NV is too old (need 22+; MotionClone needs 24+)"; exit 1; }
  [ "$NV" -ge 24 ] || say "  warn: Node $NV works for most tools; MotionClone needs 24+"
  FREE=$(df -Pk "$B" | awk 'NR==2{print int($4/1048576)}'); say "  node v$(node -v | tr -d v), free disk ${FREE} GB at $B"
  [ "${FREE:-0}" -ge 12 ] || { say "  need at least 12 GB free"; exit 1; }
}

clone(){ # repo dir
  if [ -d "$B/$2/.git" ]; then run git -C "$B/$2" pull -q --ff-only || say "  note: $2 has local changes, not updated"
  else run git clone -q --depth 1 "https://github.com/$1.git" "$B/$2"; fi
}
link(){ local n; n=$(basename "$1")
  if [ -L "$S/$n" ]; then [ "$(readlink "$S/$n")" = "$1" ] || say "  note: $n already linked elsewhere, kept"; return 0; fi
  [ -e "$S/$n" ] && { say "  note: $n exists (not a link), kept"; return 0; }
  [ $DRY = 1 ] && { echo "  [dry-run] ln -s $1 $S/$n"; return 0; }
  ln -s "$1" "$S/$n"; echo "$S/$n" >> "$B/.links"; }

# ---------- checks
diagnose(){
  step "Diagnostics"; bash "$REPO/doctor.sh" "$B" || FAILS=$((FAILS+1))
  python3 "$REPO/studio/igo.py" hw | tr -d '\n ' | cut -c1-200; echo
  if [ $KEYS = 1 ]; then
    KEY="${GEMINI_API_KEY:-$(grep -s '^GEMINI_API_KEY=' "$B/ghost-editor/.env" | cut -d= -f2-)}"
    if [ -z "$KEY" ]; then say "  GEMINI_API_KEY: not set (Ghost Editor B-roll check disabled)"
    elif curl -sf -o /dev/null "https://generativelanguage.googleapis.com/v1beta/models?key=$KEY"; then say "  GEMINI_API_KEY: valid"
    else say "  GEMINI_API_KEY: rejected by the API"; FAILS=$((FAILS+1)); fi
    [ -n "${ELEVENLABS_API_KEY:-}" ] && say "  ELEVENLABS_API_KEY: set (not tested)" || say "  ELEVENLABS_API_KEY: not set (optional)"
  fi
}

uninstall(){
  step "Uninstall (clones kept unless --purge)"
  if [ -f "$B/.links" ]; then while read -r l; do [ -L "$l" ] && run rm "$l"; done < "$B/.links"; run rm "$B/.links"; fi
  for l in "$S/video-studio" "$S/igo-director"; do [ -L "$l" ] && run rm "$l"; done
  for l in "$HOME/.shorts-skill" "$HOME/.venvs/media"; do [ -L "$l" ] && run rm "$l"; done
  [ -d "$S/shorts" ] && run rm -r "$S/shorts"
  command -v claude >/dev/null && run claude mcp remove -s user motionclone
  command -v motionclone >/dev/null && (cd "$B/motionclone" 2>/dev/null && run npm unlink -g motionclone)
  if [ $PURGE = 1 ]; then
    case "$B" in */claude-video-tools) run rm -r "$B"; say "  purged $B";; *) say "  refusing to purge unexpected path $B";; esac
  else say "  kept $B (use --purge to delete)"; fi
  exit 0
}

[ "$MODE" = uninstall ] && uninstall
preflight
[ "$MODE" = check ] && { diagnose; exit $((FAILS>0)); }

# ---------- install steps
step "1. yt-dlp + ffmpeg"
if [ "$OS" = Darwin ]; then
  { run brew install yt-dlp ffmpeg; run brew upgrade yt-dlp ffmpeg; yt-dlp --version >/dev/null && ffmpeg -version >/dev/null; } && ok "yt-dlp / ffmpeg" || fail "yt-dlp / ffmpeg" "brew"
else
  { run uv tool install --upgrade yt-dlp; export PATH="$HOME/.local/bin:$PATH"; yt-dlp --version >/dev/null && ffmpeg -version >/dev/null; } && ok "yt-dlp / ffmpeg" || fail "yt-dlp / ffmpeg" "uv tool / ffmpeg missing"
  say "  note: add \$HOME/.local/bin to PATH for yt-dlp; Playwright (MotionClone) may need system libs: sudo npx playwright install-deps chromium"
fi
ffmpeg -hide_banner -filters 2>/dev/null | grep -q drawtext || say "  note: ffmpeg lacks drawtext/libass: on-screen text is rendered with Remotion"

step "2. Whisper venv"
{ [ -x "$B/whisper-venv/bin/python" ] || run uv venv --python 3.11 "$B/whisper-venv"; run uv pip install --python "$B/whisper-venv/bin/python" openai-whisper; } \
  && ok "Whisper" || fail "Whisper" "uv/pip"

step "3. FFmpeg skill"
{ clone kajisho5/ffmpeg-skill ffmpeg-skill && link "$B/ffmpeg-skill"; } && ok "ffmpeg-skill" || fail "ffmpeg-skill" "git"

step "4. Ghost Editor"
{ clone kurbaitaev/ghost-editor ghost-editor && link "$B/ghost-editor" \
  && { [ -x "$B/media-venv/bin/python" ] || run uv venv --python 3.11 "$B/media-venv"; } \
  && run uv pip install --python "$B/media-venv/bin/python" numpy opencv-python pillow google-genai \
  && mkdir -p "$HOME/.venvs" && { [ -e "$HOME/.venvs/media" ] || ln -s "$B/media-venv" "$HOME/.venvs/media"; } \
  && (cd "$B/ghost-editor" && run "$B/media-venv/bin/python" scripts/library_restore.py); } \
  && ok "Ghost Editor (add GEMINI_API_KEY to $B/ghost-editor/.env)" || fail "Ghost Editor" "see log"

step "5. Claude Shorts"
{ clone AgriciDaniel/claude-shorts claude-shorts \
  && { [ -e "$HOME/.shorts-skill" ] || { run "$(uv python find 3.11)" -m venv "$B/shorts-venv" && ln -s "$B/shorts-venv" "$HOME/.shorts-skill"; }; } \
  && (cd "$B/claude-shorts" && run bash setup.sh && run bash install.sh); } && ok "Claude Shorts" || fail "Claude Shorts" "setup.sh/install.sh"

step "6. Three.js skills"
{ clone CloudAI-X/threejs-skills threejs-skills && for d in "$B"/threejs-skills/skills/*/; do link "${d%/}"; done; } && ok "Three.js skills" || fail "Three.js skills" "git"

step "7. Motion skills (19 packs)"
PACKS="ad-video b-roll data-animation ecommerce-video explainer-video freelance-motion generative-illustration javascript-animation kinetic-typography lower-thirds manim map-animation motion-design talking-head text-message-video tiktok-video web-animation webgl-animation youtube-video"
bad=0
for p in $PACKS; do
  clone "iart-ai/$p-skills" "motion-packs/$p-skills" || { bad=1; continue; }
  for d in "$B"/motion-packs/$p-skills/skills/*/; do n=$(basename "$d"); d="${d%/}"
    if [ -e "$S/$n" ] && [ "$(readlink "$S/$n")" != "$d" ]; then   # name taken by another pack: link under name-pack
      [ -e "$S/$n-$p" ] || { [ $DRY = 1 ] || { ln -s "$d" "$S/$n-$p"; echo "$S/$n-$p" >> "$B/.links"; }; }
    else link "$d"; fi
  done
done
[ $bad = 0 ] && ok "Motion skills" || fail "Motion skills" "some packs failed to clone"

step "8. MotionClone"
{ clone codename-zen/motionclone motionclone && cd "$B/motionclone" \
  && run npx -y pnpm@10 install --store-dir "$B/cache/pnpm" --frozen-lockfile \
  && run npx -y pnpm@10 exec playwright install chromium && run npx -y pnpm@10 build && run npm link \
  && { [ -e "$S/motionclone" ] || [ $DRY = 1 ] || { ln -s "$B/motionclone/skill" "$S/motionclone" && echo "$S/motionclone" >> "$B/.links"; }; } \
  && { command -v claude >/dev/null && { claude mcp list 2>/dev/null | grep -q '^motionclone' || run claude mcp add -s user motionclone -- motionclone mcp; } || true; } \
  && motionclone --help >/dev/null; } && ok "MotionClone" || fail "MotionClone" "needs Node 24+"
cd "$REPO"

step "9. HyperFrames skills"
run npx -y skills add heygen-com/hyperframes -g -a claude-code -y && ok "HyperFrames" || fail "HyperFrames" "needs Node 22+"

step "10. Remotion skills + promo template"
{ clone remotion-dev/skills remotion-skills && for d in "$B"/remotion-skills/skills/*/; do link "${d%/}"; done \
  && (cd "$REPO/templates/remotion-promo" && run npm install --no-audit --no-fund); } && ok "Remotion skills + template" || fail "Remotion" "npm/git"

step "11. Reference list"
clone zhuyansen/awesome-claude-video-skills awesome-claude-video-skills && ok "Awesome list" || fail "Awesome list" "git"

step "12. IGO hub + director skills"
{ link "$REPO/skills/video-studio" && link "$REPO/skills/igo-director"; } && ok "video-studio + igo-director" || fail "hub skills" "ln"

if [ $BLENDER = 1 ]; then step "13. Blender (optional)"; { [ "$OS" = Darwin ] && run brew install --cask blender || { say "  Linux: sudo snap install blender --classic"; false; }; } && ok "Blender" || fail "Blender" "brew cask"; fi

diagnose
say ""; say "========== RESULTS =========="; printf '%s\n' "${RESULTS[@]}" | tee -a "$LOG"
say ""; say "Skills in $S: $(ls "$S" | wc -l | tr -d ' ')"
say "Tests:     python3 $REPO/studio/tests/test_studio.py"
say "Dashboard: python3 $REPO/dashboard/server.py  (http://localhost:8792)"
say "Next: restart Claude Code. Keys (optional): GEMINI_API_KEY in $B/ghost-editor/.env, ELEVENLABS_API_KEY."
[ $FAILS = 0 ] && { say "ALL STEPS PASSED"; exit 0; } || { say "$FAILS step(s) failed, see $LOG"; exit 1; }
