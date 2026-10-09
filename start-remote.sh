#!/bin/bash
# 폰(Claude 앱)에서 이 툴킷을 원격으로 쓰기 — Claude Code Remote Control 서버 모드
#   bash ~/Desktop/github/claude-video-editor/start-remote.sh
#
# · 이 터미널 창을 열어 둔 동안 폰의 Claude 앱 → Code 에서 이 Mac의 세션을 고를 수 있다.
#   (스페이스바를 누르면 QR 코드가 나온다 → 폰 카메라로 스캔)
# · 작업은 이 Mac에서 돈다: 영상·폰트·플러그인 모두 이 Mac의 것을 쓴다.
# · caffeinate 로 켜 둔 동안 Mac이 잠들지 않는다 (덮개를 닫으면 잠들 수 있으니 전원 연결 권장).
# · 끄기: 이 창에서 Ctrl+C. 4시간 안에 다시 실행하면 같은 세션이 이어진다.
# 처음 한 번: "Enable Remote Control? (y/n)" → y, "Trust <폴더>? [y/N]" → y
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
command -v claude >/dev/null || { echo "Claude Code 가 없어요. 먼저 bash setup-mac.sh"; exit 1; }
echo "감사일기 릴스 원격 세션 시작 — 폰: Claude 앱 → Code → '감사일기 릴스'"
exec caffeinate -i claude remote-control --name "감사일기 릴스"
