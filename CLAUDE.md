# 감사일기 릴스 편집 툴킷

마정이의 감사일기 인스타 릴스를 역할별 담당자(서브에이전트)가 나눠 편집하는 프로젝트.
이 폴더가 IT Reelsmaker 플러그인의 프로젝트 폴더이기도 하다 (`it-reelsmaker.json` → `project_root: "."`).

## 시작
- 전체 편집: `/gratitude-reels` (감독관 스킬). 한 단계만: "자막만 다시 해줘" 처럼 말하면 감독관이 그 단계부터 이어 간다.
- B-roll 얼굴 블러만: `/faceblur`

## 역할
| 담당 | 에이전트 | 주로 쓰는 플러그인 |
|---|---|---|
| 감독관 | 스킬 `gratitude-reels` | 전체 지휘, Remotion 렌더·마스터 (IT Reelsmaker) |
| 전사기 | `transcriber` | IT Reelsmaker transcribe·structure |
| 후커 | `hooker` | Social Media Skills hook-writer + structure 티저 후보 |
| 컷편집 | `cut-editor` | IT Reelsmaker speech_mask·cut·balance |
| 자막 | `subtitler` | IT Reelsmaker 자막 키트·subs + captions-and-clipping |
| 썸네일 | `thumbnail-maker` | IT Reelsmaker poster + thumbnail-design + tools/thumbs.py |
| 화면연결 | `broll-matcher` | faceblur 스킬 → IT Reelsmaker footage·visual_plan |
| 오디오 | `audio-engineer` | IT Reelsmaker master_audio·library_catalog |

컷편집이 끝나면 **자막 담당과 썸네일 담당은 병렬**로 돈다.

## 규칙
- 플러그인 스크립트는 직접 경로로 부르지 말고 `python3 tools/plug.py rm <스크립트> …` (플러그인 위치를 찾아 준다).
- 플러그인 스크립트를 고치거나 다시 짜지 않는다. 영상마다 다른 것은 `edit/<id>/` 의 JSON에만.
- B-roll 은 항상 얼굴 블러된 `footage/<id>/broll_blur/` 만 쓴다. 원본 `broll/` 직접 사용 금지.
- 사용자 확인 없이 컷(build)·B-roll 적용(apply)·발행하지 않는다.
- 최종 결과물은 **편집 완료 영상 1개 + 썸네일 이미지 후보 3개**. 썸네일을 영상 첫 프레임(커버)에 넣지 않는다 (`master_audio.py --cover` 금지).
- 사용자 말을 지어내거나 의미를 바꾸는 편집 금지. 자막은 들은 대로, 맞춤법만.

## 폴더
```
footage/<id>/main.*          메인 영상 (원본 복사본)
footage/<id>/broll/          B-roll 원본      → broll_blur/ 얼굴 블러본
edit/<id>/                   IT Reelsmaker 작업 폴더 + pipeline.json(진행 상태)
reels/                       Remotion 프로젝트 (kit.py new 로 생성)
out/<id>/                    최종 결과물: <id>.mp4 (편집 완료 영상) + thumbnail_1~3.jpg (썸네일 후보)
brands/majunge/              브랜드 프로필 (색·폰트·톤)
assets/sfx, assets/music     효과음·배경음 (직접 넣은 것 + tools/sfx.py 합성음)
assets/fonts                 젠세리프(썸네일·훅 문구) · subtitle/ 메모먼트 꾹꾹체(자막)
tools/                       plug.py · job.py · faceblur.py · thumbs.py · subs_preview.py · sfx.py · gratitude.py(감사일기 렌더 모드)
```

## 클라우드 세션에서 진행하기 (10.6 감사일기로 검증, 2026-10-10)
원격 세션(서브에이전트 위임)은 담당자가 명령 전 준비에 시간을 많이 써서 멈춘 것처럼 보였다. 지금은 **클라우드 세션의 Claude가 감독관 흐름을 직접 돌리고, 단계마다 사용자 확인**을 받는 방식이 가장 빠르다.
Mac 툴킷은 기기 연결(remote-devices)로 파일만 다룰 수 있고, Mac 프로그램은 실행할 수 없다.

