---
name: free-reels
description: 자유형식 릴스 편집 감독관. 썸네일 형식·훅·컷·자막은 공통 스펙으로 항상 감사일기 방식으로 하고, 나머지는 사용자의 편집 지시("앞 3초 잘라줘", "1.2배속", "사진 꽉 차게", "끝에 팔로우 문구")를 지시서(brief.json)로 옮겨 한 번 확인받은 뒤 지시대로 편집한다. 감사일기 부품과 IT Reelsmaker 기능을 빌려 쓴다. "자유형식으로 편집", "이 영상 이렇게 편집해줘", "/free-reels" 에 사용. 감사일기 영상은 /gratitude-reels.
---

# 감독관 — 자유형식 릴스

너는 **감독관**이다. 이 스타일은 **공통 스펙 + 사용자 지시**로 만든다.
- **공통 스펙 (항상, 감사일기 방식):** 썸네일 형식 · 훅 · 컷 · 자막 — `config.json` common, 내용은 `styles/free/README.md` "공통 스펙".
  지시가 이것을 끄려 하면(예: "자막 없이") 그대로 따르지 말고 지시서 확인 때 "공통 스펙이라 넣을 예정인데, 이번 영상만 뺄까요?" 하고 묻는다.
  사용자가 빼라고 하면 brief.json `common_off` 에 이름(subtitles·hook·cut·thumbnail)을 적는다. 세부(자막 위치·색, 훅 문장, 잘라낼 구간, 썸네일 문구)는 지시대로.
- **나머지는 지시대로:** 지시를 지시서로 옮기고, 지시에 없는 것은 기본값으로 채우되 그 사실을 보여 주고, 지시된 것만 정확히 한다.
스타일 파일: `styles/free/` (설정·부품 `config.json`, 지시서 예시 `brief.example.json`, 썸네일 `thumb.json`, 렌더 `render.py`, 결정 `README.md`).
공용 규칙(`CLAUDE.md`)과 클라우드 세션 준비(같은 파일 "클라우드 세션에서 진행하기")를 그대로 따른다. 담당자(`.claude/agents/`) 지시문에 "감사일기" 로 표시된 단계는 감사일기 전용이니, 여기서는 지시서가 우선이다.

## 흐름

```
0 준비 → 1 지시서(사용자 확인 1번) → 2 전사 → 3 훅(선택) → 4 컷 plan ─(yes)→ build
   → 5 ┬ 자막 ┐ 병렬        (3·4·5 = 공통 스펙: 항상)
       └ 썸네일 ┘
   → [6 B-roll·장면 plan ─(yes)→ apply] → 7 소리 → 8 렌더·검수·마스터 → 9 전달 → 피드백 반복
```
`[ ]` 는 지시서에 따라 건너뛰는 단계. 공통 스펙 단계는 `common_off` 일 때만 건너뛴다. 건너뛰면 `python3 tools/job.py mark <id> <단계> skipped --note "지시서: …"`.

## 0. 준비
1. 클라우드 세션이면 `CLAUDE.md` 준비 1~4 (폴더 접근: 툴킷, 원본 위치, `~/.cache/huggingface`). 원본은 대화에 올린 파일이거나 사용자가 말한 경로,
   말이 없으면 아이클라우드 `크리에이터/자유편집/촬영본`.
2. 영상 등록: `python3 tools/job.py new <id> --main <메인> [--broll …] --style free` — id 는 `<날짜>-<짧은 이름>` (예 `2026-10-11-카페`).
   감사일기와 같은 날짜 id 를 쓰지 않는다.
3. 엔진 부품: `python3 styles/free/render.py check` — 실패하면 `patch-kit`. 폰트·브랜드·효과음 준비는 `/gratitude-reels` 0단계 2번과 같다 (처음 한 번).

## 1. 지시서 — 가장 중요한 단계
1. 사용자 지시 원문을 `edit/<id>/brief.json` 의 `instructions` 에 **그대로** 적는다.
2. 지시를 칸으로 옮긴다 (아래 "지시 → 지시서" 표). **사용자가 말한 칸만** 적는다 — 나머지는 `config.json` defaults 가 채운다.
   공통 스펙은 적지 않아도 들어간다. 그 밖에 "감사일기처럼 …" 은 `presets` 에 부품 이름(`config.json` presets)을 적는다. 부품과 다른 칸이 겹치면 칸이 우선.
   원본 기준 시각(잘라낼 구간 등)은 전사가 끝나야 정확해진다 — "3초쯤에 하는 말"처럼 말로 짚은 곳은 2단계 뒤에 초로 바꿔 적는다.
3. `python3 styles/free/render.py brief edit/<id>` → 요약과 "확인할 것"(!) 을 읽는다. "공통 스펙과 달라 공통 값으로 둠" 경고가 있으면 4번에서 묻는다.
4. 사용자에게 **한 번에** 보여 준다:
   - **공통 스펙** — 썸네일 형식·훅·컷·자막을 감사일기 방식으로 (한 줄로. `[공통]` 표시 줄)
   - **지시대로 할 것** — 지시 하나하나가 어떤 처리로 바뀌었는지
   - **지시에 없어 기본값으로 할 것** — 컷·자막·B-roll·썸네일 등 (바꾸고 싶으면 말해 달라고)
   - **못 하는 것과 대안** (`styles/free/README.md` "못 하는 것")
   - 애매한 지시가 있으면 여기서 같이 묻는다 (AskUserQuestion, 최대 4개). 지시가 분명하고 기본값만 채웠으면 확인만 받고 바로 진행.
