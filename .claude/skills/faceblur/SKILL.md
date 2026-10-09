---
name: faceblur
description: B-roll 사진·영상에 나온 다른 사람 얼굴을 찾아 블러(또는 모자이크) 처리한다. 마정이 본인 얼굴은 남기고 그 외 얼굴은 모두 가린 사본을 broll_blur 폴더에 만든다. "B-roll 얼굴 블러", "모자이크", "다른 사람 얼굴 가려줘", 화면연결 담당이 B-roll을 쓰기 전에 사용.
---

# B-roll 얼굴 블러

원본은 건드리지 않고 `footage/<id>/broll_blur/` 에 가린 사본을 만든다. 이후 모든 단계(화면연결, 썸네일)는 이 폴더만 쓴다.
도구: `tools/faceblur.py` (OpenCV + YuNet 얼굴 모델. 모델은 처음 실행 때 자동으로 받아 `assets/models/` 에 두고,
IT Reelsmaker 의 얼굴 위치 측정에도 같이 쓰이게 `it-reelsmaker.json` 에 등록한다.)

## 순서

### 1. 찾기
```bash
python3 tools/faceblur.py scan footage/<id>/broll
```
- 사진은 얼굴마다, 영상은 같은 사람을 프레임 사이로 이어 **트랙** 번호를 매긴다.
- 결과: `footage/<id>/broll/_faces/plan.json`, 검토 시트 `_faces/review-NN.jpg` (빨간 박스 + `#번호`).
- 기본값은 **전부 블러**. 영상에서 딱 한 번 잡힌 약한 검출(weak)은 오검출이 많아 `keep` 에 미리 들어 있다.

### 2. 검토 (눈으로)
1. 검토 시트를 전부 Read 로 본다.
2. 마정이 본인인지 판단하려면 메인 영상 프레임과 비교한다:
   `ffmpeg -v error -ss 3 -i footage/<id>/main.* -frames:v 1 -vf scale=540:-2 footage/<id>/broll/_faces/me.jpg` → Read.
3. `plan.json` 수정:
   - 본인 얼굴 트랙 → 그 파일의 `keep` 에 번호 추가
   - weak 인데 **진짜 사람 얼굴**이면 → `keep` 에서 빼서 블러되게
   - 박스가 얼굴이 아닌 곳(깃발, 무늬)이면 → `keep` 에 넣어 블러하지 않음
   - 검출이 놓친 얼굴(작은 얼굴, 옆모습, 뒤통수 아닌 얼굴) → `extra` 에 `[시작초, 끝초, x, y, w, h]` (사진은 `0, 0`). 좌표는 원본 픽셀.
4. **애매하면 블러한다.** 본인인지 확신이 없으면 감독관에게 질문으로 올리고, 답을 못 받으면 블러.

### 3. 적용
```bash
python3 tools/faceblur.py apply footage/<id>/broll            # 기본: 부드러운 블러
python3 tools/faceblur.py apply footage/<id>/broll --style mosaic   # 모자이크를 원할 때
```
→ `footage/<id>/broll_blur/` (얼굴 없는 파일도 그대로 복사되어 이 폴더 하나로 충분). 영상은 사이 프레임을 보간해 얼굴을 따라간다.

### 4. 확인
```bash
python3 tools/faceblur.py check footage/<id>/broll_blur
```
- `footage/<id>/_faces_check/check-NN.jpg` 를 Read 로 본다. 남은 박스가 본인 얼굴(keep)이거나 오검출이면 정상.
- 블러되지 않은 **다른 사람 얼굴**이 보이면 2단계로 돌아가 `extra` 에 넣고 다시 apply.
- 영상은 몇 장 뽑아 직접 본다: `ffmpeg -v error -i footage/<id>/broll_blur/<영상>.mp4 -vf "fps=2,scale=240:-2,tile=6x1" -frames:v 1 footage/<id>/_faces_check/<영상>-strip.jpg`

## 결과 보고
파일 수, 블러한 얼굴 수, 본인이라 남긴 얼굴(파일·번호), 직접 추가한 얼굴, 확인 결과. 원본 폴더는 그대로라는 것도 적는다.

## 한계 (사용자에게 그대로 말할 것)
- 아주 작거나(화면 폭의 3% 미만) 많이 돌아간 얼굴, 마스크·선글라스 얼굴은 놓칠 수 있다 → 4단계 눈 확인이 필수.
- 본인 여부는 자동 판별하지 않는다 (얼굴 인식 저장 없음). 시트를 보고 사람이 판단한다.
