# claude-video-editor — 스타일별 릴스 자동 편집

카메라를 보고 말한 영상과 B-roll 사진을 넣으면, Claude가 정해 둔 **편집 스타일**대로 단계별로 편집해서
**인스타 릴스용 영상 1개(1080×1920)와 썸네일**을 만들어 주는 툴킷입니다.
편집 엔진은 Claude Code 플러그인(IT Reelsmaker · Social Media Skills · ffmpeg-llm)을 쓰고, 이 저장소는 그 위에
스타일별 모습·형식과 공용 단계(전사, 컷, 자막, 얼굴 블러, 썸네일, 효과음, 렌더)를 얹은 것입니다.

```
메인 영상 + B-roll 사진 + 스타일 선택
  → ① 전사 → ② 훅 고르기 → ③ 컷 편집(더듬은 곳·반복·긴 쉼 제거)
  → ④ 자막 · 썸네일 → ⑤ B-roll 연결(얼굴 블러) → ⑥ 효과음
  → ⑦ 렌더 · 검수 · 마스터링 → out/<id>/ (영상 1개 + 썸네일)
```

## 편집 스타일

| 스타일 | 어떤 영상 | 감독관 | 문서 |
|---|---|---|---|
| **감사일기** (`gratitude`) | 셀카로 그날의 감사한 일 3~4가지를 말하는 영상 | `/gratitude-reels` | [styles/gratitude/README.md](styles/gratitude/README.md) |

스타일마다 자막 모습, 훅 연출, 효과음, 썸네일 문구 모습, 형식(구성·길이)이 다릅니다.
새 스타일을 더하는 방법은 [styles/README.md](styles/README.md) 에 있습니다.

---

## 1. 실행 방법

두 가지 방법이 있습니다. **지금은 A를 권장합니다.** (10.6 감사일기를 A로 끝까지 편집해서 검증)

### A. Claude 앱에서 실행 (권장)

Mac에서 Claude 데스크톱 앱을 켜 두고, Claude 앱(데스크톱·웹·폰)의 **크리에이터 프로젝트**에서 새 대화를 열어 스타일과 영상을 말합니다.

```
감사일기 툴킷으로 10.7 감사일기 편집해줘
```

- 편집은 Anthropic 클라우드 작업 공간에서 돌아가고, Mac의 툴킷 폴더와는 **Claude 데스크톱 앱 연결**로 파일을 주고받습니다.
- 처음에 폴더 접근 허락 창이 몇 번 뜹니다: 툴킷 폴더, 아이클라우드 원본 폴더(감사일기: `크리에이터/감사일기`), 음성 인식 모델 폴더 `~/.cache/huggingface`.
- 작업 공간 준비는 1분 안팎입니다. Claude가 Mac 쪽에서 툴킷을 파일 하나로 묶고(`tools/cloud_bundle.sh`), 클라우드에서 한 번에 풉니다(`tools/cloud_setup.sh`).
  커밋하지 않은 변경도 함께 가져가므로 `git push` 를 안 해도 최신 툴킷으로 작업합니다.
- 전사도 Claude가 Mac에 받아 둔 음성 인식 모델로 직접 돌립니다(`tools/vm_transcribe.sh`). 터미널을 열 필요가 없습니다.
  (Mac에서 한 번도 전사한 적이 없으면 모델이 없으니, 처음 한 번은 Mac 터미널에서 `python3 tools/plug.py rm transcribe …` 를 돌려 주세요.)
- Claude 데스크톱 앱 로그인이 만료되면 파일을 못 가져옵니다. Claude가 알려 주면 Mac에서 다시 로그인하면 됩니다.
- **Mac을 쓸 수 없을 때(비상용):** 구글 드라이브 `크리에이터/감사일기-툴킷` 의 `cloud-setup-bundle.tgz` 를 영상과 함께 대화에 직접 올리면 편집 준비는 됩니다. 다만 클라우드에서는 음성 인식 모델을 받을 수 없어 전사가 안 됩니다. 툴킷을 고친 뒤에는 이 묶음도 새로 만들어 바꿔 두세요.
- 영상마다 **새 대화**로 시작하는 게 좋습니다. 한 대화가 길어지면 느려집니다. 결정은 `CLAUDE.md`(공용)와 `styles/<스타일>/`(스타일별)에 남아 있습니다.

### B. Mac의 Claude Code에서 실행

Mac에서 직접 돌리는 방법입니다. 서브에이전트(담당자 7명)가 단계를 나눠 맡는데, 담당자가 준비에 시간을 오래 써서
멈춘 것처럼 보이는 일이 있었습니다(2026-10-09). A가 안 될 때 씁니다.