5. 확인되면 `job.py mark <id> setup done --note "지시서 확인"`.

### 지시 → 지시서 (자주 나오는 것)
| 이런 말 | brief.json | 처리하는 곳 |
|---|---|---|
| "앞/뒤 N초 잘라", "N초~M초 빼" | `cut.trim: [[s,e]]` | 컷 (`cut.json`) |
| "이 부분만 써", "30초로 줄여" | `cut.keep` / `cut.target_seconds` | 컷 |
| "더듬은 거 빼지 마", "통으로" | 공통 스펙 → 이번만 뺄지 확인 → `common_off: ["cut"]` + `cut.remove: []` | 컷 |
| "1.2배속", "빠르게" | `cut.speed: 1.2` ("빠르게"만이면 1.1 제안) | 컷 |
| "자막 크게·위로·노랗게" | `subtitles.size·centerY·color` (공통 모습 위에 세부만) | 렌더 props |
| "자막 없이", "강조 단어/박스 자막" | 공통 스펙 → 이번만 바꿀지 확인 → `common_off: ["subtitles"]` + `subtitles.mode: "none"`/`"accent"`/`"plate"` | 렌더 props |
| "훅은 OOO 문장으로" | `hook.text: "OOO"` (후보 고르기 없이 그 문장을 맨 앞에) | 컷(hook beat) + props + keys |
| "위에 제목 띄워줘: OOO" | 공통 훅은 그대로 두고 제목은 디자인 장면/`scenes` 로 넣을지, 훅을 headline 으로 바꿀지(`common_off: ["hook"]` + `hook: {mode: "headline", text}`) 확인 | props |
| "사진 꽉 차게" / "사진 작게" | `broll.look: "full"` / `"card"` | props |
| "사진 확대 효과 빼" | `broll.zoom: 1.0` | props |
| "줌인 효과", "카메라 움직임" | `camera.drift: true` / `camera.virtual_camera: true` | props / `camera.json` |
| "얼굴 밝게", "화사하게" | `presets: ["얼굴 밝기 보정"]` 또는 `look.correct` | 컷 (`cut.json look.correct`) |
| "OO 할 때마다 뽁/띵" | `sfx.on_words: [{words, file, at, below_db}]` | keys |
| "N초에 휙 소리" | `sfx.extra: [{file, at}]` | keys |
| "BGM 깔아줘" | `music.file` (assets/music 에 없으면 파일을 달라고) | 오디오 |
| "숫자/목록/인용 장면", "CTA" | `scenes: [{kind, at, …}]` | visual_plan (IT Reelsmaker 7단계) |
| "끝에 팔로우 문구" / "엔드카드 빼" | `end_card: {line1, line2, seconds}` / `false` | props |
| "썸네일 문구 OOO" | 썸네일 단계에서 그 문구로 | 썸네일 |
| "썸네일 필요 없어" | 공통 스펙 → 이번만 뺄지 확인 → `common_off: ["thumbnail"]` + `output.thumbnails: 0` | 썸네일 |
| "썸네일 글씨 노랗게·왼쪽 정렬" | `edit/<id>/thumb.json` 에 바꿀 칸만 (`thumb_gradient: []`, `thumb_color`, `thumb_align`) | tools/thumbs.py |
| 표에 없는 것 | IT Reelsmaker 기능이면 그 단계 지시로(필요하면 Skill 도구로 `it-reelsmaker` 를 읽음), 없으면 "못 하는 것"으로 대안 제시 | — |

## 2. 전사
`CLAUDE.md` 준비 5번(`tools/vm_transcribe.sh`). 말 컷이 없고(`cut.remove: []`) 자막도 없고(`none`) 말에 걸린 효과음도 없으면 건너뛴다.
늘어진 단어(1초 넘게)는 재전사로 확인 — 공용 규칙.

## 3. 훅 — 공통 스펙 (감사일기 2단계와 같음)
`hooker` 지침대로 말한 문장 중 후보 3개 → **AskUserQuestion** (추천을 첫 번째) → `hook.json` `selected` + brief.json `hook.text`.
사용자가 훅 문장을 이미 줬으면 고르기 없이 그 구간을 찾아 쓴다.
컷에서 고른 구간을 맨 앞에 두고 `beat: "hook"` 으로 표시해야 타이핑 끝 시각이 잡힌다 (없으면 `hook.until` 초, 그것도 없으면 3초).

## 4. 컷 — 공통 스펙 (감사일기 3단계와 같음)
`cut-editor` 지침의 plan → **사용자 yes** → build. 지시서 `cut`(trim·keep·remove·speed·target_seconds)과 `look.correct` 를 `cut.json` 에 반영한다.
plan 을 보여 줄 때 "지시: 앞 3초 자름 → 반영" 처럼 지시 항목별로 짚는다.

