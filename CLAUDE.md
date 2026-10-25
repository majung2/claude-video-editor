# 릴스 편집 툴킷 (편집 스타일별)

마정이의 인스타 릴스를 **편집 스타일별**로 자동 편집하는 프로젝트. 스타일마다 감독관 스킬과 `styles/<스타일>/` 폴더가 있고,
전사·컷·자막·B-roll·효과음·렌더 같은 공용 단계와 도구는 모든 스타일이 같이 쓴다.
이 폴더가 IT Reelsmaker 플러그인의 프로젝트 폴더이기도 하다 (`it-reelsmaker.json` → `project_root: "."`).

## 편집 스타일
| 스타일 | 폴더 | 감독관 스킬 | 상태 |
|---|---|---|---|
| 감사일기 (`gratitude`) | `styles/gratitude/` | `/gratitude-reels` | 사용 중 (10.6 편집으로 검증) |
| 자유형식 (`free`) | `styles/free/` | `/free-reels` | 새로 추가 — 공통 스펙(썸네일 형식·훅·컷·자막)은 항상 감사일기 방식, 나머지는 지시서 `edit/<id>/brief.json` 대로. 엔진 패치 없음 |

- **영상을 시작할 때 스타일을 정한다:** `python3 tools/job.py new <id> --main … --style <스타일>` → `edit/<id>/pipeline.json` 의 `style`.
  이후 모든 단계는 그 스타일의 `styles/<스타일>/README.md`(사용자 결정)·`config.json`·감독관 스킬을 따른다.
- **스타일 전용 결정은 `styles/<스타일>/README.md` 에만** 적는다. 이 파일에는 모든 스타일에 해당하는 것만.
- 새 스타일 추가 방법: `styles/README.md`.

## 시작
- 감사일기 전체 편집: `/gratitude-reels`. 지시대로 하는 편집: `/free-reels`. 한 단계만: "자막만 다시 해줘" 처럼 말하면 감독관이 그 단계부터 이어 간다.
- B-roll 얼굴 블러만: `/faceblur` (공용)

## 역할 (공용 — 스타일마다 감독관만 다르다)
| 담당 | 에이전트 | 주로 쓰는 플러그인 |
|---|---|---|
| 감독관 | 스타일별 스킬 (감사일기: `gratitude-reels`) | 전체 지휘, Remotion 렌더·마스터 (IT Reelsmaker) |
| 전사기 | `transcriber` | IT Reelsmaker transcribe·structure |
| 후커 | `hooker` | Social Media Skills hook-writer + structure 티저 후보 |
| 컷편집 | `cut-editor` | IT Reelsmaker speech_mask·cut·balance |
| 자막 | `subtitler` | IT Reelsmaker 자막 키트·subs + captions-and-clipping |
| 썸네일 | `thumbnail-maker` | IT Reelsmaker poster + thumbnail-design + tools/thumbs.py |
| 화면연결 | `broll-matcher` | faceblur 스킬 → IT Reelsmaker footage·visual_plan |
| 오디오 | `audio-engineer` | IT Reelsmaker master_audio·library_catalog |

담당자 지시문(`.claude/agents/*.md`)에 감사일기 전용 단계가 적힌 곳은 "감사일기" 로 표시돼 있다 — 다른 스타일에서는 그 스타일 README 가 우선.
컷편집이 끝나면 **자막 담당과 썸네일 담당은 병렬**로 돈다.

## 규칙 (모든 스타일)
- 플러그인 스크립트는 직접 경로로 부르지 말고 `python3 tools/plug.py rm <스크립트> …` (플러그인 위치를 찾아 준다).
- 플러그인 스크립트를 고치거나 다시 짜지 않는다. 영상마다 다른 것은 `edit/<id>/` 의 JSON에만, 스타일마다 다른 것은 `styles/<스타일>/` 에만.
- 렌더 엔진(`reels/`)은 모든 스타일이 같이 쓴다. 스타일 패치(`styles/<스타일>/render.py patch-kit`)는 **덧붙이기만** 하고,
  그 스타일의 props 일 때만 동작해야 한다 (예: 감사일기 자막은 `subtitles: "gratitude"` 일 때만).
- B-roll 은 항상 얼굴 블러된 `footage/<id>/broll_blur/` 만 쓴다. 원본 `broll/` 직접 사용 금지.
- 사용자 확인 없이 컷(build)·B-roll 적용(apply)·발행하지 않는다.
- 썸네일은 영상과 별개 결과물이다. 영상 첫 프레임(커버)에 넣지 않는다 (`master_audio.py --cover` 금지).
- 사용자 말을 지어내거나 의미를 바꾸는 편집 금지. 자막은 들은 대로, 맞춤법만.

