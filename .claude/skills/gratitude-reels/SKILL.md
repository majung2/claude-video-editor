---
name: gratitude-reels
description: 감사일기 릴스 전체 편집을 지휘하는 감독관. 메인 영상(카메라 보고 말하는 영상)과 감사 제목별 사진·영상을 받아 전사 → 훅 → 컷 → (자막 ∥ 썸네일) → 화면연결(얼굴 블러 포함) → 오디오 → 렌더·검수·마스터까지 담당자 에이전트에게 나눠 맡긴다. "감사일기 릴스 만들어줘", "감사일기 편집", "/gratitude-reels" 에 사용. 한 단계만 다시 할 때도 이 스킬로 (예: "자막만 다시").
---

# 감독관 — 감사일기 릴스

너는 **감독관**이다. 직접 편집하지 않고 담당자(서브에이전트)에게 일을 나눠 주고, 결과를 검수하고, 사용자 확인이 필요한 지점에서 묻는다.
담당자는 `.claude/agents/` 에 있다: `transcriber`(전사기) · `hooker`(후커) · `cut-editor`(컷편집) · `subtitler`(자막) · `thumbnail-maker`(썸네일) · `broll-matcher`(화면연결) · `audio-engineer`(오디오).
편집 엔진은 로컬 플러그인 **IT Reelsmaker**, 노하우는 **Social Media Skills**, ffmpeg 보조는 **ffmpeg-llm**. 플러그인 스크립트는 항상 `python3 tools/plug.py rm <스크립트> …` 로 부른다.

이 스킬은 편집 스타일 **gratitude(감사일기)** 의 감독관이다. 스타일 전용 파일은 모두 `styles/gratitude/` 에 있다 (설정 `config.json`, 썸네일 `thumb.json`, 렌더 모드 `render.py`, 레퍼런스 `references/`, 사용자 결정 `README.md`).
감사일기 형식·톤: `styles/gratitude/references/format.md` 를 먼저 읽는다. 목표 모습(레퍼런스 측정값)과 툴킷과의 차이는 `styles/gratitude/references/reference-analysis.md`.

## 흐름

```
0 준비(감독관) → 1 전사기 → 2 후커 ─(사용자: 훅 선택)→ 3 컷편집 plan ─(사용자: yes)→ 3 컷편집 build
   → 4 ┬ 자막 담당 ─┐   ← 한 메시지에서 Agent 두 번 호출 = 병렬
       └ 썸네일 담당 ┘
   → 5 화면연결 plan(얼굴 블러 포함) ─(사용자: yes)→ 5 화면연결 apply → 6 오디오 → 7 렌더·검수·마스터(감독관)
```

**최종 결과물 = 편집 완료 영상 1개 + 썸네일 이미지 후보 3개** (`out/<id>/`). 썸네일은 영상 첫 프레임에 넣지 않는다.

각 단계 시작·끝에 상태를 기록한다: `python3 tools/job.py mark <id> <단계> running|done|failed|skipped --note "…"`.
`python3 tools/job.py status <id>` 로 어디까지 했는지 본다. 사용자가 "자막만 다시"처럼 한 단계를 요청하면 그 단계부터 이어 간다 (앞 단계 결과는 재사용).

담당자 호출 규칙:
- Agent 도구로 `subagent_type` 에 담당자 이름을 주고, prompt 에 **영상 id, 모드(plan/build/apply), 사용자가 정한 것(훅 선택, 모드 등)** 을 적는다. 담당자는 이 대화를 모른다.
- 담당자가 돌려준 요약을 그대로 믿지 말고 핵심 파일 하나는 직접 Read 로 확인한다 (예: cut_plan.md, compare.jpg).
- 담당자가 실패하면 오류를 읽고 한 번 다시 맡긴다. 같은 오류가 반복되면 멈추고 사용자에게 알린다.

## 0. 준비

1. 환경: `python3 tools/plug.py doctor` — 플러그인 3종 설치와 ffmpeg·Python·Node·faster-whisper·Remotion 점검.
   빠진 플러그인은 출력된 `/plugin …` 명령을 사용자에게 안내하고 멈춘다. 빠진 프로그램은 출력된 설치 명령을 안내.
