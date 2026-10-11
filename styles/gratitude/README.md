# 감사일기 스타일 (`gratitude`)

카메라를 보고 그날의 감사한 일을 말하는 셀카 영상을 인스타 릴스로 만드는 스타일입니다.
레퍼런스 릴스 2개를 측정해서 맞춘 모습에, 10.6 감사일기를 편집하며 정한 것들을 더했습니다.

- 감독관 스킬: `/gratitude-reels` (`.claude/skills/gratitude-reels/SKILL.md`)
- 원본 폴더(아이클라우드): `크리에이터/감사일기/촬영본` → 결과물 `크리에이터/감사일기/결과물/<id>/`
- 영상 등록: `python3 tools/job.py new <id> --main <메인 영상> --broll <사진…> --style gratitude`

## 기본 모습

| 항목 | 모습 | 설정 위치 |
|---|---|---|
| 구성 | 훅 → "N일차 감사일기" 인트로 → 감사 항목들 → 마무리. 목표 40~45초, 60초까지 허용 | `references/format.md` |
| 훅 자막 | 위쪽 훅 문구 없이, 훅 문장을 썸네일과 같은 젠세리프·파스텔 그라데이션(색은 공통 썸네일 스펙 `thumb_gradient`)으로 **한 글자씩 타이핑**(기울기 없음) | `config.json` → `hook` |
| 말자막 | 메모먼트 꾹꾹체, 흰 글자 + 얇은 검은 외곽선, 화면 74.5% 높이 가운데 한 줄. 문장 자리를 먼저 잡고 단어가 제자리에 나타남. **마침표 없음** | `config.json` → `subtitles` |
| 컷 | 다시 말한 곳·더듬은 곳·같은 말 반복·긴 쉼은 전부 뺌. 속도 1.0 기본(길면 1.1) | 영상별 `edit/<id>/cut.json` |
| B-roll | 다른 사람 얼굴은 블러(본인은 남김). 세로 사진은 화면 80% 카드, 가로 사진은 머리 위쪽에 폭 80%. 천천히 1.05배까지 부드럽게 확대, 전환 효과 없음 | `config.json` → `card`, `pip`, `card_zoom` |
| 효과음 | 훅 한 글자마다 키보드 **타닥**(4가지 돌아가며), "감사합니다" 말 시작마다 **뽁**, 훅→인트로 rise, 감사 1 시작 pop | `config.json` → `sounds` |
| 소리 | −14 LUFS, 피크 −1dB 이하. 효과음은 목소리보다 18dB 아래(뽁만 6dB 아래). BGM은 `assets/music/` 에 곡이 있을 때만 | 영상별 `edit/<id>/sfx.json` |
| 썸네일 | 원본에서 고른 표정 좋은 장면(얼굴이 위쪽) + 공통 썸네일 스펙: 레퍼런스 'ENTP가 INFP를 좋아하는 이유' 모습 (공통 스펙 `config/thumb.json`, 2026-10-11): 젠세리프 크게(176px, 긴 줄은 폭에 맞춰 축소)·줄 간격 촘촘히(1.05)·**왼쪽 정렬**, **얼굴 바로 아래**(턱 아래 2.5%, 얼굴 자동 검출), 민트·크림·연분홍이 비스듬히 되풀이되는 펄 그라데이션, 도톰한 입체, 옅은 그림자, 오른쪽 2° 올라감, **굴곡은 왼쪽 아래에서 시작해 오른쪽 위에서 끝남**(반 물결, 세기 24), 글자 뒤 아래로 완만한 연한 그라데이션 | `config/thumb.json` (공통) |

