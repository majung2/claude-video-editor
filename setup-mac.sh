#!/bin/bash
# 감사일기 릴스 툴킷 — Mac 한 번에 세팅
#   bash ~/Desktop/github/claude-video-editor/setup-mac.sh
#
# 1) GitHub 푸시  2) 프로그램 설치(ffmpeg·node·Python 패키지·Claude Code)
# 3) 플러그인 3개 설치  4) 폰트 확인  5) 환경 점검(doctor)
# 이미 된 단계는 건너뛴다. 여러 번 실행해도 안전하다.
set -u
cd "$(dirname "$0")"
ROOT="$(pwd)"
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
step() { printf "\n\033[1m[%s] %s\033[0m\n" "$1" "$2"; }

step 1 "GitHub 푸시"
if git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1 && [ -z "$(git log @{u}.. --oneline 2>/dev/null)" ]; then
  ok "이미 올라가 있음"
else
  git push -u origin main && ok "푸시 완료" || warn "푸시 실패 — GitHub 로그인 확인 후 다시 실행 (gh auth login 또는 키체인)"
fi

step 2 "프로그램"
if ! command -v brew >/dev/null; then
  warn "Homebrew 가 없어요. https://brew.sh 의 설치 명령을 먼저 실행한 뒤 이 스크립트를 다시 실행하세요."; exit 1
fi
for p in ffmpeg node; do
  command -v "$p" >/dev/null && ok "$p 있음" || { brew install "$p" && ok "$p 설치"; }
done
python3 -m pip install --user -q -r requirements.txt 2>/dev/null \
  || python3 -m pip install --user --break-system-packages -q -r requirements.txt \
  && ok "Python 패키지 (faster-whisper, opencv, pillow …)"
if ! command -v claude >/dev/null; then
  curl -fsSL https://claude.ai/install.sh | bash && export PATH="$HOME/.local/bin:$PATH"
fi
command -v claude >/dev/null && ok "Claude Code $(claude --version 2>/dev/null | head -1)" || { warn "Claude Code 설치 실패"; exit 1; }

step 3 "플러그인 (프로젝트 범위)"
add_install() { # 마켓플레이스 소스, 플러그인@마켓플레이스
  claude plugin marketplace add "$1" >/dev/null 2>&1
  if claude plugin list 2>/dev/null | grep -q "${2%@*}"; then ok "$2 이미 설치"
  else claude plugin install "$2" --scope project && ok "$2 설치" || warn "$2 설치 실패"; fi
}
add_install itpartypattaya/reels-montage   it-reelsmaker@itparty
add_install social-media-skills/skills     social-media-skills@social-media-skills
add_install rendi-api/ffmpeg-llm           ffmpeg-llm@rendi-official

step 4 "폰트"
ls assets/fonts/*[Zz][Ee][Nn]*[Ss][Ee][Rr][Ii][Ff]* >/dev/null 2>&1 && ok "젠세리프 (썸네일·훅 문구)" || warn "젠세리프 없음 → assets/fonts/ 에 넣기"
ls assets/fonts/subtitle/* >/dev/null 2>&1 && ok "메모먼트 꾹꾹체 (자막)" || warn "꾹꾹체 없음 → assets/fonts/subtitle/ 에 넣기"
[ -n "$(ls assets/sfx/*.wav 2>/dev/null)" ] || python3 tools/sfx.py >/dev/null && ok "기본 효과음"

step 5 "환경 점검 (doctor)"
python3 tools/plug.py doctor
# 편집 스타일마다 렌더 엔진 패치를 넣는다 (styles/<스타일>/render.py patch-kit). reels/ 가 아직 없으면 첫 실행 때 감독관이 한다
if [ -f reels/src/ReelKit.tsx ]; then
  for r in styles/*/render.py; do python3 "$r" patch-kit || true; done
fi
echo
echo "다음: 폰에서 원격으로 쓰려면  bash $ROOT/start-remote.sh"