### 준비 (세션마다)
1. 폴더 접근 요청: 툴킷 `~/Desktop/github/claude-video-editor`, 원본 `~/Library/Mobile Documents/com~apple~CloudDocs/크리에이터/감사일기`, (재전사가 필요하면) `~/.cache/huggingface`.
2. GitHub 저장소를 클론하고, **git 에 없는 파일**을 stage 해서 덮어쓴다: `brands/`, `assets/fonts/`, `assets/models/`, `reels/package*.json`·`reels/src/`, `footage/<id>/`, `edit/<id>/`, 푸시 안 된 커밋의 파일.
   한글 파일명은 stage 뒤 이름 정규화(NFD)가 달라 `cp "경로"` 가 실패한다 → `find … -exec cp` 로 복사.
3. `config/plugins.json` 은 지우고 `export REELSMAKER_DIR=<세션의 it-reelsmaker 폴더>` (`find / -name kit.py -path '*it-reelsmaker*'`).
4. `cd reels && npm ci`. Remotion 은 브라우저를 remotion.media 에서 받으려다 실패한다 → still·render 에 항상
   `--browser-executable=/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell`.
5. `python3 tools/gratitude.py patch-kit` → `check`.

### 단계별 메모
- **전사:** 클라우드에는 음성 인식 모델이 없다(Hugging Face 차단). 전체 전사는 Mac 터미널에서
  `python3 tools/plug.py rm transcribe edit/<id> footage/<id>/main.MOV --language ko --model medium` (2분 영상 몇 분).
- **더듬은 곳·반복 찾기:** Whisper 는 다시 말한 부분을 1초 넘게 늘어진 단어 하나로 뭉친다. 늘어진 단어 주변을 **5초 이하로 잘라 다시 받아쓴다** —
  기기 연결 VM 에서 `pip install faster-whisper` 후 `~/.cache/huggingface` 의 medium 모델로 실행(VM 은 HF 다운로드 불가, Mac 캐시는 읽힘).
  결과는 `edit/<id>/snip/` 에 두고, 맞는 구간의 단어를 `transcripts/main.json` 에 덮어쓴다(원본은 `main.before-splice.json`). 끊는 자리는 `speech_mask.py` 로.
- **얼굴 블러 모델:** 클라우드에서 GitHub raw 가 막히면 기기 연결 VM 에서 받아 `assets/models/` 에 둔다.
- **전달:** 기기로 보내는 파일은 30MB 한도 → 마스터를 `libx264 -b:v 3600k -maxrate 4500k`, 소리는 `-c:a copy` 로 다시 압축하고
  `master_audio --check` 로 다시 확인. 영상은 SendUserFile 로 보낸 뒤 그 fileUuid 로 기기에 쓴다. 인스타가 어차피 다시 압축하므로 화질 문제 없음.
- **git:** 기기 연결 셸은 기본적으로 삭제가 막혀 git 잠금 파일이 남는다 → 커밋 전에 툴킷 폴더 삭제 권한을 요청한다. 푸시는 사용자가 Mac 에서.

### 사용자가 정한 것 (다음 영상도 그대로)
- 결과물 = 영상 1개 + 썸네일(후보를 보여 주고 고른 1장). 썸네일은 영상 첫 프레임에 넣지 않는다.
- 썸네일 문구: 젠세리프 파스텔 그라데이션, 강조색 없음, 가운데 정렬(`"align": "center"`), 얼굴을 가리지 않는 위치.
- 훅: 위쪽 훅 문구 없이, 훅 문장을 썸네일 스타일로 한 글자씩 타이핑(기울기 없음) + 글자마다 타닥 소리.
- 자막: 마침표 없음, 제자리 타자기(문장 자리를 먼저 잡고 단어가 나타남) 유지. 오인식은 `fix`/`fix_at`.
- 컷: 더듬은 곳·같은 말 반복은 전부 뺀다 — 늘어진 단어는 재전사로 반드시 확인.
- B-roll: 다른 사람 얼굴은 블러(본인은 남김), 화상 통화 캡처는 이름표·UI 를 잘라낸다. 사진은 부드럽게 1.05배 확대.
- 효과음: "감사합니다" 말 시작마다 뽁, 훅 타이핑 타닥. 효과음 미리 듣기용 파일로 먼저 확인받은 뒤 영상에 입힌다.