**설치 (처음 한 번)** — 젠세리프·메모먼트 꾹꾹체 폰트 파일을 `assets/fonts/` 에 넣은 뒤(`assets/fonts/README.md`):

```bash
bash ~/Desktop/github/claude-video-editor/setup-mac.sh
```

ffmpeg·node·Python 패키지·Claude Code·플러그인 3개 설치 → 폰트·효과음 확인 → 모든 스타일의 엔진 패치 → 환경 점검(doctor)까지 한 번에 합니다.
여러 번 실행해도 안전하고, 끝에 나오는 doctor 결과에서 빠진 것만 채우면 됩니다.

**실행** — 이 폴더에서 Claude Code를 열고 스타일의 감독관을 부릅니다:

```
/gratitude-reels  ~/Movies/감사일기/IMG_4821.MOV 이랑 ~/Movies/감사일기/broll 폴더로 오늘 감사일기 릴스 만들어줘
```

**폰에서 원격으로** — `bash start-remote.sh` 를 켜 두면 폰 Claude 앱 → Code 에 세션이 뜹니다(스페이스바 = QR 코드).
켜 둔 동안 Mac이 잠들지 않고(caffeinate), 툴킷 명령은 `.claude/settings.json` 에서 미리 허용해 둬서 승인 알림이 적습니다.
처음 한 번 `Enable Remote Control?` → y, `Trust …?` → y.

---

## 2. 진행 방식 — 무엇을 묻고, 무엇을 정해 주면 되는지

모든 스타일이 같은 단계를 거칩니다. Claude가 단계마다 결과를 보여 주고 필요한 것만 묻습니다.

| 단계 | Claude가 하는 일 | 사람이 할 일 |
|---|---|---|
| 시작 | 영상 등록(`job.py new … --style <스타일>`), 작업 공간 준비 | **스타일 정하기** (말하지 않으면 묻거나 감사일기) |
| ① 전사 | 말을 단어 단위 시간과 함께 받아쓰고, 항목·다시 말한 곳·잘못 들린 단어를 정리 (`edit/<id>/transcript.md`) | — |
| ② 훅 | 첫 3초에 올릴 문장 후보 3개 제안 | **하나 고르기** |
| ③ 컷 | 남길 문장·뺄 문장·최종 길이를 담은 컷 계획 | **계획 승인** (길이가 넘치면 속도·줄일 곳 선택) |
| ④ 자막·썸네일 | 잘못 들린 단어 고치기, 썸네일 장면·문구 후보 | **썸네일 고르기**, 문구·위치 수정 요청 |
| ⑤ B-roll | 사진마다 얼굴 블러, 어느 말에 어떤 사진을 띄울지 계획 | **계획 승인**, 본인 얼굴인지 애매하면 답하기 |
| ⑥ 효과음 | 새 효과음은 미리 듣기 파일로 먼저 보여 줌 | **소리 확인** |
| ⑦ 렌더 | 렌더 → 스틸·얼굴 검수 → −14 LUFS 마스터링 → Mac `out/<id>/` 로 전달 | **완성본 보고 피드백** |

- 피드백은 자연스럽게 말하면 됩니다. 예: "17초쯤 더듬은 곳 빼줘", "모임 사진도 넣어줘", "뽁 소리로 바꾸고 말 시작에 넣어줘".
- 피드백 중 다음 영상에도 적용할 것은 그 스타일의 `README.md`·`config.json` 에 기본값으로 남깁니다.
- 한 단계만 다시: "2026-10-06 자막만 다시 해줘", "썸네일 다른 장면으로".
- 진행 상황은 `python3 tools/job.py status <id>` 또는 `edit/<id>/pipeline.json` 에서 볼 수 있습니다.

### 결과물 (`out/<id>/`)
- `<id>.mp4` — 편집 완료 영상 (1080×1920, −14 LUFS). Mac으로 보낼 때 약 3.6Mbps(1분에 약 25MB)로 다시 압축합니다. 인스타가 어차피 다시 압축하므로 화질 차이는 거의 없습니다.
- `thumbnail.jpg` — 고른 썸네일. 영상과 별개 파일이고, 업로드할 때 커버로 직접 고릅니다. (`thumbnail_1~3.jpg` 는 후보)

---

## 3. 자주 생기는 문제 (공용)