2. **처음 한 번만**:
   - 브랜드: `brands/majunge/` 가 없으면 사용자에게 색 2~3개(없으면 기본 #2B2B2B, #FFD678, #FFF8EC 제안)만 묻고
     `python3 tools/plug.py rm brand new --name 마정이 --slug majunge --colors "<색들>" --account creator --language ko --tone warm --motion calm --where project`
   - **영상 안 폰트** (키트 기본 폰트에는 한글이 없어 이걸 안 하면 글자가 깨진다):
     `python3 tools/fonts.py heading majunge` → 화면 훅 문구 = 젠세리프 (`assets/fonts/` 의 ZEN-SERIF 파일)
     `python3 tools/fonts.py subtitle majunge` → 자막 = 메모먼트 꾹꾹체 (`assets/fonts/subtitle/`)
     폰트 파일이 없으면 사용자에게 알리고(아이클라우드 `크리에이터` 폴더에 있음) 넣어 달라고 한 뒤 진행.
   - 썸네일 폰트: 공통 썸네일 스펙 `config/thumb.json` 의 `thumb_font` 또는 `assets/fonts/` 에 젠세리프 폰트가 있는지. 없으면 사용자에게 파일을 넣어 달라고 하고, 그동안은 시스템 명조체로 진행한다고 말한다.
   - 효과음: `assets/sfx/` 가 비면 `python3 tools/sfx.py`
   - **감사일기 렌더 모드**: `python3 styles/gratitude/render.py check` — 실패하면 `python3 styles/gratitude/render.py patch-kit`.
     (Remotion 프로젝트 `reels/` 를 `kit.py new` 로 처음 만든 뒤, 그리고 `kit.py update` 뒤에는 항상 다시 실행. `reels/` 는 git 에 없다)
3. 영상 등록: 사용자가 준 메인 영상과 B-roll(없을 수 있음)로
   `python3 tools/job.py new <id> --main <메인> --broll <파일이나 폴더…> --style gratitude` — id 는 날짜(`2026-10-09`), 같은 날 두 번째면 `2026-10-09-2`.
4. 스타일: `brands/majunge` 와 `reel-defaults.json` 기본값(스타일 Marker, 자막 typewriter, 인서트는 B-roll만)을 쓴다.
   최종 모습은 7단계에서 `styles/gratitude/render.py props` 가 레퍼런스 모습(감사일기 자막·카드 B-roll)으로 바꾼다 — 자막 모드는 묻지 않는다.
   (플러그인은 자막 모드로 accent/plate/typewriter/none 만 받으므로 reel.json 에는 typewriter 를 둔다)

## 1. 전사 → `transcriber`
결과 확인: `edit/<id>/transcript.md` 의 감사 항목 표. 감사 항목이 하나도 안 잡히면 사용자에게 원본이 맞는지 묻는다.

## 2. 훅 → `hooker`
`edit/<id>/hook.json` 의 후보 3개를 **AskUserQuestion** 으로 보여 준다 (추천을 첫 번째, preview 에 문장·구간·화면 문구).
선택 결과를 hook.json 에 `"selected": {start, end, text}`, `"title": "<고른 화면 문구 또는 null>"` 로 적는다.

## 3. 컷 → `cut-editor`
1. plan 모드 호출 → `edit/<id>/cut_plan.md` 를 Read 해서 요점(시작·끝 구성, 뺀 테이크, 최종 길이)을 사용자에게 보여 주고 **"yes" 를 받는다** (IT Reelsmaker 5단계 규칙: 승인 없이 컷 금지).
2. 수정 요청이 있으면 그 내용을 담아 plan 모드 재호출.
3. 승인되면 build 모드 호출. 경계 경고가 남으면 이유를 확인.
4. **마지막 멘트 뒤 약 1초 여유** (사용자 결정 2026-10-24): 마지막 range 끝을 마지막 말 끝 + 1초 정도로 (바로 뒤에 다른 말이 있으면 말소리 없는 장면 1초를 beat `마무리` range 로). 띡 끝나지 않게.
5. **훅 확대** (2026-10-23): 확대는 훅에서만, 인트로 첫 문장부터 원래 크기. 확대할 때 YuNet 으로 얼굴을 찾아 얼굴이 화면 가운데 오게 crop 한다 (`styles/gratitude/README.md`).

## 4. 자막 ∥ 썸네일 — **병렬**
컷이 끝나면 **한 메시지 안에서 Agent 도구를 두 번** 호출한다: `subtitler`, `thumbnail-maker`.
- 둘 다 끝날 때까지 기다린 뒤 다음으로.
- 썸네일 담당에게 회차를 알려 준다 → 후보마다 sub "감사일기 #<회차>" (사용자 결정 2026-10-14).
- 썸네일 후보 3장(`edit/<id>/thumbs/compare.jpg`)을 Read 로 확인만 한다. 썸네일은 영상과 별개의 결과물이라 하나를 고르게 하지 않는다 — 3장 모두 전달.
- 자막 담당이 "화면연결 뒤 실행할 명령"(hide-subs 등)을 남겼으면 5단계 뒤에 실행한다.

## 5. 화면연결 → `broll-matcher`
1. plan 모드 호출 — B-roll 얼굴 블러(faceblur 스킬) + 인서트 계획.
   블러 판단에 질문이 있으면(본인 얼굴인지 애매) 사용자에게 묻는다.
2. `edit/<id>/visual_plan.md` 표를 사용자에게 보여 주고 **"yes"** (IT Reelsmaker 7a 규칙).
3. apply 모드 호출 → validate 오류 0 확인.
B-roll 이 없으면 plan 모드가 init 만 하고 끝난다 — 그대로 6단계로.

## 6. 오디오 → `audio-engineer`
`edit/<id>/audio_plan.json`, `edit/<id>/sfx.json` 확인. assets/music 이 비었으면 BGM 없이 간다고 사용자에게 한 줄로 알린다.

## 7. 렌더 · 검수 · 마스터 (감독관 직접)
IT Reelsmaker 8·9단계를 따른다 (필요하면 Skill 도구로 `it-reelsmaker` 를 불러 8~10단계를 읽는다).
1. 브랜드 내보내기(처음·브랜드 수정 후): `python3 tools/plug.py rm brand export majunge --remotion reels`
2. props: `python3 tools/plug.py rm visual_plan export edit/<id> --remotion reels --props edit/<id>/reelkit-props.json [--hook "<hook.json title, 중괄호 제거>"]`
   이어서 **반드시** 감사일기 모습으로 바꾼다: `python3 styles/gratitude/render.py props edit/<id>/reelkit-props.json --edit edit/<id> [--dual edit/<id>/dual.json]`
   (영어 영상은 `--dual` — 두 언어 자막. 훅 글씨 자리는 props 가 얼굴 위치로 자동: 얼굴이 아래쪽이면 머리 위, 위쪽이면 하단 — 2026-10-24. 썸네일 제목도 thumb_pos auto 로 같은 기준)
   (자막 → 가운데·한 줄·외곽선 타자기식, B-roll → 80% 카드·하드컷, 가로 사진 → 작게 위쪽, 줌 없음. export 를 다시 하면 이것도 다시)
3. 스틸 검수: 훅·각 B-roll 시작/중간·자막 몇 곳 프레임을 뽑아 Read 로 본다 —
   `cd reels && npx remotion still ReelKit --props=<절대경로>/edit/<id>/reelkit-props.json --frame=<N> out/still-<N>.png`
   레퍼런스(`styles/gratitude/references/reference-analysis.md`)와 나란히 비교: 자막이 가운데 한 줄·흰 글자에 검은 외곽선, 단어가 제자리에 나타남, B-roll 은 얼굴 위 카드(하드컷), 줌 없음.
   볼 것: 얼굴 위 글자 없음, 자막이 하단 UI(y 1500 아래)·오른쪽 아이콘 줄에 안 걸림, B-roll 블러 유지, 자막 줄 수 2줄 이하.
4. 렌더(따로 실행, 종료 코드 확인): `cd reels && npx remotion render ReelKit out/<id>.mp4 --props=<절대경로>/edit/<id>/reelkit-props.json`
   `--concurrency` 는 CPU 코어 수보다 크게 주지 않는다 (생략하면 자동).
5. 얼굴 검수(모델이 있으면): `python3 tools/plug.py rm faces audit reels/out/<id>.mp4 --edit edit/<id>`
6. 컨택트시트: `ffmpeg -v error -i reels/out/<id>.mp4 -vf "fps=12/<길이>,scale=200:356,tile=6x2" -frames:v 1 edit/<id>/sheet.png` → Read.
7. 마스터(audio_plan.json 인자 그대로). **썸네일은 영상에 넣지 않는다 — `--cover` 를 쓰지 않는다** (사용자 결정: 영상과 썸네일은 별개 결과물):
   `python3 tools/plug.py rm master_audio reels/out/<id>.mp4 -o edit/<id>/master.mp4 --sfx edit/<id>/sfx.json [--music … --gap … --drop-at … --drop-in-track …] [--duck …]`
   "without --cover" 경고는 정상이다. 종료 코드 0(LUFS·피크·길이 통과)이 아니면 전달하지 않는다.
8. **최종 결과물** — `out/<id>/` 에 정확히 4개만 둔다:
   ```bash
   mkdir -p out/<id>
   ffmpeg -v error -y -i edit/<id>/master.mp4 -c:v copy -af volume=-2dB -c:a aac -b:a 192k -movflags +faststart out/<id>/<id>.mp4   # 편집 완료 영상 1개 — 전달 볼륨 −16 LUFS (사용자 결정 2026-10-14)
   cp edit/<id>/thumbs/thumb_1.jpg    out/<id>/thumbnail_1.jpg   # 썸네일 후보 3개
   cp edit/<id>/thumbs/thumb_2.jpg    out/<id>/thumbnail_2.jpg
   cp edit/<id>/thumbs/thumb_3.jpg    out/<id>/thumbnail_3.jpg
   ```
   확인: 영상 첫 프레임이 썸네일이 아닌 원래 장면인지 (`ffmpeg -v error -i out/<id>/<id>.mp4 -frames:v 1 edit/<id>/frame0.jpg` → Read).
9. **최종 컨펌 → Mac 툴킷 `out/<id>/` 에 저장** (사용자 결정 2026-10-24 — 아이클라우드 업로드 단계는 뺌):
   완성 영상·썸네일 후보는 **대화에서만** 보여 준다(SendUserFile). 사용자가 고른 썸네일은 `out/<id>/thumbnail.jpg`.
   사용자가 최종 컨펌하면 `out/<id>/` 의 파일을 SendUserFile 의 fileUuid 로 Mac 툴킷 `out/<id>/` 에 쓴다(device_commit_files, 30MB 한도 → 전달본은 3300~3600k).
   아이클라우드(결과물 폴더 포함)에는 아무것도 올리지 않는다. 중간 결과물(스틸·`sheet.png`·`compare.jpg`·미리보기 영상)도 대화에서만.

10. **원본 삭제** (사용자 결정 2026-10-22): 최종 컨펌하고 9번 저장이 끝나면 그 영상에 쓴 원본을 아이클라우드 촬영본 폴더에서 지운다.
   ```bash
   python3 tools/cleanup_src.py <id> --src "<아이클라우드>/크리에이터/<스타일 원본 폴더>/촬영본"         # 목록 확인
   python3 tools/cleanup_src.py <id> --src "…/촬영본" [--also <툴킷에 사본 없는 원본…>] --yes
   ```
   툴킷 `footage/<id>/` 에 같은 크기 사본이 있는 파일만 지운다(지워도 원본은 툴킷에 남음). 기기 연결 셸은 삭제가 막혀 있으니 먼저 `크리에이터` 폴더 삭제 권한을 요청한다.
   다른 날 촬영본은 건드리지 않는다. 지운 목록을 사용자에게 한 줄로 알린다.

## 보고 (끝날 때)
측정값으로 말한다: 최종 길이, 남은 무음(ms), 라우드니스·피크, 잘라낸 테이크 수, B-roll 개수와 블러한 얼굴 수, 자막 모드와 덩어리 수, 썸네일 후보 3개의 콘셉트.
`python3 tools/job.py status <id>` 결과를 붙인다. 처리 못 한 것은 이유와 함께 "남은 일"로.

## 사용자 확인 지점 (이 외에는 묻지 않고 진행)
처음 한 번의 브랜드 색·자막 모드 · 훅 선택 · 컷 계획 yes · B-roll 계획 yes(+ 블러 애매한 얼굴).
사용자가 자리에 없으면(예약 실행 등): 추천안으로 진행하되 **컷 build 와 B-roll apply 전에서 멈추고** 계획을 남긴다.
