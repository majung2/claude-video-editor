#!/usr/bin/env bash
# [클라우드 세션 준비 2/2 — 클라우드 쪽] Mac 에서 가져온 묶음으로 작업 폴더를 만들고 편집할 준비를 한 번에 한다.
#
#   bash cloud_setup.sh <cloud.tgz> [작업 폴더=~/w] [따로 가져온 메인 영상 ...]
#
# 묶음에 이 스크립트도 들어 있으므로 처음에는 묶음에서 꺼내 실행한다:
#   tar -xzf <cloud.tgz> -O --wildcards '*tools/cloud_setup.sh' > /tmp/cloud_setup.sh && bash /tmp/cloud_setup.sh <cloud.tgz>
#
# 하는 일: 풀기 → 한글 파일 이름 정리(Mac NFD → NFC) → IT Reelsmaker 위치 찾기 → 렌더 엔진 npm ci →
#          렌더용 브라우저 지정 → 얼굴 모델 경로 → 감사일기 패치 확인 → 환경 점검
# 끝나면 <작업 폴더>/.cloud_env 를 source 해서 쓴다 (REELSMAKER_DIR, REMOTION_BROWSER).
# 전사용 플러그인 스크립트 묶음도 만든다: <작업 폴더>/_bundle/rm_scripts.tgz → Mac 연결 쪽 전사(vm_transcribe.sh)에 쓴다.
set -euo pipefail
BUNDLE="$(readlink -f "$1")"; shift
W="${1:-$HOME/w}"; [ $# -gt 0 ] && shift
T0=$(date +%s)
mkdir -p "$W" && cd "$W"

echo "== 1. 풀기"
tar -xzf "$BUNDLE"
for m in "$@"; do  # 따로 가져온 메인 영상: footage/<id>/ 로 (경로에서 id 를 찾는다)
  id=$(basename "$(dirname "$m")")
  mkdir -p "footage/$id" && cp "$m" "footage/$id/"
done
chmod -R u+w .

echo "== 2. 한글 파일 이름 정리 (NFC)"
python3 - <<'EOF'
import os, unicodedata
n = 0
for d, dirs, files in os.walk(".", topdown=False):
    for name in files + dirs:
        nfc = unicodedata.normalize("NFC", name)
        if nfc != name:
            os.rename(os.path.join(d, name), os.path.join(d, nfc)); n += 1
print(f"  바꾼 이름 {n}개")
EOF

echo "== 3. IT Reelsmaker 위치"
RM=""
for base in "$HOME/.claude" /root/.claude /mnt/skills; do
  [ -d "$base" ] || continue
  hit=$(find "$base" -path '*it-reelsmaker/scripts/kit.py' 2>/dev/null | head -1)
  [ -n "$hit" ] && RM="$(dirname "$(dirname "$hit")")" && break
done
[ -n "$RM" ] || { echo "[오류] IT Reelsmaker 플러그인을 못 찾았어요 (세션에 플러그인이 켜져 있는지 확인)"; exit 1; }
echo "  $RM"
rm -f config/plugins.json   # Mac 경로가 들어 있다
BROWSER=$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell 2>/dev/null | head -1 || true)
cat > .cloud_env <<EOF
export REELSMAKER_DIR="$RM"
export REMOTION_BROWSER="$BROWSER"
EOF
# shellcheck disable=SC1091
source .cloud_env

echo "== 4. 렌더 엔진 (npm ci)"
if [ -f reels/package-lock.json ]; then
  (cd reels && npm ci --no-audit --no-fund --loglevel=error >/dev/null)
  # Remotion 은 브라우저를 remotion.media 에서 받으려다 실패한다 → 이 작업 공간의 headless shell 을 쓰게 한다 (클라우드 사본만 고침)
  if [ -n "$BROWSER" ] && ! grep -q REMOTION_BROWSER reels/remotion.config.ts; then
    printf '\n// cloud_setup.sh: 클라우드 작업 공간의 브라우저 (remotion.media 다운로드가 막혀 있음)\nif (process.env.REMOTION_BROWSER) Config.setBrowserExecutable(process.env.REMOTION_BROWSER);\n' >> reels/remotion.config.ts
  fi
  echo "  ok (브라우저: ${BROWSER:-없음 — still/render 가 실패하면 --browser-executable 지정})"
else
  echo "  [건너뜀] reels/ 가 묶음에 없어요 — kit.py new 로 만든 뒤 styles/*/render.py patch-kit"
fi

echo "== 5. 얼굴 모델"
FM=$(ls assets/models/*.onnx 2>/dev/null | head -1 || true)
python3 - "$FM" <<'EOF'
import json, sys, os
p = "it-reelsmaker.json"; d = json.load(open(p))
d["face_model"] = os.path.abspath(sys.argv[1]) if sys.argv[1] else ""
json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
print("  " + (d["face_model"] or "없음 — faceblur 첫 실행 때 받거나 Mac 연결 쪽에서 받아 assets/models/ 에"))
EOF

echo "== 6. 편집 스타일 패치 (styles/*/render.py)"
if [ -d reels/src ]; then
  for r in styles/*/render.py; do echo "  $r"; python3 "$r" patch-kit && python3 "$r" check; done
fi

echo "== 7. 점검"
python3 tools/plug.py doctor 2>&1 | grep -E '^(  ok|  miss|  --)|required' | grep -v -E 'rembg|online add-on' || true

echo "== 8. 전사용 플러그인 스크립트 묶음"
mkdir -p _bundle && tar -czf _bundle/rm_scripts.tgz -C "$RM" scripts
echo "  $W/_bundle/rm_scripts.tgz → Mac 툴킷 _bundle/ 에 없으면 보내서 vm_transcribe.sh 가 쓴다"

echo "준비 끝 ($(( $(date +%s) - T0 ))초). 쓰기 전에: source $W/.cloud_env"
