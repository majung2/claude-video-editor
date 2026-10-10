#!/usr/bin/env bash
# [클라우드 세션 준비 1/2 — Mac 쪽] 툴킷 폴더를 압축 파일 하나로 묶는다.
#
#   bash tools/cloud_bundle.sh [영상 id ...]
#     예) bash tools/cloud_bundle.sh 2026-10-07
#
# 클라우드 세션의 Claude 가 Mac 연결 셸(device_bash)에서 실행하고, 결과 파일 하나만 stage 해서 가져간다.
# (파일을 하나씩 60개 넘게 가져오던 것을 한 번으로 — 2026-10-10)
#
# 묶는 것: 툴킷 전체(커밋 안 된 변경 포함) + git 에 없는 개인 파일(brands/, 폰트, 얼굴 모델, 효과음, 음악,
#          패치된 렌더 엔진 reels/src) + 지정한 영상의 footage/<id>/, edit/<id>/
# 빼는 것: .git, reels/node_modules (클라우드에서 npm ci), out/, 다른 영상, 캐시
# 결과:    _bundle/cloud.tgz (git 에 안 올라감, 매번 덮어씀)
#          영상 원본이 커서 묶음이 400MB 를 넘으면 메인 영상은 빼고, 따로 stage 할 경로를 알려 준다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p _bundle
LIST="_bundle/files.txt"
: > "$LIST"

# 툴킷 + 개인 파일 (영상·작업 폴더·결과물은 아래에서 고른 것만)
find . -path ./.git -prune -o -path ./reels/node_modules -prune -o -path ./out -prune \
       -o -path ./footage -prune -o -path ./edit -prune -o -path ./_bundle -prune \
       -o -path ./_footage_index -prune -o -path ./reels/out -prune -o -path ./reels/.kit-backup -prune -o -path './reels/public/2*' -prune \
       -o -name __pycache__ -prune -o -name .DS_Store -prune \
       -o -type f -print >> "$LIST"

MAIN_SKIPPED=()
for id in "$@"; do
  [ -d "footage/$id" ] && find "footage/$id" -name .DS_Store -prune -o -type f -print >> "$LIST"
  [ -d "edit/$id" ] && find "edit/$id" -path "edit/$id/clips" -prune -o -path "edit/$id/inserts" -prune \
       -o -name '*.mp4' -prune -o -name .DS_Store -prune -o -type f -print >> "$LIST"
done

# stage 한도(400MB)를 넘으면 메인 영상은 빼고 따로 가져가게 한다
total=$(tr '\n' '\0' < "$LIST" | xargs -0 du -cb 2>/dev/null | tail -1 | cut -f1)
if [ "${total:-0}" -gt 380000000 ]; then
  for id in "$@"; do
    for m in footage/"$id"/main.*; do
      [ -f "$m" ] || continue
      grep -vxF "$m" "$LIST" > "$LIST.tmp" && mv "$LIST.tmp" "$LIST"
      MAIN_SKIPPED+=("$m")
    done
  done
fi

tar -czf _bundle/cloud.tgz -T "$LIST"
rm -f "$LIST"
echo "묶음: _bundle/cloud.tgz — Mac 경로: <툴킷 폴더>/_bundle/cloud.tgz ($(du -h _bundle/cloud.tgz | cut -f1))"
for m in "${MAIN_SKIPPED[@]:-}"; do
  [ -n "$m" ] && echo "따로 stage: <툴킷 폴더>/$m"
done
exit 0
