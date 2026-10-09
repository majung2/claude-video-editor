"""[감사일기 전용] IT Reelsmaker 키트를 감사일기 레퍼런스 모습으로 렌더하게 하는 도구.

레퍼런스(.claude/skills/gratitude-reels/references/reference-analysis.md)와 똑같이 만들려고
  · 자막: 가운데 정렬 · 한 줄 · 흰 글자 + 얇은 검은 외곽선 · 세로 중심 y≈74.5% · 제자리 타자기식 등장
  · B-roll: 화면 80% 크기 카드(사진 전체가 보이게)로 얼굴 위에 하드컷, 줌 없음 · 가로 사진은 작게 위쪽(y≈40%)
  · 화면 전체: 줌(drift)·가상 카메라 없음
을 키트에 더한다. 플러그인(visual_plan.py 등)은 고치지 않는다 — 플러그인이 만든 결과(props)를 이 도구가 바꾼다.
그래서 플러그인을 업데이트해도 그대로 쓸 수 있다.

    python3 tools/gratitude.py patch-kit [--remotion reels]   키트에 감사일기 모드를 넣는다 (이미 있으면 그대로)
    python3 tools/gratitude.py check     [--remotion reels]   키트에 감사일기 모드가 있는지 확인 (없으면 종료 코드 1)
    python3 tools/gratitude.py props edit/<id>/reelkit-props.json [--edit edit/<id>] [--remotion reels]
                                                              visual_plan export 결과를 감사일기 모습으로 바꾼다

`kit.py update` 로 키트를 새로 받으면 감사일기 모드가 지워진다 → `patch-kit` 를 다시 실행한다.
설정값(글자 크기·위치·카드 크기 등)은 config/gratitude.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "gratitude.json"
MARK = "majunge patch"

DEFAULTS = {
    "subtitles": {"size": 78, "centerY": 1430, "maxWidth": 842, "weight": 700, "color": "#FFFFFF", "outline": 3,
                  "outlineColor": "#000000", "shadow": 2, "holdAfter": 0.25},
    "card": [108, 192, 864, 1536],
    "pip": {"w": 0.55, "max_h": 0.30, "center_y": 0.40},
    "pip_if_wider_than": 1.15,
}

GRATITUDE_TSX = r'''// 감사일기 subtitles (majunge patch — not part of the plugin's kit; tools/gratitude.py patch-kit writes this file and
// tools/gratitude.py check verifies it). Measured from the two 감사일기 reference reels
// (.claude/skills/gratitude-reels/references/reference-analysis.md): white text with a thin dark outline and a soft
// shadow, centered, one line, centered at y ≈ 74.5 % (1430 px of 1920), at most ≈ 78 % of the width. Typewriter reveal
// in a fixed layout: the whole line is laid out centered first and the words appear in place, left to right, as they
// are spoken (the line never re-centers). A line clears ~0.25 s after its last word or when the next one starts, so a
// real pause between sentences shows as a short blank.
import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { measureText } from "@remotion/layout-utils";
import { fitSize, useFontsReady } from "./Phrase";
import type { Captions, Word } from "./Subtitles";
import { bestSplit, buildChunks } from "./Subtitles";

export type GratitudeStyle = {
  size?: number; // font px at 1920 height (메모먼트 꾹꾹체 matches the reference at 78)
  centerY?: number; // line center, px
  maxWidth?: number; // px
  weight?: number;
  color?: string;
  outline?: number; // px
  outlineColor?: string;
  shadow?: number; // px, soft drop shadow under the outline
  holdAfter?: number; // s the line stays after its last word
};
export const GRATITUDE_DEFAULTS: Required<GratitudeStyle> = {
  size: 78, centerY: 1430, maxWidth: 842, weight: 700, color: "#FFFFFF", outline: 3, outlineColor: "#000000", shadow: 2,
  holdAfter: 0.25,
};

type Line = { words: Word[]; start: number; end: number; size: number };
const text = (ws: Word[]) => ws.map((w, k) => (k && !w.glue ? " " : "") + w.text).join("");

// an outline drawn with text-shadow in 16 directions (CSS text-stroke would eat into the glyphs), plus a soft shadow
const outlineShadow = (px: number, color: string, shadow: number) => {
  const out: string[] = [];
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * 2 * Math.PI;
    out.push(`${(Math.cos(a) * px).toFixed(2)}px ${(Math.sin(a) * px).toFixed(2)}px 0 ${color}`);
  }
  if (shadow > 0) out.push(`0 ${shadow}px ${shadow * 2}px rgba(0,0,0,0.55)`);
  return out.join(", ");
};

export const GratitudeSubtitles: React.FC<{
  captions: Captions;
  font: string;
  hide?: [number, number][];
  tail?: number;
  style?: GratitudeStyle | null;
}> = ({ captions, font, hide = [], tail = 0, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ready = useFontsReady([font]);
  const s = { ...GRATITUDE_DEFAULTS, ...(style ?? {}) };
  const hideKey = JSON.stringify(hide);
  const lines = React.useMemo(() => {
    const words = captions.words.filter((w) => !hide.some(([a, b]) => w.start >= a && w.end <= b));
    const width = (ws: Word[]) =>
      ready ? measureText({ text: text(ws), fontFamily: font, fontSize: s.size, fontWeight: s.weight }).width + 2 * s.outline : 0;
    // one sentence (or phrase between pauses) per subtitle; one that does not fit on one line is split where it reads as
    // two (the kit's bestSplit: pauses, commas, never after a short function word), each part on its own line
    const fit = (ws: Word[]): Word[][] => {
      if (ws.length < 2 || width(ws) <= s.maxWidth) return [ws];
      const k = bestSplit(ws);
      return [...fit(ws.slice(0, k)), ...fit(ws.slice(k))];
    };
    const parts = buildChunks(words, 40, 200).flatMap((c) => fit(c.words));
    const out: Line[] = parts.map((ws) => ({
      words: ws, start: ws[0].start, end: ws[ws.length - 1].end + s.holdAfter,
      // a single word wider than the line shrinks instead of running past the edge
      size: Math.min(s.size, fitSize({ text: text(ws), size: s.size, font, weight: s.weight, maxWidth: s.maxWidth, ready })),
    }));
    out.forEach((l, k) => {
      const next = out[k + 1];
      if (next) l.end = Math.min(l.end, next.start - 0.04);
      else l.end = Math.min(Math.max(l.end, captions.duration), captions.duration + tail);
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captions, hideKey, font, ready, s.size, s.maxWidth, s.weight, s.outline, s.holdAfter, tail]);
  const t = frame / fps;
  if (hide.some(([a, b]) => t >= a && t < b)) return null;
  const l = lines.find((x) => t >= x.start - 0.03 && t < x.end);
  if (!l) return null;
  const lh = 1.25;
  return (
    <div style={{ position: "absolute", left: 0, width: 1080, top: s.centerY - (l.size * lh) / 2, textAlign: "center",
      fontFamily: font, fontWeight: s.weight, fontSize: l.size, lineHeight: lh, color: s.color, whiteSpace: "pre",
      textShadow: outlineShadow(s.outline, s.outlineColor, s.shadow) }}>
      {l.words.map((w, k) => (
        // words not yet spoken keep their place (the line is laid out once), they are only invisible
        <span key={k} style={{ opacity: w === l.words[0] || t >= w.start - 0.03 ? 1 : 0 }}>
          {k && !w.glue ? " " : ""}
          {w.text}
        </span>
      ))}
    </div>
  );
};
'''

# (file, old, new): applied once; a file that already holds `new` is left alone
EDITS = [
    ("kit/Subtitles.tsx",
     'export type SubtitleMode = "accent" | "plate" | "typewriter" | "none";',
     '// "gratitude" (majunge patch): the 감사일기 reference style, drawn by GratitudeSubtitles; KitSubtitles draws nothing for it\n'
     'export type SubtitleMode = "accent" | "plate" | "typewriter" | "gratitude" | "none";'),
    ("kit/Subtitles.tsx",
     '  if (mode === "none") return null;\n',
     '  if (mode === "none" || mode === "gratitude") return null;\n'),
    ("kit/Inserts.tsx",
     '  mode: "replace" | "window" | "popup" | "cutaway";',
     '  // "card" (majunge patch, 감사일기 reference): the picture whole (contain) in a box over the speaker, hard cut, no zoom\n'
     '  mode: "replace" | "window" | "popup" | "cutaway" | "card";'),
    ("kit/Inserts.tsx",
     'const warnedBox = new Set<string>();',
     'const warnedBox = new Set<string>();\n'
     '// "card" without a box (majunge patch): 80 % × 80 % of the frame, centered (감사일기 reference)\n'
     'const CARD_BOX = [108, 192, 864, 1536];'),
    ("kit/Inserts.tsx",
     '  } else if (ins.mode === "window") {',
     '  } else if (ins.mode === "card") {\n'
     '    // majunge patch — 감사일기 reference: the photo or clip as a card ≈ 80 % × 80 % of the frame, centered, over the\n'
     '    // speaker; the whole picture is shown (contain) and the speaker stays visible around it; it appears and\n'
     '    // disappears with a cut, without zoom\n'
     '    const b = ins.box && ins.box.length === 4 ? ins.box : CARD_BOX;\n'
     '    body = (\n'
     '      <div style={{ position: "absolute", left: b[0], top: b[1], width: b[2], height: b[3], display: "flex",\n'
     '        alignItems: "center", justifyContent: "center" }}>\n'
     '        <Media ins={ins} style={{ width: b[2], height: b[3], objectFit: "contain", maxWidth: "none" }} />\n'
     '      </div>\n'
     '    );\n'
     '  } else if (ins.mode === "window") {'),
    ("ReelKit.tsx",
     'import { Captions, KitSubtitles, SubtitleMode } from "./kit/Subtitles";',
     'import { Captions, KitSubtitles, SubtitleMode } from "./kit/Subtitles";\n'
     'import { GratitudeStyle, GratitudeSubtitles } from "./kit/GratitudeSubtitles"; // majunge patch'),
    ("ReelKit.tsx",
     '  subtitlesTop?: number;',
     '  gratitude?: GratitudeStyle | null; // majunge patch — subtitles "gratitude": its style (tools/gratitude.py props)\n'
     '  subtitlesTop?: number;'),
    ("ReelKit.tsx",
     '      <KitSubtitles captions={p.subtitleCaptions ?? p.captions} brand={p.brand} font={fonts.body} mode={p.subtitles} hide={hide}\n'
     '        top={p.subtitlesTop ?? 1290} look={look} shade={p.subtitlesShade ?? 0.35} part="text" tail={tail} {...subArea} />',
     '      {p.subtitles === "gratitude" ? ( // majunge patch\n'
     '        <GratitudeSubtitles captions={p.subtitleCaptions ?? p.captions} font={fonts.body} hide={hide} tail={tail} style={p.gratitude} />\n'
     '      ) : (\n'
     '        <KitSubtitles captions={p.subtitleCaptions ?? p.captions} brand={p.brand} font={fonts.body} mode={p.subtitles} hide={hide}\n'
     '          top={p.subtitlesTop ?? 1290} look={look} shade={p.subtitlesShade ?? 0.35} part="text" tail={tail} {...subArea} />\n'
     '      )}'),
]


def remotion_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    cfg = ROOT / "it-reelsmaker.json"
    if cfg.exists():
        d = json.loads(cfg.read_text(encoding="utf-8")).get("remotion_dir")
        if d and (Path(d) / "src").is_dir():
            return Path(d)
    return ROOT / "reels"


def config() -> dict:
    c = json.loads(json.dumps(DEFAULTS))
    if CONFIG.exists():
        user = json.loads(CONFIG.read_text(encoding="utf-8"))
        for k, v in user.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update({kk: vv for kk, vv in v.items() if not kk.startswith("_")})
            else:
                c[k] = v
    return c


def status(rem: Path) -> list[str]:
    """What is missing from the kit's 감사일기 mode (empty: all there)."""
    src = rem / "src"
    missing = []
    if not (src / "kit" / "GratitudeSubtitles.tsx").exists():
        missing.append("kit/GratitudeSubtitles.tsx")
    for f, old, new in EDITS:
        p = src / f
        if not p.exists() or new not in p.read_text(encoding="utf-8"):
            missing.append(f"{f}: {new.strip().splitlines()[-1].strip()[:60]}")
    return missing


