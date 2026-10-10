"""[전사 — Mac 연결 셸 쪽, vm_transcribe.sh 가 부른다] IT Reelsmaker transcribe.py 와 같은 결과를 조각조각 만든다.

Mac 연결 셸(device_bash)은 호출이 끝나면 그 안의 프로그램을 모두 끝내고, 한 번에 최대 3분이라
긴 전사를 한 번에도, 백그라운드로도 돌릴 수 없다(2026-10-10 확인). 그래서 음성을 1분 안팎 조각으로 나눠
한 번 부를 때마다 시간 안에서 할 수 있는 조각까지만 받아쓰고, 다시 부르면 이어서 한다.

    python3 tools/vm_transcribe.py <영상 id> [--budget 140]
      → "계속" 이 나오면 같은 명령을 다시, "끝" 이 나오면 edit/<id>/transcripts/<원본 이름>.json 완성

조각 경계는 말 사이 가장 조용한 곳(목표 55초 ±8초)이라 단어가 잘리지 않는다. 조각 결과는 edit/<id>/vmt/ 에 남는다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import wave
from pathlib import Path

import numpy as np

T0 = time.time()
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(os.environ.get("RM_SCRIPTS", Path.home() / "rm" / "scripts"))))
import transcribe as T  # noqa: E402  (IT Reelsmaker scripts/transcribe.py)

CHUNK, SEARCH, SR = 55.0, 8.0, 16000
SPEED = 0.9  # 이 VM 에서 medium int8 은 음성 1초에 약 0.85초 (40초 → 33초)


def cut_points(a: np.ndarray) -> list[float]:
    """CHUNK 초마다, 그 근처 ±SEARCH 초 안에서 0.3초 평균이 가장 조용한 곳."""
    dur = len(a) / SR
    win = int(0.3 * SR)
    pts, t = [0.0], CHUNK
    while t < dur - 15:
        lo, hi = int((t - SEARCH) * SR), int(min(dur, t + SEARCH) * SR)
        seg = a[lo:hi] ** 2
        rms = np.convolve(seg, np.ones(win) / win, "valid")
        best = lo + int(np.argmin(rms)) + win // 2
        pts.append(round(best / SR, 3))
        t = best / SR + CHUNK
    pts.append(round(dur, 3))
    return pts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--budget", type=float, default=140, help="이번 호출에서 쓸 초 (device_bash 한 번 = 최대 180초)")
    ap.add_argument("--model", default="medium")
    ap.add_argument("--language", default="ko")
    a = ap.parse_args()
    os.chdir(ROOT)
    project = T.project_root()
    e = T.edit_dir(f"edit/{a.id}", project, create=True)
    mains = sorted((ROOT / "footage" / a.id).glob("main.*"))
    if not mains:
        sys.exit(f"[오류] footage/{a.id}/main.* 가 없어요")
    src = mains[0]
    out = e / "transcripts" / f"{src.stem}.json"
    vmt = e / "vmt"
    vmt.mkdir(exist_ok=True)

    # 1) 음성 추출 + 조각 계획 (처음 한 번)
    plan_p = vmt / "plan.json"
    if not plan_p.exists():
        wav, identity, off = T.source_wav(e, src)
        a16 = T.read_wav(wav)
        pts = cut_points(a16)
        parts = []
        for i, (s, t) in enumerate(zip(pts, pts[1:])):
            p = vmt / f"chunk-{i:02d}.wav"
            with wave.open(str(p), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
                w.writeframes((np.clip(a16[int(s * SR):int(t * SR)], -1, 1) * 32767).astype(np.int16).tobytes())
            parts.append({"i": i, "start": s, "end": t, "wav": p.name})
        plan_p.write_text(json.dumps({"source": src.name, "identity": identity, "audio_offset": off, "parts": parts},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        spans = ", ".join("%.0f-%.0fs" % (q["start"], q["end"]) for q in parts)
        print(f"계획: {len(parts)}조각 ({spans})")
    plan = json.loads(plan_p.read_text(encoding="utf-8"))

    # 2) 남은 조각을 시간 안에서
    model = None
    for p in plan["parts"]:
        done = vmt / f"part-{p['i']:02d}.json"
        if done.exists():
            continue
        need = (p["end"] - p["start"]) * SPEED + (8 if model is None else 0)
        if time.time() - T0 + need > a.budget:
            left = sum(1 for q in plan["parts"] if not (vmt / f"part-{q['i']:02d}.json").exists())
            print(f"계속: 남은 조각 {left}개 — 같은 명령을 다시 실행하세요")
            return
        if model is None:
            model = T.load_model(a.model, "int8")
        lang, text, words = T.words_of(model, vmt / p["wav"], a.language, offset=p["start"])
        done.write_text(json.dumps({"lang": lang, "text": text, "words": words}, ensure_ascii=False), encoding="utf-8")
        print(f"조각 {p['i'] + 1}/{len(plan['parts'])} ({p['start']:.0f}-{p['end']:.0f}s): 단어 {len(words)}개 "
              f"[{time.time() - T0:.0f}초]", flush=True)

    # 3) 합치기 — transcribe.py full 과 같은 형식
    docs = [json.loads((vmt / f"part-{p['i']:02d}.json").read_text(encoding="utf-8")) for p in plan["parts"]]
    words = [w for d in docs for w in d["words"]]
    doc = {"language_code": docs[0]["lang"] if docs else a.language, "text": " ".join(d["text"] for d in docs),
           "words": words, "source": plan["source"], "source_identity": plan["identity"],
           "model": f"faster-whisper {a.model} int8 (vm_transcribe, {len(docs)} parts)", "timeline": "video",
           "audio_offset": plan["audio_offset"]}
    T.save_json(out, doc)
    problems = [x for x in T.check_doc(doc) if not x.startswith("note:")]
    notes = [x[6:] for x in T.check_doc(doc) if x.startswith("note:")]
    print(f"끝: {out.relative_to(ROOT)} — 단어 {len(words)}개" + (f"; 문제: {'; '.join(problems)}" if problems else ""))
    for n in notes:
        print("  참고: " + n)


if __name__ == "__main__":
    main()