## 폴더
```
styles/<스타일>/             스타일 전용: README.md(결정) · config.json · thumb.json · render.py · references/
config/thumb.json            썸네일 문구 공통 스펙 (모든 스타일)
config/audio.json            오디오 공통 스펙 (모든 스타일) — −14 LUFS·−1dBTP, BGM 목소리 −20~−25dB
footage/<id>/main.*          메인 영상 (원본 복사본)
footage/<id>/broll/          B-roll 원본      → broll_blur/ 얼굴 블러본
edit/<id>/                   IT Reelsmaker 작업 폴더 + pipeline.json(스타일·진행 상태)
reels/                       Remotion 렌더 엔진 (kit.py new 로 생성, 모든 스타일 공용, git 에 없음)
out/<id>/                    최종 결과물: <id>.mp4 + thumbnail.jpg (후보 thumbnail_1~3.jpg)
brands/majunge/              브랜드 프로필 (색·폰트·톤) — 사람 단위라 스타일 공용
brands/majunge/account/      인스타 @majunge.log 계정 분석 스타일 (style-guide.md · style-profile.json, 2026-10-24 승인) — 편집 전 구성안 짤 때 참고
assets/sfx, assets/music     효과음·배경음 (tools/sfx.py 합성음 + 직접 넣은 것)
assets/fonts                 젠세리프 · subtitle/ 메모먼트 꾹꾹체
tools/                       공용 도구: plug · job · faceblur · thumbs · cleanup_src(컨펌 후 원본 삭제) · subs_preview · sfx · fonts · cloud_bundle/setup · vm_transcribe
```

## 클라우드 세션에서 진행하기 (모든 스타일 공용, 10.6 감사일기로 검증 2026-10-10)
원격 세션(서브에이전트 위임)은 담당자가 명령 전 준비에 시간을 많이 써서 멈춘 것처럼 보였다. 지금은 **클라우드 세션의 Claude가 감독관 흐름을 직접 돌리고, 단계마다 사용자 확인**을 받는 방식이 가장 빠르다.
Mac 툴킷은 기기 연결(remote-devices)로 파일만 다룰 수 있고, Mac 프로그램은 실행할 수 없다.

### 준비 (세션마다) — 묶음 하나로 1분 안팎
**기본은 Mac 이 켜져 있을 때의 이 방식이다 (사용자 결정 2026-10-10).** 구글 드라이브 `크리에이터/감사일기-툴킷/cloud-setup-bundle.tgz`(스타일 전체가 들어 있음) 는 Mac 을 못 쓸 때의 비상용 — 사용자가 직접 대화에 올려야 하고(드라이브 연결 도구로는 큰 파일을 주고받을 수 없음), 그때는 클라우드에서 전사를 할 수 없다.
1. 폴더 접근 요청: 툴킷 `~/Desktop/github/claude-video-editor`, 원본 `~/Library/Mobile Documents/com~apple~CloudDocs/크리에이터/<스타일 원본 폴더>` (감사일기: `크리에이터/감사일기`), 전사 모델 `~/.cache/huggingface`.
2. 새 영상이면 원본을 툴킷으로 옮겨 둔다 (Mac 연결 셸에서 `cp` 로 `footage/<id>/main.MOV`, `footage/<id>/broll/`).
3. **Mac 연결 셸:** `bash tools/cloud_bundle.sh <id>` → `_bundle/cloud.tgz` 하나 (툴킷 전체 + 커밋 안 된 변경 + 폰트·브랜드·패치된 엔진 + 그 영상).
   400MB 를 넘으면 메인 영상만 빠지고 "따로 stage" 경로가 나온다. → 이 파일(들)만 stage. **git push·클론 필요 없음.**
4. **클라우드:** `tar -xzf <cloud.tgz> -O --wildcards '*tools/cloud_setup.sh' > /tmp/s.sh && bash /tmp/s.sh <cloud.tgz> ~/w [따로 받은 main.MOV]`
   → 풀기·한글 파일 이름(NFC)·플러그인 위치·`npm ci`·렌더 브라우저(remotion.config.ts 에 지정되어 플래그 불필요)·얼굴 모델·패치·점검을 한 번에 (10초 남짓).
   이후 명령 전에 `source ~/w/.cloud_env`.
