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
tools/                       plug.py · job.py · faceblur.py · thumbs.py · subs_preview.py · sfx.py
```