def cmd_patch(a) -> None:
    rem = remotion_dir(a.remotion)
    src = rem / "src"
    if not (src / "ReelKit.tsx").exists():
        sys.exit(f"[오류] 키트가 없어요: {src}/ReelKit.tsx (kit.py new 로 먼저 만드세요)")
    (src / "kit" / "GratitudeSubtitles.tsx").write_text(GRATITUDE_TSX, encoding="utf-8")
    changed, failed = [], []
    for f, old, new in EDITS:
        p = src / f
        s = p.read_text(encoding="utf-8")
        if new in s:
            continue
        if s.count(old) != 1:
            failed.append(f"{f}: 고칠 자리를 못 찾음 → {old.strip().splitlines()[0][:70]}")
            continue
        p.write_text(s.replace(old, new), encoding="utf-8")
        changed.append(f)
    if failed:
        print("\n".join(failed))
        sys.exit("[오류] 키트 버전이 달라 일부를 못 고쳤어요. 위 자리를 보고 손으로 맞추거나 Claude에게 맡기세요.")
    print(f"키트 감사일기 모드: {'적용 ' + ', '.join(sorted(set(changed))) if changed else '이미 적용됨'} ({rem})")


def cmd_check(a) -> None:
    rem = remotion_dir(a.remotion)
    miss = status(rem)
    if miss:
        print("키트에 감사일기 모드가 없어요 (kit.py update 뒤라면 정상) → python3 tools/gratitude.py patch-kit")
        print("\n".join("  - " + m for m in miss))
        sys.exit(1)
    print(f"키트 감사일기 모드: OK ({rem})")


