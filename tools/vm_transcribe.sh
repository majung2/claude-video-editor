#!/usr/bin/env bash
# [전사 — Mac 연결 셸(device_bash) 쪽] 클라우드에는 음성 인식 모델이 없어서(Hugging Face 차단),
# Mac 에 받아 둔 faster-whisper 모델을 Mac 연결 VM 에서 읽어 전사한다. 사용자가 터미널을 열 필요가 없다.
#
#   bash tools/vm_transcribe.sh <영상 id>      # "계속" 이 나오면 같은 명령을 다시 (device_bash timeout_ms 180000)
#                                              # "끝" 이 나오면 edit/<id>/transcripts/main.json 완성
#
# device_bash 는 호출이 끝나면 그 안의 프로그램을 모두 끝내고 한 번에 최대 3분이라, 백그라운드로는 못 돌린다.
# 그래서 조각으로 나눠 이어서 받아쓴다 (tools/vm_transcribe.py). 이 VM 에서 2분 영상은 보통 1~2번이면 끝난다.
#
# 필요한 것:
#   - 폴더 접근: 툴킷, ~/.cache/huggingface (Mac 에서 한 번이라도 전사했으면 medium 모델이 거기 있다)
#   - _bundle/rm_scripts.tgz: IT Reelsmaker 스크립트 (cloud_setup.sh 가 클라우드에서 만든 것을 보내 둔다)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ID="${1:?영상 id}"
cd "$ROOT"
[ -f _bundle/rm_scripts.tgz ] || { echo "[오류] _bundle/rm_scripts.tgz 가 없어요 — 클라우드의 cloud_setup.sh 결과를 먼저 보내 주세요"; exit 1; }
HUB=$(find "$HOME/mnt" -maxdepth 3 -type d -name hub -path '*huggingface*' 2>/dev/null | head -1)
[ -n "$HUB" ] || { echo "[오류] ~/.cache/huggingface 접근이 없어요 — 폴더 접근을 요청하세요"; exit 1; }
if [ ! -f "$HOME/rm/scripts/transcribe.py" ] || [ _bundle/rm_scripts.tgz -nt "$HOME/rm/scripts/transcribe.py" ]; then
  rm -rf "$HOME/rm" && mkdir -p "$HOME/rm" && tar -xzf _bundle/rm_scripts.tgz -C "$HOME/rm"
fi
python3 -c "import faster_whisper" 2>/dev/null || python3 -m pip install -q faster-whisper >/dev/null 2>&1
# 모델은 Mac 캐시에서만 (다운로드 시도 없이)
HF_HUB_CACHE="$HUB" HF_HUB_OFFLINE=1 RM_SCRIPTS="$HOME/rm/scripts" python3 tools/vm_transcribe.py "$ID"