스타일 전용 문제는 각 스타일 README 에 있습니다 (감사일기: [styles/gratitude/README.md](styles/gratitude/README.md#자주-생기는-문제-감사일기)).

| 증상 | 원인과 해결 |
|---|---|
| 전사 단계에서 한참 멈춤 | 첫 실행 때 음성 인식 모델(약 1.5GB) 다운로드이거나, 원격 세션 담당자가 명령 전에 시간을 쓰는 경우. A 방식에서는 `tools/vm_transcribe.sh <id>` 가 1분 조각으로 이어서 받아씁니다. Mac 터미널에서 직접: `python3 tools/plug.py rm transcribe edit/<id> footage/<id>/main.MOV --language ko --model medium` |
| Claude가 "파일을 가져올 수 없다(로그인 만료)"고 함 | Mac의 Claude 데스크톱 앱에 로그인 안내가 떠 있음 → 다시 로그인. 알림이 없으면 잠시 뒤 다시 시도 |
| 자막에 같은 말이 두 번 나옴 / "바로 가능 내일 가능"처럼 더듬은 게 남음 | 음성 인식이 다시 말한 부분을 한 단어로 뭉친 것. 1초 넘게 늘어진 단어 주변을 5초 이하로 다시 받아써서 찾아 뺍니다 |
| 피크가 −1dB를 넘어 마스터링 실패 | 효과음이 목소리와 겹친 것. `edit/<id>/sfx.json` 의 `below_voice_db` 를 18 정도로 |
| `kit.py update` 뒤 화면 모습이 원래대로 | 엔진을 업데이트하면 스타일 패치가 지워집니다 → `for r in styles/*/render.py; do python3 $r patch-kit; done` |

---

## 4. 구성

```
styles/<스타일>/       스타일 전용 — README(모습·결정) · config.json · thumb.json · render.py · references/
.claude/skills/        감독관(스타일별 <스타일>-reels) · faceblur(공용)
.claude/agents/        담당자 7명 (공용)
tools/                 공용 도구
CLAUDE.md              Claude가 읽는 공용 규칙 — 클라우드 세션 준비, 단계별 요령, 모든 스타일의 사용자 결정
```

| 공용 도구 | 역할 |
|---|---|
| `tools/plug.py` | 플러그인 찾기·점검(`doctor`)·IT Reelsmaker 스크립트 실행 |
| `tools/job.py` | 영상 등록(`--style`), 단계별 진행 상태 |
| `tools/faceblur.py` | 얼굴 검출(YuNet)·트래킹·블러·확인 시트 |
| `tools/thumbs.py` | 썸네일 문구 얹기 + 비교 시트 — 영상 스타일의 `thumb.json` 을 읽음 |
| `tools/subs_preview.py` | 렌더 전 자막 끊김 미리보기 |
| `tools/sfx.py` | 효과음 합성 (whoosh·pop·ding·rise + 키보드 타닥 4종·마우스 딸깍) |
| `tools/fonts.py` | 영상 안 폰트 지정 |
| `tools/cloud_bundle.sh` | (A 방식, Mac 쪽) 툴킷·개인 파일·영상을 `_bundle/cloud.tgz` 하나로 묶기 |
| `tools/cloud_setup.sh` | (A 방식, 클라우드 쪽) 묶음 풀기부터 렌더 준비·모든 스타일 패치·점검까지 한 번에 |
| `tools/vm_transcribe.sh` / `.py` | (A 방식, Mac 쪽) Mac에 받아 둔 모델로 전체 전사 (1분 조각으로 이어서) |
| `reel-defaults.json`, `it-reelsmaker.json` | IT Reelsmaker 프로젝트 설정 (영상별 `edit/<id>/reel.json` 이 덮어씀) |

### 폴더
```
footage/<id>/main.*        메인 영상          footage/<id>/broll/      B-roll 원본 → broll_blur/ 블러본
edit/<id>/                 작업 폴더(스타일·전사·컷·자막·B-roll 계획·효과음·진행 상태)
out/<id>/                  결과물              reels/                   렌더 엔진(Remotion, 모든 스타일 공용, git 에 없음)
brands/majunge/            브랜드(색·폰트)      assets/                  폰트·효과음·음악·얼굴 모델 (공용)
```
`footage/`, `edit/`, `out/`, `reels/`, `brands/`, `_bundle/`, 폰트·모델·효과음 파일은 개인 자료라 git 에 올리지 않습니다.

## 참고
- 레퍼런스: [choigpt-ai/retention-shorts](https://github.com/choigpt-ai/retention-shorts) — 구간 선정·세이프존 검수 발상
- 편집 엔진: [IT Reelsmaker](https://github.com/itpartypattaya/reels-montage) (MIT), [Social Media Skills](https://github.com/social-media-skills/skills), [ffmpeg-llm](https://github.com/rendi-api/ffmpeg-llm) (MIT)
- 얼굴 검출 모델: OpenCV Zoo YuNet