def media_size(path: Path) -> tuple[int, int] | None:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height:stream_side_data=rotation", "-of", "json", str(path)],
                             capture_output=True, text=True, check=True).stdout
        st = json.loads(out)["streams"][0]
        w, h = int(st["width"]), int(st["height"])
        rot = next((abs(int(d.get("rotation", 0))) for d in st.get("side_data_list", []) if "rotation" in d), 0)
        return (h, w) if rot in (90, 270) else (w, h)
    except Exception:
        return None


def cmd_props(a) -> None:
    rem = remotion_dir(a.remotion)
    miss = status(rem)
    if miss:
        sys.exit("[오류] 키트에 감사일기 모드가 없어요 → python3 tools/gratitude.py patch-kit 먼저")
    c = config()
    p = Path(a.props)
    props = json.loads(p.read_text(encoding="utf-8"))
    props["subtitles"] = "gratitude"
    props["gratitude"] = c["subtitles"]
    props["drift"] = False  # 레퍼런스: 줌 없음
    props.pop("camera", None)
    cards = pips = 0
    for ins in props.get("inserts", []):
        if ins.get("kind") != "broll" or ins.get("mode") not in ("replace", "window", "card"):
            continue
        ins["mode"] = "card"
        ins["transition_in"] = ins["transition_out"] = "cut"
        size = media_size(rem / "public" / ins["file"])
        if ins.get("media") == "image" and size and size[0] > size[1] * float(c["pip_if_wider_than"]):
            # 가로 사진: 작게 위쪽 (레퍼런스 PiP, 폭 55 %, 세로 중심 40 %)
            w = round(1080 * c["pip"]["w"])
            h = min(round(w * size[1] / size[0]), round(1920 * c["pip"]["max_h"]))
            ins["box"] = [round((1080 - w) / 2), round(1920 * c["pip"]["center_y"] - h / 2), w, h]
            pips += 1
        else:
            ins["box"] = list(c["card"])
            cards += 1
    p.write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    s = c["subtitles"]
    band = [round(s["centerY"] - s["size"] * 0.7), round(s["centerY"] + s["size"] * 0.7)]
    if a.edit:  # faces.py audit 이 실제 자막 위치로 검사하도록
        vp = Path(a.edit) / "visual_plan.json"
        if vp.exists():
            plan = json.loads(vp.read_text(encoding="utf-8"))
            plan["subtitles_band"] = band
            vp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"감사일기 모습으로 바꿈: 자막 gratitude(가운데·한 줄·외곽선, y {s['centerY']}), 줌 없음, "
          f"B-roll 카드 {cards}개 · 작은 가로 사진 {pips}개 (하드컷). 자막 띠 {band}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("patch-kit", "check"):
        q = sp.add_parser(name)
        q.add_argument("--remotion")
    q = sp.add_parser("props")
    q.add_argument("props")
    q.add_argument("--edit")
    q.add_argument("--remotion")
    a = ap.parse_args()
    {"patch-kit": cmd_patch, "check": cmd_check, "props": cmd_props}[a.cmd](a)


if __name__ == "__main__":
    main()