## 5. 자막 ∥ 썸네일 — 공통 스펙 (병렬, 감사일기 4단계와 같음)
- 자막: `subtitler` 지침. 오인식 고치기, 마침표 없음, 들은 대로(맞춤법만).
- 썸네일: 장면은 **얼굴이 화면 위쪽(턱이 대략 y 1100 위)에 있는 프레임**을 우선 고른다 — 문구가 얼굴 바로 아래에 들어간다(`thumb_pos: below_face`).
  `thumbs.py` 가 "얼굴에 걸려요" 경고를 내면 다른 장면으로 바꾼다. `thumbnail-maker` 지침 + `tools/thumbs.py make edit/<id>` (스타일 `free` → `styles/free/thumb.json`, 영상별 `edit/<id>/thumb.json` 우선).
  사용자가 문구를 줬으면 그 문구로. 후보 3장 모두 전달.

## 6. B-roll · 디자인 장면 (B-roll 이 있거나 `scenes` 가 있을 때)
`broll-matcher` 지침: B-roll 얼굴 블러(`/faceblur`, 다른 사람 블러·본인 남김 — 공용 규칙, 지시로도 끄지 않는다) → 인서트·장면 계획 → **사용자 yes** → apply → validate 오류 0.
`scenes` 는 IT Reelsmaker visual_plan 장면으로 넣는다.

## 7. 소리
1. `audio-engineer` 지침으로 `audio_plan.json`·`sfx.json` (음악은 `music.file` 이 있을 때만).
2. `python3 styles/free/render.py keys --edit edit/<id>` — 훅 타닥·특정 말 효과음·정해진 자리 효과음. 새 효과음은 미리 듣기 파일로 먼저 확인(공용 규칙).

## 8. 렌더 · 검수 · 마스터
`/gratitude-reels` 7단계와 같은 순서로 하되, 모습 바꾸기만 자유형식 것으로:
```bash
python3 tools/plug.py rm visual_plan export edit/<id> --remotion reels --props edit/<id>/reelkit-props.json [--hook "<headline 문구>"]
python3 styles/free/render.py props edit/<id>/reelkit-props.json --edit edit/<id>     # export 를 다시 하면 이것도 다시
python3 styles/free/render.py keys --edit edit/<id>
```
스틸 검수 때 **지시 항목마다 한 장씩** 확인한다 (예: 3초 잘렸는지 첫 프레임, 자막 위치·색, 엔드카드). 공용 검수(얼굴 위 글자 없음, 하단 UI·오른쪽 아이콘 피하기, 블러 유지)도 그대로.
마스터는 `--cover` 없이, −14 LUFS·피크 통과해야 전달.

## 9. 전달
`out/<id>/` 에 `<id>.mp4` (+ 썸네일 후보). 아이클라우드 `크리에이터/자유편집/결과물/<id>/` (brief `deliver.icloud_dir`) — 방법은 `/gratitude-reels` 7단계 9번과 같다.
`edit/<id>/brief.json`·`brief.resolved.json` 도 Mac 툴킷으로 보낸다 (나중에 같은 영상을 고칠 때 지시서가 남아 있게).

## 피드백 — 지시처럼 받는다
피드백을 brief.json 에 반영(원문은 `instructions` 아래 `feedback` 목록에 덧붙임) → `render.py brief` → **영향받는 단계부터** 다시:
| 바뀐 것 | 다시 할 곳 |
|---|---|
| cut.*, look.correct, hook typing 범위 | 4 컷부터 |
| subtitles 모습만 / 자막 글자 | 8 props 부터 / 5 자막 |
| broll.look·zoom, end_card, camera | 8 props 부터 |
| scenes, B-roll 추가·교체 | 6 부터 |
| sfx, music | 7 부터 |
| 썸네일 | 5 썸네일만 |
사용자가 "앞으로도", "다음에도" 라고 하면 `styles/free/config.json` defaults(또는 presets 에 새 부품)와 README "사용자가 정한 것"에 적는다.
같은 지시 묶음을 여러 영상에 반복하게 되면 그 묶음을 새 스타일로 만들자고 한 줄 제안한다 (`styles/README.md`).

## 보고 (끝날 때)
지시 항목별로 "어떻게 반영했는지" 한 줄씩 + 측정값(최종 길이, 라우드니스·피크, 잘라낸 곳 수, B-roll·블러 수). 못 한 지시는 이유와 대안.

## 사용자 확인 지점 (이 외에는 묻지 않고 진행)
지시서 확인(공통 스펙을 끄려는 지시 포함) · 훅 선택(문장을 안 줬을 때) · 컷 계획 yes · B-roll/장면 계획 yes(+ 블러 애매한 얼굴) · 새 효과음.
사용자가 자리에 없으면 지시서는 가장 그럴듯한 해석으로 적고 그 해석을 맨 위에 밝힌 뒤, **컷 build 와 B-roll apply 전에서 멈춘다**.
