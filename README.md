# claude-video-editor — 감사일기 릴스 자동 편집

Claude Code에서 **감독관 1명 + 담당자 7명**이 역할을 나눠 감사일기 인스타 릴스를 편집합니다.
편집 엔진은 로컬 플러그인(IT Reelsmaker · Social Media Skills · ffmpeg-llm)을 쓰고, 이 저장소는 그 위에
역할 분담·감사일기 형식·얼굴 블러·썸네일 3안을 얹은 툴킷입니다.

```
메인 영상 + B-roll
  → 전사기 → 후커(훅 3초) → 컷편집(중복·무음 제거)
  → ┬ 자막 담당   ┐ 병렬
    └ 썸네일 담당 ┘
  → 화면연결(B-roll 얼굴 블러 → 감사 제목별 연결) → 오디오(효과음·BGM)
  → 감독관: 렌더 · 검수 · 마스터 → out/<id>/ (영상 1개 + 썸네일 후보 3개)
```

## 1. 설치 (처음 한 번)

1. 프로그램: ffmpeg, Python 3.9+, Node.js 18+
   ```bash
   brew install ffmpeg node        # macOS
   python3 -m pip install -r requirements.txt
   ```
2. Claude Code에서 플러그인 3개 설치:
   ```
   /plugin marketplace add itpartypattaya/reels-montage
   /plugin install it-reelsmaker@itparty
   /plugin marketplace add social-media-skills/skills
   /plugin install social-media-skills@social-media-skills
   /plugin marketplace add rendi-api/ffmpeg-llm
   /plugin install ffmpeg-llm@rendi-official
   ```
   IT Reelsmaker 설정을 물으면 project_root 는 이 폴더, remotion_dir 은 `<이 폴더>/reels` 로.
3. 점검: `python3 tools/plug.py doctor`
4. 폰트 (파일은 저장소에 올라가지 않음):
   - 자막: 메모먼트 꾹꾹체 파일을 `assets/fonts/subtitle/` 에
   - 썸네일: 젠세리프 폰트 파일을 `assets/fonts/` 에
   - 화면 훅 문구 등 제목: `python3 tools/fonts.py` (Pretendard, 자동 다운로드)
5. (선택) 배경음: 쓸 수 있는 음원을 `assets/music/` 에. 효과음은 `python3 tools/sfx.py` 로 기본 4종 생성.

브랜드 프로필과 Remotion 프로젝트는 첫 실행 때 감독관이 만들어 줍니다.

## 2. 사용

이 폴더에서 Claude Code를 열고:

```
/gratitude-reels  ~/Movies/감사일기/IMG_4821.MOV 이랑 ~/Movies/감사일기/broll 폴더로 오늘 감사일기 릴스 만들어줘
```

감독관이 묻는 것은 세 가지뿐입니다: **훅 선택 → 컷 계획 OK → B-roll 계획 OK**.
한 단계만 다시: "2026-10-09 자막만 다시 해줘", "썸네일 다른 장면으로 다시".
B-roll 블러만: `/faceblur`

결과 (`out/<id>/`):
- `<id>.mp4` — 편집 완료 영상 (1080×1920, −14 LUFS)
- `thumbnail_1.jpg` ~ `thumbnail_3.jpg` — 썸네일 후보 3개 (영상과 별개, 업로드 때 커버로 직접 선택)

## 3. 구성

| 파일 | 역할 |
|---|---|
| `.claude/skills/gratitude-reels/` | 감독관 — 전체 흐름, 사용자 확인, 렌더·마스터 |
| `.claude/skills/faceblur/` | B-roll 다른 사람 얼굴 블러 |
| `.claude/agents/transcriber.md` | 전사기 |
| `.claude/agents/hooker.md` | 후커 |
| `.claude/agents/cut-editor.md` | 컷편집 담당 |
| `.claude/agents/subtitler.md` | 자막 담당 |
| `.claude/agents/thumbnail-maker.md` | 썸네일 담당 |
| `.claude/agents/broll-matcher.md` | 화면연결 담당 |
| `.claude/agents/audio-engineer.md` | 오디오 담당 |
| `tools/plug.py` | 플러그인 찾기·점검·IT Reelsmaker 스크립트 실행 |
| `tools/job.py` | 영상 등록, 단계별 진행 상태 |
| `tools/faceblur.py` | 얼굴 검출(YuNet)·트래킹·블러·확인 시트 |
| `tools/thumbs.py` | 젠세리프 제목 썸네일 3안 + 비교 시트 |
| `tools/subs_preview.py` | 렌더 전 자막 끊김 미리보기 (키트와 같은 규칙) |
| `tools/sfx.py` | 기본 효과음 합성 |
| `tools/fonts.py` | 자막용 한글 폰트(Pretendard) 받기, 브랜드 폰트 지정 |
| `reel-defaults.json`, `it-reelsmaker.json` | IT Reelsmaker 프로젝트 설정 (감사일기 기본값) |

## 참고
- 레퍼런스: [choigpt-ai/retention-shorts](https://github.com/choigpt-ai/retention-shorts) — 구간 선정·세이프존 검수 발상
- 편집 엔진: [IT Reelsmaker](https://github.com/itpartypattaya/reels-montage) (MIT), [Social Media Skills](https://github.com/social-media-skills/skills), [ffmpeg-llm](https://github.com/rendi-api/ffmpeg-llm) (MIT)
- 얼굴 검출 모델: OpenCV Zoo YuNet (첫 실행 때 자동 다운로드)