5. **전사(Mac 연결 셸):** 처음이면 `~/w/_bundle/rm_scripts.tgz` 를 Mac 툴킷 `_bundle/rm_scripts.tgz` 로 보낸다(SendUserFile → device_commit_files).
   `bash tools/vm_transcribe.sh <id>` (device_bash `timeout_ms: 180000`) — "계속"이면 같은 명령을 다시, "끝"이면
   결과 파일(`edit/<id>/transcripts/main.json`, `audio16k-main.*`)을 stage 해서 `~/w/edit/<id>/` 에. 2분 영상은 한 번(약 105초)에 끝났다.
   device_bash 는 호출이 끝나면 그 안의 프로그램을 모두 끝내서 백그라운드 실행(nohup·setsid)은 안 된다 → 1분 조각으로 이어서 받아쓴다.
   사용자가 Mac 터미널을 열 필요가 없다. (안 되면 예전처럼 Mac 터미널에서 `python3 tools/plug.py rm transcribe …`)
6. 결과물·작업 파일은 끝날 때 Mac 으로 보낸다 (아래 "전달"). `edit/<id>/final.mp4` 같은 큰 중간 파일은 보내지 않으므로, 나중에 같은 영상을 다른 세션에서 고치려면 `cut.py` 를 다시 돌린다(2분 영상 약 4분).

### 단계별 메모
- **전사:** 클라우드에는 음성 인식 모델이 없다(Hugging Face 차단) → 준비 5번의 `vm_transcribe.sh`.
- **더듬은 곳·반복 찾기:** Whisper 는 다시 말한 부분을 1초 넘게 늘어진 단어 하나로 뭉친다. 늘어진 단어 주변을 **5초 이하로 잘라 다시 받아쓴다** —
  기기 연결 VM 에서 `pip install faster-whisper` 후 `~/.cache/huggingface` 의 medium 모델로 실행(VM 은 HF 다운로드 불가, Mac 캐시는 읽힘).
  결과는 `edit/<id>/snip/` 에 두고, 맞는 구간의 단어를 `transcripts/main.json` 에 덮어쓴다(원본은 `main.before-splice.json`). 끊는 자리는 `speech_mask.py` 로.
- **얼굴 블러 모델:** 클라우드에서 GitHub raw 가 막히면 기기 연결 VM 에서 받아 `assets/models/` 에 둔다.
- **전달:** 기기로 보내는 파일은 30MB 한도 → 마스터를 `libx264 -b:v 3600k -maxrate 4500k` 로 다시 압축하면서 **소리를 2dB 낮춘다** (`-af volume=-2dB -c:a aac -b:a 192k` → 약 −16 LUFS, 사용자 결정 2026-10-14 · `config/audio.json` delivery).
  `master_audio --check` 는 마스터(−14)에서 통과를 확인하고, 전달본은 ebur128 로 −16 ±0.7 인지 확인. 영상은 SendUserFile 로 보낸 뒤 그 fileUuid 로 기기에 쓴다. 인스타가 어차피 다시 압축하므로 화질 문제 없음.
- **git:** 기기 연결 셸은 기본적으로 삭제가 막혀 git 잠금 파일이 남는다 → 커밋 전에 툴킷 폴더 삭제 권한을 요청한다. 푸시는 사용자가 Mac 에서.
- **stage 가 `untrusted_device`·`session_stale_relogin` 으로 거부되면** Mac 의 Claude 데스크톱 앱 로그인이 만료된 것 → 사용자에게 다시 로그인해 달라고 하고 기다린다.
- **한 편을 여러 파일로 찍었으면** (18·19일차, 2026-10-22): Mac 셸에서 `ffmpeg -f concat -safe 0 -i list.txt -c copy footage/<id>/main.MOV` 로 하나로 합쳐 등록·전사한다.
- **원본이 아이클라우드에만 있으면** (`device_list_dir` 의 `cloudOnly`): VM 에서 읽으면 'Resource deadlock avoided', stage 도 거부 → 사용자에게 Finder 에서 그 파일들 오른쪽 클릭 → '지금 다운로드' 를 부탁한다.
- **메인이 커서 stage 한도(400MB)를 넘으면** (18·19일차): 컷 계획을 승인받은 뒤 Mac 셸에서 쓸 구간만 앞뒤 0.2~0.5초 여유를 두고 trim·concat 해 `footage/<id>/main_sel.mp4`(libx264 CRF 17)로 만들어 stage 한다.
  전사 단어 시간은 그 타임라인으로 옮겨 `transcripts/main_sel.json` 에(cut.json `sources.main`). 나중에 넣을 구간은 `add.mp4` 같은 별도 source 로 뽑아 붙인다.
