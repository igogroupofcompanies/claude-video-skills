#!/usr/bin/env bash
# Health check: tools + skill links. Exit 1 on any problem.
B="${1:-$([ -d "/Volumes/Disk 1 SSD/claude-video-tools" ] && echo "/Volumes/Disk 1 SSD/claude-video-tools" || echo "$HOME/claude-video-tools")}"
S="$HOME/.claude/skills"; bad=0
chk(){ if out=$("${@:2}" 2>&1 | head -1) && [ -n "$out" ] || "${@:2}" >/dev/null 2>&1; then echo "  ok    $1  ${out:0:60}"; else echo "  FAIL  $1"; bad=$((bad+1)); fi; }
chk yt-dlp yt-dlp --version; chk ffmpeg ffmpeg -version; chk node node -v
chk whisper "$B/whisper-venv/bin/python" -c "import whisper;print('ok')"
chk ffmpeg-skill python3 "$B/ffmpeg-skill/scripts/probe.py" --help
chk ghost-deps "$B/media-venv/bin/python" -c "import cv2,numpy,PIL,google.genai;print('ok')"
chk shorts "$B/shorts-venv/bin/python" -c "import faster_whisper,cv2,mediapipe;print('ok')"
chk motionclone motionclone --version
for s in video-studio igo-director ffmpeg-skill ghost-editor shorts motionclone hyperframes remotion-best-practices threejs-fundamentals kinetic-typography; do
  [ -e "$S/$s/SKILL.md" ] && echo "  ok    skill $s" || { echo "  FAIL  skill $s missing"; bad=$((bad+1)); }; done
broken=$(find "$S" -maxdepth 1 -type l ! -exec test -e {} \; -print | wc -l | tr -d ' ')
[ "$broken" = 0 ] && echo "  ok    no broken skill links" || { echo "  FAIL  $broken broken skill links"; bad=$((bad+1)); }
echo "$([ $bad = 0 ] && echo ALL GOOD || echo "$bad problem(s)")"; exit $((bad>0))