## 사용자가 정한 것 (다음 영상도 그대로)
- 썸네일 문구: 공통 썸네일 스펙(`config/thumb.json`)을 따른다 — 왼쪽 정렬, 얼굴 바로 아래, 펄 그라데이션, 왼쪽 아래→오른쪽 위 굴곡. 강조색 없음. (2026-10-11 레퍼런스 반영, 10.7·10.8 썸네일 다시 만들어 확정. 예전 결정 '가운데 정렬'은 바뀜)
- 훅: 위쪽 훅 문구 없이, 훅 문장을 썸네일 스타일로 한 글자씩 타이핑(기울기 없음) + 글자마다 타닥 소리.
- 자막: 마침표 없음, 제자리 타자기(문장 자리를 먼저 잡고 단어가 나타남) 유지. 오인식은 `fix`/`fix_at`.
- B-roll 사진은 부드럽게 1.05배 확대.
- 얼굴 밝기 보정: 어두운 곳 위주로 살짝 밝게 — cut.json `look.correct` = `curves=all='0/0 0.25/0.31 0.5/0.58 0.75/0.81 1/1',eq=saturation=1.04` (10.7·10.8, 2026-10-10)
- 썸네일 글자 뒤: 아래쪽으로 길고 완만하게 어두워지는 연한 그라데이션(`thumb_shade_style: fade`, 최대 약 40%). 썸네일은 원본 전체(편집에서 잘린 장면 포함)에서 표정 좋은 장면을 골라 후보를 낸다
- 효과음: "감사합니다" 말 시작마다 뽁, 훅 타이핑 타닥. 마지막 "감사합니다"에 ding 없음, 감사 2·3 등장 pop 없음.

## 이 폴더

| 파일 | 내용 |
|---|---|
| `README.md` | 이 문서 — 스타일 소개, 기본 모습, 사용자 결정 |
| `config.json` | 자막·훅·B-roll 카드·효과음 기본값 (레퍼런스 측정값 + 결정) |
| `thumb.json` | `{"extends": "common"}` — 썸네일 문구 모습은 공통 스펙 `config/thumb.json`. 감사일기만 다르게 할 칸이 생기면 여기에 |
| `render.py` | 렌더 모드. `patch-kit`(엔진에 감사일기 자막·훅 타이핑·B-roll 카드·부드러운 확대를 덧붙임) · `check` · `props`(렌더 설정을 감사일기 모습으로) · `keys`(훅 타닥·감사합니다 뽁 효과음 배치) |
| `references/format.md` | 감사일기 형식·톤 — 편집 규칙 |
| `references/reference-analysis.md` | 레퍼런스 릴스 2개 측정값과 툴킷과의 차이 |

## 렌더 순서 (감독관 7단계)
```bash
python3 tools/plug.py rm visual_plan export edit/<id> --remotion reels --props edit/<id>/reelkit-props.json
python3 styles/gratitude/render.py props edit/<id>/reelkit-props.json --edit edit/<id>   # 감사일기 모습으로
python3 styles/gratitude/render.py keys --edit edit/<id>                                  # 훅 타닥·감사합니다 뽁
cd reels && npx remotion render ReelKit out/<id>.mp4 --props=<절대경로>/edit/<id>/reelkit-props.json
python3 tools/plug.py rm master_audio reels/out/<id>.mp4 -o edit/<id>/master.mp4 --sfx edit/<id>/sfx.json
```

## 자주 생기는 문제 (감사일기)
| 증상 | 원인과 해결 |
|---|---|
| 화면에 "ReelKit template" 글자 | 훅 문구가 비어 엔진 기본값이 나온 것. `render.py props` 를 거치면 꺼집니다 |
| B-roll 사진이 흔들림 | 예전 방식(미리 만든 확대 영상). 지금은 엔진이 직접 부드럽게 확대합니다 → `render.py patch-kit` |
| "감사합니다" 효과음이 안 들림 | 말 첫 음절과 겹쳐 묻힌 것. `config.json` 의 `click_below_db`(숫자가 작을수록 큼) |
| `kit.py update` 뒤 자막·카드 모습이 원래대로 | 엔진을 업데이트하면 패치가 지워집니다 → `python3 styles/gratitude/render.py patch-kit` |