- **차 안·바깥 소음이 큰 영상:** RMS·VAD 로는 말 사이 쉼을 못 찾는다 → 구간을 5~8초로 잘라 다시 받아쓴 단어 시간(`snip/`)으로 경계를 정한다.
- **영어로 찍은 영상:** `tools/vm_transcribe.py <id> --language en` (vm_transcribe.sh 는 한국어 고정이라 py 를 직접 부른다). 자막은 두 언어 — `styles/gratitude/README.md`.

### 사용자가 정한 것 (모든 스타일)
- 결과물 = 영상 1개 + 썸네일(후보를 보여 주고 고른 1장).
- **중간 결과물은 대화에서만** (2026-10-16): 스틸·컨택트시트·썸네일 비교·미리보기 영상 등은 SendUserFile 로 대화에서만 보여 주고 아이클라우드에 올리지 않는다. **아이클라우드 업로드는 하지 않는다** (사용자 결정 2026-10-24): 사용자가 최종 컨펌하면 결과물은 Mac 툴킷 `out/<id>/` 에만 둔다 (SendUserFile → 그 fileUuid 로 device_commit_files).
- **최종 컨펌 → 원본 삭제** (2026-10-22, 업로드 단계는 2026-10-24 에 뺌): 최종 컨펌하고 결과물을 Mac 툴킷 `out/<id>/` 에 둔 다음, 그 영상에 쓴 원본을 아이클라우드 촬영본 폴더에서 지운다.
  `python3 tools/cleanup_src.py <id> --src <촬영본 폴더>` 로 목록을 먼저 보고(툴킷 `footage/<id>/` 에 같은 크기 사본이 있는 파일만 대상) → `--yes`.
  툴킷에 사본이 없는 원본(나중에 따로 올린 사진 등)은 `--also <파일명…>` 으로 지정하면 `footage/<id>/broll/` 로 복사한 뒤 지운다.
  기기 연결 셸은 삭제가 막혀 있으니 먼저 원본 폴더(`크리에이터`) 삭제 권한을 요청한다. 이번 영상과 무관한 파일(다음 날 촬영본)은 건드리지 않는다.
- **최종 볼륨 −16 LUFS** (2026-10-14, 10.10 에서 −14 는 크다고 함): 마스터 −14 → 전달 압축 때 −2dB. 썸네일은 영상 첫 프레임에 넣지 않는다.
- **썸네일 문구 모습은 모든 스타일 공통** — `config/thumb.json` (2026-10-11, 레퍼런스 "ENTP가 INFP를 좋아하는 이유"): 왼쪽 정렬, 얼굴 바로 아래, 펄 그라데이션, 입체,
  굴곡은 왼쪽 아래에서 시작해 오른쪽 위에서 끝남(세기 24). 장면은 원본 전체에서 얼굴이 화면 위쪽인 프레임 우선.
  작은 글씨(sub, 감사일기 #N)는 제목 바로 아래, 제목 시작점보다 살짝 뒤(`thumb_sub_dx` 11, 2026-10-15 — 10.11 에서 결정). 스타일 `thumb.json` 은 `extends: common` + 바꿀 칸만.
- **화면 안전영역은 모든 스타일 공통** — `config/safe_zone.json` (사용자 결정 2026-10-25, 인스타 UI 캡처로 측정): x 50~890, y 240~1530 (1080×1920). 위 UI ~215, 오른쪽 아이콘 줄 x 925~(y 1250~1820), 아래 캡션 y 1565~. 자막·훅·B-roll 카드는 이 안에 둔다.
- **오디오 기준은 모든 스타일 공통** — `config/audio.json` (2026-10-13): 마스터 −14 LUFS·true peak −1dBTP(−12 LUFS 보다 크게 금지), 목소리 피크 −6~−3dBFS·평균 −18~−12dBFS,
  BGM 은 말할 때 목소리보다 20~25dB 아래(기본 `--gap 22`)·핵심 문장 25dB 이상 덕킹, 효과음은 튀지 않게. BGM 이 있으면 폰 스피커로도 확인.
- 컷: 더듬은 곳·같은 말 반복은 전부 뺀다 — 늘어진 단어는 재전사로 반드시 확인.
- B-roll: 다른 사람 얼굴은 블러(본인은 남김), 화상 통화 캡처는 이름표·UI 를 잘라낸다.
- 새 효과음은 미리 듣기용 파일로 먼저 확인받은 뒤 영상에 입힌다.
- Mac 이 켜져 있을 때의 클라우드 세션 방식이 기본.
- 스타일별 결정(자막 모습, 훅, 효과음 종류, 썸네일 문구 모습 등)은 `styles/<스타일>/README.md` (감사일기: `styles/gratitude/README.md`).
