"""[자유형식 전용] 사용자의 편집 지시서(edit/<id>/brief.json)대로 렌더 설정·효과음을 바꾸는 도구.

자유형식은 정해진 모습이 없다. 영상마다 사용자가 준 지시를 brief.json 에 적고, 지시에 없는 칸은
styles/free/config.json 의 defaults 로 채운다. 화면 부품은 새로 만들지 않고 이미 있는 것을 빌려 쓴다:
  · 감사일기 엔진 부품 (styles/gratitude/render.py patch-kit 이 엔진에 넣은 것):
    제자리 타자기 자막(subtitles "gratitude"), 훅 한 글자씩 타이핑(gratitudeHook), B-roll 카드·가로 사진 PiP, 사진 부드러운 확대
  · IT Reelsmaker 기본 기능: 자막 typewriter/accent/plate, 위쪽 훅 문구, 디자인 장면(인용·숫자·목록·CTA), 가상 카메라, 엔드카드
그래서 이 도구는 엔진을 패치하지 않는다 (patch-kit 은 감사일기 패치를 대신 불러 줄 뿐).

    python3 styles/free/render.py patch-kit [--remotion reels]   엔진에 빌려 쓸 부품이 없으면 감사일기 patch-kit 실행
    python3 styles/free/render.py check     [--remotion reels]   빌려 쓸 부품이 있는지 (없으면 종료 코드 1)
    python3 styles/free/render.py brief edit/<id>                brief.json + 기본값 → brief.resolved.json, 할 일 요약 출력
    python3 styles/free/render.py props edit/<id>/reelkit-props.json --edit edit/<id> [--remotion reels]
                                                                 visual_plan export 결과를 지시서 모습으로 바꾼다
    python3 styles/free/render.py keys --edit edit/<id>          지시서의 효과음(훅 타이핑·특정 말마다 소리)을 sfx.json 에
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

STYLE = Path(__file__).resolve().parent          # styles/free/
ROOT = STYLE.parent.parent                        # 툴킷 루트
CONFIG = STYLE / "config.json"
TAG = "자유:"                                     # sfx.json 에서 이 도구가 넣은 소리 표시 (다시 계산할 때 이것만 바꿈)


def _gratitude():
    """감사일기 render.py 를 모듈로 불러 부품(설정값·계산 함수)을 빌린다. 감사일기 파일은 고치지 않는다."""
    p = ROOT / "styles" / "gratitude" / "render.py"
    spec = importlib.util.spec_from_file_location("gratitude_render", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _gratitude()


def merge(base, over):
    """over 를 base 위에 깊게 덮는다. "_" 로 시작하는 설명 칸은 버린다. 리스트·값은 통째로 바꾼다."""
    if not isinstance(base, dict) or not isinstance(over, dict):
        return json.loads(json.dumps(over))
    out = {k: json.loads(json.dumps(v)) for k, v in base.items() if not str(k).startswith("_")}
    for k, v in over.items():
        if str(k).startswith("_"):
            continue
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else json.loads(json.dumps(v))
    return out


def config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def resolve(edit: Path) -> dict:
    """brief.json(지시) + config defaults(지시에 없는 칸) + presets(지시가 부른 감사일기 부품) → 최종 지시서."""
    c = config()
    p = edit / "brief.json"
    if not p.exists():
        sys.exit(f"[오류] 지시서가 없어요: {p} (감독관이 사용자 지시를 받아 먼저 만든다 — styles/free/brief.example.json 참고)")
    brief = json.loads(p.read_text(encoding="utf-8"))
    out = merge(c["defaults"], {})
    for name in brief.get("presets", []):
        if name not in c.get("presets", {}):
            sys.exit(f"[오류] 없는 부품 이름: {name} (있는 것: {', '.join(k for k in c['presets'] if not k.startswith('_'))})")
        out = merge(out, c["presets"][name]["brief"])
    out = merge(out, {k: v for k, v in brief.items() if k not in ("presets", "common_off")})
    # 공통 스펙 (썸네일 형식·훅·컷·자막): 지시와 상관없이 항상. common_off 에 적힌 것만 이 영상에서 지시서대로
    off = set(brief.get("common_off", []))
    bad = off - set(c["common"])
    if bad:
        sys.exit(f"[오류] common_off 에 없는 이름: {', '.join(bad)} (있는 것: {', '.join(c['common'])})")
    out["_overridden"] = []
    for name, spec in c["common"].items():
        if name in off:
            continue
        for path in c.get("locked", {}).get(name, []):
            want = spec["brief"]
            for k in path:
                want = want[k]
            cur = out
            for k in path[:-1]:
                cur = cur.setdefault(k, {})
            if cur.get(path[-1]) != want:
                out["_overridden"].append(f"{name}: {'.'.join(path)} = {cur.get(path[-1])!r} → 공통 스펙 {want!r}")
                cur[path[-1]] = json.loads(json.dumps(want))
    out["presets"] = brief.get("presets", [])
    out["common_off"] = sorted(off)
    return out


def subtitle_style(b: dict) -> dict:
    """감사일기 자막 모습(styles/gratitude/config.json subtitles) 위에 지시서의 자막 값을 덮은 것."""
    keys = ("size", "centerY", "maxWidth", "weight", "color", "outline", "outlineColor", "shadow", "holdAfter")
    return {**G.config()["subtitles"], **{k: v for k, v in b.get("subtitles", {}).items() if k in keys}}


# ---------------------------------------------------------------- brief


def summary(b: dict) -> list[str]:
    s, h, br, cut = b["subtitles"], b["hook"], b["broll"], b["cut"]
    lines = []
    off = set(b.get("common_off", []))
    tag = lambda name: "[공통 꺼짐] " if name in off else "[공통] "
    mode = {"gratitude": "제자리 타자기(감사일기 모습)", "typewriter": "IT Reelsmaker 타자기", "accent": "강조 단어",
            "plate": "판 위 글자", "none": "자막 없음"}.get(s["mode"], s["mode"])
    lines.append(tag("subtitles") + f"자막: {mode}" + ("" if s["mode"] == "none" else f", 마침표 {'남김' if s.get('period') else '없음'}"))
    hm = {"none": "없음", "typing": "훅 문장 한 글자씩 타이핑(썸네일 글씨)", "headline": "위쪽 훅 문구",
          "plugin": "IT Reelsmaker 기본"}.get(h["mode"], h["mode"])
    lines.append(tag("hook") + f"훅: {hm}" + (f" — \"{h['text']}\"" if h.get("text") else
                                 " — 후보 3개 중 고른 문장을 맨 앞에" if h["mode"] == "typing" else
                                 " — 후보 3개 제안" if h["mode"] == "headline" else ""))
    rm = {"retakes": "다시 말한 곳", "stutters": "더듬은 곳", "repeats": "같은 말 반복", "long_pauses": "긴 쉼",
          "fillers": "음·어 같은 군말"}
    lines.append(tag("cut") + "컷: " + (", ".join(rm.get(x, x) for x in cut.get("remove", [])) + " 빼기" if cut.get("remove") else "말 컷 없음")
                 + (f", 잘라낼 구간 {cut['trim']}" if cut.get("trim") else "")
                 + (f", 남길 구간 {cut['keep']}" if cut.get("keep") else "")
                 + (f", 속도 {cut['speed']}배" if cut.get("speed", 1.0) != 1.0 else "")
                 + (f", 목표 {cut['target_seconds']}초" if cut.get("target_seconds") else ""))
    bl = {"card": "80% 카드(가로 사진은 위쪽 작게)", "full": "화면 전체", "plugin": "IT Reelsmaker 기본"}.get(br["look"], br["look"])
    lines.append(f"B-roll: {bl}, 확대 {br.get('zoom', 1.0)}배, 다른 사람 얼굴 블러")
    cam = b["camera"]
    lines.append("화면 움직임: " + ("가상 카메라" if cam.get("virtual_camera") else "천천히 확대(drift)" if cam.get("drift") else "없음"))
    if b["look"].get("correct"):
        lines.append(f"색 보정: {b['look']['correct']}")
    sx = b["sfx"]
    snd = []
    if h["mode"] == "typing" and sx.get("hook_typing"):
        snd.append("훅 글자마다 타닥")
    for w in sx.get("on_words", []):
        snd.append(f"\"{'/'.join(w['words'])}\" 마다 {Path(w['file']).stem}")
    for x in sx.get("extra", []):
        snd.append(f"{x.get('at')}초 {Path(x['file']).stem}")
    lines.append("효과음: " + (", ".join(snd) if snd else "없음"))
    lines.append("음악: " + (b["music"]["file"] if b["music"].get("file") else "없음"))
    if b.get("scenes"):
        lines.append(f"디자인 장면: {len(b['scenes'])}개 ({', '.join(x.get('kind', '?') for x in b['scenes'])})")
    if b.get("end_card"):
        lines.append(f"엔드카드: {b['end_card']}")
    n = b["output"].get("thumbnails", 3)
    lines.append(tag("thumbnail") + f"결과물: 영상 1개" + (f" + 썸네일 후보 {n}개 (젠세리프 파스텔)" if n else " (썸네일 없음)"))
    return lines


def cmd_brief(a) -> None:
    edit = Path(a.edit)
    b = resolve(edit)
    warn = [f"지시서가 공통 스펙과 달라 공통 값으로 둠 — {x} (이 영상만 끄려면 사용자 확인 뒤 common_off)"
            for x in b.get("_overridden", [])]
    if b["hook"]["mode"] == "typing" and b["subtitles"]["mode"] not in ("gratitude", "none"):
        warn.append("훅 타이핑은 감사일기 자막 엔진에서만 그려져요 → 자막을 gratitude 로 바꾸거나 훅을 headline 으로")
    if b["hook"]["mode"] == "headline" and not b["hook"].get("text"):
        warn.append("위쪽 훅 문구는 화면에 쓸 글(hook.text)이 필요해요 — 후커 단계에서 정함")
    for w in b["sfx"].get("on_words", []) + b["sfx"].get("extra", []):
        if not (ROOT / w["file"]).exists():
            warn.append(f"효과음 파일이 없어요: {w['file']} (python3 tools/sfx.py 로 합성하거나 파일을 넣어 주세요)")
    if b["music"].get("file") and not (ROOT / b["music"]["file"]).exists():
        warn.append(f"음악 파일이 없어요: {b['music']['file']}")
    (edit / "brief.resolved.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print("지시서 (지시 + 기본값):")
    print("\n".join("  · " + x for x in summary(b)))
    if b.get("presets"):
        print("  빌려 온 부품: " + ", ".join(b["presets"]))
    if warn:
        print("확인할 것:")
        print("\n".join("  ! " + x for x in warn))
    print(f"→ {edit / 'brief.resolved.json'}")


# ---------------------------------------------------------------- props


def cmd_props(a) -> None:
    rem = G.remotion_dir(a.remotion)
    edit = Path(a.edit)
    b = resolve(edit)
    if b["subtitles"]["mode"] == "gratitude" or b["hook"]["mode"] == "typing" or b["broll"]["look"] == "card":
        if G.status(rem):
            sys.exit("[오류] 엔진에 빌려 쓸 감사일기 부품이 없어요 → python3 styles/free/render.py patch-kit 먼저")
    p = Path(a.props)
    props = json.loads(p.read_text(encoding="utf-8"))
    did = []

    # 훅 구간 끝 (출력 초): cut.json 의 hook beat → 지시서 hook.until → 3초
    hook_end = G.hook_until(edit) or b["hook"].get("until") or 3.0
    dur = None
    try:
        dur = float(json.loads((edit / "captions.json").read_text(encoding="utf-8")).get("duration") or 0) or None
    except (OSError, ValueError):
        pass

    # 자막
    sm = b["subtitles"]["mode"]
    hide = list(props.get("hideSubtitles") or [])
    if sm == "gratitude" or (sm == "none" and b["hook"]["mode"] == "typing"):
        props["subtitles"] = "gratitude"
        props["gratitude"] = subtitle_style(b)
        if sm == "none":  # 훅 타이핑만 쓰고 말자막은 숨김
            hide.append([round(hook_end, 3), round((dur or 9999) + 1, 3)])
        did.append(f"자막 {'훅만' if sm == 'none' else 'gratitude'} (y {props['gratitude']['centerY']}, {props['gratitude']['size']}px)")
    elif sm in ("typewriter", "accent", "plate", "none"):
        props["subtitles"] = sm
        props["gratitude"] = None
        did.append(f"자막 {sm}")
    else:
        sys.exit(f"[오류] 모르는 자막 모드: {sm}")

    # 훅
    hm = b["hook"]["mode"]
    props["gratitudeHook"] = None
    if hm == "typing":
        sys.path.insert(0, str(ROOT / "tools"))
        from thumbs import load_style  # 썸네일 공통 스펙(config/thumb.json)까지 따라감
        grad = load_style(STYLE.name).get("thumb_gradient")
        hook_cfg = {**G.config().get("hook", {}), **b["hook"].get("look", {})}
        props["gratitudeHook"] = {**hook_cfg, "until": round(hook_end, 3), **({"gradient": grad} if grad else {})}
        props["hook"] = None  # pop 하면 템플릿 기본 문구가 나온다
        hide = [h for h in hide if not (h[0] <= 0.05 and h[1] <= hook_end + 0.5)]
        did.append(f"훅 타이핑 0~{hook_end:.2f}s")
    elif hm == "headline":
        props["hook"] = {"text": b["hook"].get("text") or "", "until": round(hook_end, 3)}
        did.append(f"위쪽 훅 문구 0~{hook_end:.2f}s")
    elif hm == "none":
        props["hook"] = None
        hide = [h for h in hide if not (h[0] <= 0.05 and h[1] <= hook_end + 0.5)]
        did.append("훅 문구 없음")
    props["hideSubtitles"] = hide

    # 화면 움직임
    cam = b["camera"]
    props["drift"] = bool(cam.get("drift"))
    if not cam.get("virtual_camera"):
        props.pop("camera", None)

    # B-roll
    look = b["broll"]["look"]
    gc = G.config()
    card = b["broll"].get("card") or gc["card"]
    pip = {**gc["pip"], **b["broll"].get("pip", {})}
    wider = float(b["broll"].get("pip_if_wider_than", gc["pip_if_wider_than"]))
    zoom = float(b["broll"].get("zoom", 1.0))
    cards = pips = fulls = 0
    for ins in props.get("inserts", []):
        if ins.get("kind") != "broll" or ins.get("mode") not in ("replace", "window", "card"):
            continue
        if look == "plugin":
            continue
        ins["transition_in"] = ins["transition_out"] = b["broll"].get("transition", "cut")
        try:
            photo = G.photo_source(edit, ins["id"])
        except OSError:  # 다른 작업 공간에서 만든 경로 등
            photo = None
        if photo and Path(ins["file"]).parent.name != "photos":
            # 사진은 미리 만든 확대 영상(픽셀 단위로 움직여 떨림) 대신 원본(블러본)을 엔진이 직접 그린다
            dst = rem / "public" / Path(ins["file"]).parent.parent / "photos" / (ins["id"] + photo.suffix.lower())
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(photo, dst)
            ins["file"] = dst.relative_to(rem / "public").as_posix()
            ins["media"] = "image"
            ins["src_in"] = 0.0
        if ins.get("media") == "image":
            ins["zoom_to"] = zoom  # 1.0 = 확대 없음 (엔진 기본 1.06 이 끼지 않게 항상 적는다)
        if look == "full":
            ins["mode"] = "replace"
            ins.pop("box", None)
            fulls += 1
            continue
        ins["mode"] = "card"
        size = G.media_size(rem / "public" / ins["file"])
        if ins.get("media") == "image" and size and size[0] > size[1] * wider:
            w = round(1080 * pip["w"])
            h = min(round(w * size[1] / size[0]), round(1920 * pip["max_h"]))
            ins["box"] = [round((1080 - w) / 2), round(1920 * pip["center_y"] - h / 2), w, h]
            pips += 1
        else:
            ins["box"] = list(card)
            cards += 1
    if cards + pips + fulls:
        did.append(f"B-roll 카드 {cards} · 위쪽 작은 사진 {pips} · 전체 화면 {fulls}")

    # 엔드카드
    if b.get("end_card"):
        props["endCard"] = b["end_card"]
        did.append("엔드카드")
    elif b.get("end_card") is False:  # 지시: 엔드카드 빼기 (null 이면 reel.json/플러그인 설정 그대로)
        props["endCard"] = None

    p.write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")

    # faces.py audit 이 실제 자막 위치로 검사하도록
    if props["subtitles"] == "gratitude":
        s = props["gratitude"]
        band = [round(s["centerY"] - s["size"] * 0.7), round(s["centerY"] + s["size"] * 0.7)]
        vp = edit / "visual_plan.json"
        if vp.exists():
            plan = json.loads(vp.read_text(encoding="utf-8"))
            plan["subtitles_band"] = band
            vp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print("지시서 모습으로 바꿈: " + " / ".join(did))


# ---------------------------------------------------------------- keys


def cmd_keys(a) -> None:
    edit = Path(a.edit)
    b = resolve(edit)
    p = edit / "sfx.json"
    sfx = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"below_voice_db": 18, "sounds": []}
    keep = [x for x in sfx.get("sounds", []) if not str(x.get("what", "")).startswith(TAG)]
    added = []
    cap = json.loads((edit / "captions.json").read_text(encoding="utf-8"))
    dur = float(cap.get("duration") or 0) or None
    gk = G.config().get("sounds", {}).get("key", [])
    if b["hook"]["mode"] == "typing" and b["sfx"].get("hook_typing") and gk:
        until = G.hook_until(edit) or b["hook"].get("until") or 3.0
        hook_cfg = {**G.config().get("hook", {}), **b["hook"].get("look", {}), "until": until}
        keys = gk if isinstance(gk, list) else [gk]
        for i, t in enumerate(G.hook_keys(edit, hook_cfg)):
            added.append({"file": keys[(i * 3 + i // 2) % len(keys)], "at": t, "start": 0.0, "what": f"{TAG} 훅 타이핑"})
    voice = None
    for rule in b["sfx"].get("on_words", []):
        gain = None
        if rule.get("below_db") is not None:
            voice = voice if voice is not None else G.peak_db(edit / "final.mp4")
            cpk = G.peak_db(ROOT / rule["file"])
            if voice is not None and cpk is not None:
                gain = round(voice - float(rule["below_db"]) - cpk, 1)
        words = [w.replace(" ", "") for w in rule["words"]]
        for w in cap["words"]:
            if w["text"].rstrip(".!?,~").replace(" ", "") in words:
                at = w["end"] - 0.03 if rule.get("at", "start") == "end" else w["start"]
                if dur:
                    at = min(at, dur - 0.15)
                x = {"file": rule["file"], "at": round(at, 3), "start": 0.0, "what": f"{TAG} {'/'.join(rule['words'])}"}
                if gain is not None:
                    x["gain_db"] = gain
                added.append(x)
    for x in b["sfx"].get("extra", []):
        added.append({"start": 0.0, **x, "what": f"{TAG} {x.get('what', Path(x['file']).stem)}"})
    sfx["sounds"] = sorted(keep + added, key=lambda x: x["at"])
    p.write_text(json.dumps(sfx, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds: dict[str, int] = {}
    for x in added:
        kinds[x["what"]] = kinds.get(x["what"], 0) + 1
    print("효과음: " + (", ".join(f"{k[len(TAG):].strip()} {v}개" for k, v in kinds.items()) or "없음") + f" → {p}")


# ---------------------------------------------------------------- engine


def cmd_patch(a) -> None:
    rem = G.remotion_dir(a.remotion)
    if G.status(rem):
        G.cmd_patch(a)
    print(f"자유형식: 엔진 패치 없음 — 감사일기 부품을 빌려 씀 ({rem})")


def cmd_check(a) -> None:
    rem = G.remotion_dir(a.remotion)
    miss = G.status(rem)
    if miss:
        print("엔진에 빌려 쓸 감사일기 부품이 없어요 → python3 styles/free/render.py patch-kit")
        sys.exit(1)
    print(f"자유형식: 빌려 쓸 부품 OK ({rem})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("patch-kit", "check"):
        q = sp.add_parser(name)
        q.add_argument("--remotion")
    q = sp.add_parser("brief")
    q.add_argument("edit")
    q = sp.add_parser("props")
    q.add_argument("props")
    q.add_argument("--edit", required=True)
    q.add_argument("--remotion")
    q = sp.add_parser("keys")
    q.add_argument("--edit", required=True)
    a = ap.parse_args()
    {"patch-kit": cmd_patch, "check": cmd_check, "brief": cmd_brief, "props": cmd_props, "keys": cmd_keys}[a.cmd](a)


if __name__ == "__main__":
    main()
