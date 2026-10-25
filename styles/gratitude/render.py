"""[감사일기 전용] IT Reelsmaker 키트를 감사일기 레퍼런스 모습으로 렌더하게 하는 도구.

레퍼런스(styles/gratitude/references/reference-analysis.md)와 똑같이 만들려고
  · 자막: 가운데 정렬 · 한 줄 · 흰 글자 + 얇은 검은 외곽선 · 세로 중심 y≈74.5% · 제자리 타자기식 등장
  · B-roll: 화면 80% 크기 카드(사진 전체가 보이게)로 얼굴 위에 하드컷, 줌 없음 · 가로 사진은 작게 위쪽(y≈40%)
  · 화면 전체: 줌(drift)·가상 카메라 없음
을 키트에 더한다. 플러그인(visual_plan.py 등)은 고치지 않는다 — 플러그인이 만든 결과(props)를 이 도구가 바꾼다.
그래서 플러그인을 업데이트해도 그대로 쓸 수 있다.

    python3 styles/gratitude/render.py patch-kit [--remotion reels]   키트에 감사일기 모드를 넣는다 (이미 있으면 그대로)
    python3 styles/gratitude/render.py check     [--remotion reels]   키트에 감사일기 모드가 있는지 확인 (없으면 종료 코드 1)
    python3 styles/gratitude/render.py props edit/<id>/reelkit-props.json [--edit edit/<id>] [--remotion reels]
                                                              visual_plan export 결과를 감사일기 모습으로 바꾼다

`kit.py update` 로 키트를 새로 받으면 감사일기 모드가 지워진다 → `patch-kit` 를 다시 실행한다.
설정값(글자 크기·위치·카드 크기·훅·효과음 등)은 같은 폴더의 config.json, 썸네일 문구 모습은 thumb.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

STYLE = Path(__file__).resolve().parent          # styles/gratitude/
ROOT = STYLE.parent.parent                        # 툴킷 루트
CONFIG = STYLE / "config.json"
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
  softShadow?: { alpha?: number; blur?: number; dx?: number; dy?: number } | null; // 연한 그림자 (2026-10-24): 있으면 이것만 (outline 0 이면 테두리 없음)
  reveal?: "word" | "line"; // "line" (2026-10-23 사용자 결정, 19일차): the whole line appears at once instead of word by word
  dual?: GratitudeDual | null; // two-language subtitles (2026-10-22, 18일차 English): spoken line above, translation below
};
// Two-language subtitles (majunge patch, user decision 2026-10-22): the spoken words (e.g. English) on top in the heading
// font and a butter-cream color, typed in place as usual; the translation (Korean) under it in the subtitle font, shown
// whole for the line. `lines` are spans on the output timeline (render.py props --dual): the words spoken in a span make
// one subtitle and `ko` is its translation. Both lines are smaller than the one-line style.
export type GratitudeDual = {
  lines: { start: number; end: number; ko: string }[];
  enSize?: number; enCenterY?: number; enColor?: string; enOutline?: number; enFont?: "heading" | "body";
  koSize?: number; koCenterY?: number; koColor?: string; koOutline?: number;
  hookKoCenterY?: number; // translation under the hook phrase
  reveal?: "word" | "line"; // "line" (2026-10-22 사용자 결정): the whole spoken line appears at once, no word-by-word typing
};
// The hook (majunge patch, user decision 2026-10-09): instead of a headline at the top plus subtitles at the bottom, the
// hook's spoken words appear phrase by phrase, as they are spoken, in the thumbnail's look — heading font (젠세리프),
// a pastel gradient across the line, a faint shadow, the line tilted up to the right. One phrase at a time, centered.
export type GratitudeHook = {
  until: number; // s on the output timeline: the hook ends here, the normal subtitles take over
  size?: number;
  centerY?: number;
  gradient?: string[]; // left → right color stops (config/style.json thumb_gradient)
  tilt?: number; // degrees, right side up
  shadow?: { alpha?: number; blur?: number; dx?: number; dy?: number };
  maxChars?: number; // a phrase grows word by word up to this many letters (spaces not counted)
  gap?: number; // s of silence that starts a new phrase
  color?: string; // solid letter color instead of the gradient (2026-10-24 사용자 결정: #FCEED1)
  charStep?: number; // s per letter at most: a word types out letter by letter from its start (tools/gratitude.py keys = same timing)
};

// letter-by-letter timing of a hook phrase: the letters of each word are typed from the word's start, evenly over the
// word (at most charStep apart); a space appears with the next letter. tools/gratitude.py hook_keys() mirrors this.
export const typeTimes = (words: Word[], charStep = 0.11): number[] => {
  const out: number[] = [];
  words.forEach((w, i) => {
    const n = [...w.text].length;
    const step = Math.min(charStep, Math.max(0.03, (w.end - w.start) / Math.max(1, n)));
    if (i && !w.glue) out.push(w.start); // the space before the word
    for (let k = 0; k < n; k++) out.push(w.start + k * step);
  });
  return out;
};

// text-shadow for the spoken subtitles: the soft shadow alone (2026-10-24) or the old outline + shadow
const subShadow = (s: { outline: number; outlineColor: string; shadow: number; softShadow?: GratitudeStyle["softShadow"] }) => {
  if (!s.softShadow) return outlineShadow(s.outline, s.outlineColor, s.shadow);
  const sh = { alpha: 0.35, blur: 8, dx: 2, dy: 3, ...s.softShadow };
  const soft = `${sh.dx}px ${sh.dy}px ${sh.blur}px rgba(0,0,0,${sh.alpha})`;
  return s.outline > 0 ? `${outlineShadow(s.outline, s.outlineColor, 0)}, ${soft}` : soft;
};

export const GRATITUDE_DEFAULTS: Required<GratitudeStyle> = {
  size: 78, centerY: 1430, maxWidth: 842, weight: 700, color: "#FFFFFF", outline: 3, outlineColor: "#000000", shadow: 2,
  holdAfter: 0.25,
};

type Line = { words: Word[]; start: number; end: number; size: number };
const text = (ws: Word[]) => ws.map((w, k) => (k && !w.glue ? " " : "") + w.text).join("");
// 문장이 끝나면 다음 자막으로 (사용자 결정 2026-10-25, 21일차): 존댓말 문장 끝(~니다/~요/~죠) 또는 . ! ? 뒤에서 덩어리를 끊는다.
// buildChunks 는 seg 가 바뀌면 끊으므로, 문장 끝 다음 단어부터 seg 번호를 하나씩 올린다.
const SENT_END_KO = /(니다|요|죠)[.!?\u2026]*$|[.!?\u2026]$/;
const sentenceSegs = (ws: Word[], on: boolean): Word[] => {
  if (!on) return ws;
  let n = 0;
  return ws.map((w) => { const o = { ...w, seg: ((w as any).seg ?? 0) * 1000 + n } as Word; if (SENT_END_KO.test(w.text)) n += 1; return o; });
};

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
  headFont?: string;
  hook?: GratitudeHook | null;
}> = ({ captions, font, hide = [], tail = 0, style, headFont, hook }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ready = useFontsReady(headFont ? [font, headFont] : [font]);
  const until = hook?.until ?? 0;
  const hookPhrases = React.useMemo(() => {
    if (!hook) return [] as { words: Word[]; start: number }[];
    const maxChars = hook.maxChars ?? 9, gap = hook.gap ?? 0.25;
    const out: { words: Word[]; start: number }[] = [];
    let cur: Word[] = [];
    for (const w of captions.words.filter((x) => x.start < until)) {
      const len = cur.map((x) => x.text).join("").length;
      if (cur.length && (w.start - cur[cur.length - 1].end > gap || len + w.text.length > maxChars)) {
        out.push({ words: cur, start: cur[0].start });
        cur = [];
      }
      cur.push(w);
    }
    if (cur.length) out.push({ words: cur, start: cur[0].start });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [captions, until]);
  const s = { ...GRATITUDE_DEFAULTS, ...(style ?? {}) };
  const hideKey = JSON.stringify(hide);
  const lines = React.useMemo(() => {
    const words = captions.words.filter((w) => w.start >= until && !hide.some(([a, b]) => w.start >= a && w.end <= b));
    const width = (ws: Word[]) =>
      ready ? measureText({ text: text(ws), fontFamily: font, fontSize: s.size, fontWeight: s.weight }).width + 2 * s.outline : 0;
    // one sentence (or phrase between pauses) per subtitle; one that does not fit on one line is split where it reads as
    // two (the kit's bestSplit: pauses, commas, never after a short function word), each part on its own line
    const fit = (ws: Word[]): Word[][] => {
      if (ws.length < 2 || width(ws) <= s.maxWidth) return [ws];
      const k = bestSplit(ws);
      return [...fit(ws.slice(0, k)), ...fit(ws.slice(k))];
    };
    const dual = s.dual;
    const parts = dual && dual.lines.length
      ? dual.lines.map((d) => words.filter((w) => w.start >= d.start - 0.05 && w.start < d.end)).filter((ws) => ws.length)
      : buildChunks(sentenceSegs(words, (s as any).sentenceBreak !== false), 40, 200).flatMap((c) => fit(c.words));
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
  }, [captions, hideKey, font, ready, s.size, s.maxWidth, s.weight, s.outline, s.holdAfter, tail, until, s.dual]);
  const t = frame / fps;
  if (hook && t < until) {
    // one phrase at a time: it appears with its first word and stays until the next phrase (the last one: to the hook's end)
    const k = hookPhrases.findIndex((ph, i) => t >= ph.start - 0.03 && (i === hookPhrases.length - 1 || t < hookPhrases[i + 1].start - 0.03));
    if (k < 0) return null;
    const size = hook.size ?? 96, cy = hook.centerY ?? s.centerY;
    const full = text(hookPhrases[k].words);
    const times = typeTimes(hookPhrases[k].words, hook.charStep ?? 0.11);
    const shown = times.filter((x) => t >= x - 0.01).length;
    const hf = headFont ?? font;
    const pad = size * 0.08;
    const fullW = ready ? measureText({ text: full, fontFamily: hf, fontSize: size }).width : 0;
    const shownW = ready ? measureText({ text: full.slice(0, shown), fontFamily: hf, fontSize: size }).width : 0;
    const stops = (hook.gradient ?? ["#DDF0D2", "#FFF6E6", "#F6D3E3", "#E8DAF2", "#FFF6E6", "#DDF0D2"]).join(", ");
    const sh = { alpha: 0.4, blur: 6, dx: 3, dy: 4, ...(hook.shadow ?? {}) };
    const hookKo = s.dual ? s.dual.lines.find((d) => d.start < until && t >= d.start - 0.05 && t < Math.max(d.end, until)) : null;
    const koS = s.dual?.koSize ?? 58;
    return (
      <>
      {hookKo && hookKo.ko ? (
        <div style={{ position: "absolute", left: 0, width: 1080, top: (s.dual?.hookKoCenterY ?? cy + size * 0.95) - (koS * 1.25) / 2,
          textAlign: "center", fontFamily: font, fontWeight: s.weight, lineHeight: 1.25, whiteSpace: "pre", color: s.dual?.koColor ?? s.color,
          fontSize: Math.min(koS, fitSize({ text: hookKo.ko, size: koS, font, weight: s.weight, maxWidth: s.maxWidth, ready })),
          textShadow: outlineShadow(s.dual?.koOutline ?? s.outline, s.outlineColor, s.shadow) }}>{hookKo.ko}</div>
      ) : null}
      <div style={{ position: "absolute", left: 0, width: 1080, top: cy - size * 0.7, height: size * 1.4, display: "flex",
        alignItems: "center", justifyContent: "center" }}>
        {/* the whole phrase is laid out once (centered) and typed out in place, letter by letter: a clip from the right
            hides the letters not yet typed, so the gradient keeps its place across the line */}
        <span style={{ display: "inline-block", fontFamily: hf, fontSize: size, lineHeight: 1.2, whiteSpace: "pre",
          padding: `0 ${pad}px`, ...(hook.color ? { color: hook.color } : { backgroundImage: `linear-gradient(90deg, ${stops})`, WebkitBackgroundClip: "text",
          backgroundClip: "text", color: "transparent" }), transform: `rotate(${-(hook.tilt ?? 0)}deg)`,
          clipPath: `inset(-30% ${Math.max(0, fullW - shownW + pad)}px -30% -30%)`,
          filter: `drop-shadow(${sh.dx}px ${sh.dy}px ${sh.blur}px rgba(0,0,0,${sh.alpha}))` }}>
          {full}
        </span>
      </div>
      </>
    );
  }
  if (hide.some(([a, b]) => t >= a && t < b)) return null;
  const l = lines.find((x) => t >= x.start - 0.03 && t < x.end);
  if (!l) return null;
  const lh = 1.25;
  if (s.dual) {
    const d = s.dual;
    const enFont = d.enFont === "body" ? font : headFont ?? font;
    const enS = d.enSize ?? 62, koS = d.koSize ?? 58;
    const enSize = Math.min(enS, fitSize({ text: text(l.words), size: enS, font: enFont, weight: 400, maxWidth: s.maxWidth, ready }));
    const ko = d.lines.find((x) => l.start >= x.start - 0.05 && l.start < x.end)?.ko ?? "";
    const koSize = Math.min(koS, fitSize({ text: ko, size: koS, font, weight: s.weight, maxWidth: s.maxWidth, ready }));
    return (
      <>
        <div style={{ position: "absolute", left: 0, width: 1080, top: (d.enCenterY ?? 1370) - (enSize * lh) / 2, textAlign: "center",
          fontFamily: enFont, fontSize: enSize, lineHeight: lh, color: d.enColor ?? "#FFF1C1", whiteSpace: "pre",
          textShadow: outlineShadow(d.enOutline ?? 2.5, s.outlineColor, s.shadow) }}>
          {l.words.map((w, k) => (
            <span key={k} style={{ opacity: d.reveal === "line" || w === l.words[0] || t >= w.start - 0.03 ? 1 : 0 }}>
              {k && !w.glue ? " " : ""}
              {w.text}
            </span>
          ))}
        </div>
        {ko ? (
          <div style={{ position: "absolute", left: 0, width: 1080, top: (d.koCenterY ?? 1450) - (koSize * lh) / 2, textAlign: "center",
            fontFamily: font, fontWeight: s.weight, fontSize: koSize, lineHeight: lh, color: d.koColor ?? s.color, whiteSpace: "pre",
            textShadow: outlineShadow(d.koOutline ?? s.outline, s.outlineColor, s.shadow) }}>{ko}</div>
        ) : null}
      </>
    );
  }
  return (
    <div style={{ position: "absolute", left: 0, width: 1080, top: s.centerY - (l.size * lh) / 2, textAlign: "center",
      fontFamily: font, fontWeight: s.weight, fontSize: l.size, lineHeight: lh, color: s.color, whiteSpace: "pre",
      textShadow: subShadow(s) }}>
      {l.words.map((w, k) => (
        // words not yet spoken keep their place (the line is laid out once), they are only invisible
        <span key={k} style={{ opacity: s.reveal === "line" || w === l.words[0] || t >= w.start - 0.03 ? 1 : 0 }}>
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
     '        <Media ins={ins} style={{ width: b[2], height: b[3], objectFit: "contain", maxWidth: "none" }} zoom={!!ins.zoom_to} />\n'
     '      </div>\n'
     '    );\n'
     '  } else if (ins.mode === "window") {'),
    ("ReelKit.tsx",
     'import { Captions, KitSubtitles, SubtitleMode } from "./kit/Subtitles";',
     'import { Captions, KitSubtitles, SubtitleMode } from "./kit/Subtitles";\n'
     'import { GratitudeHook, GratitudeStyle, GratitudeSubtitles } from "./kit/GratitudeSubtitles"; // majunge patch'),
    ("ReelKit.tsx",
     '  subtitlesTop?: number;',
     '  gratitude?: GratitudeStyle | null; // majunge patch — subtitles "gratitude": its style (tools/gratitude.py props)\n'
     '  gratitudeHook?: GratitudeHook | null; // majunge patch — the hook spoken phrases in the thumbnail style\n'
     '  subtitlesTop?: number;'),
    ("ReelKit.tsx",
     '      <KitSubtitles captions={p.subtitleCaptions ?? p.captions} brand={p.brand} font={fonts.body} mode={p.subtitles} hide={hide}\n'
     '        top={p.subtitlesTop ?? 1290} look={look} shade={p.subtitlesShade ?? 0.35} part="text" tail={tail} {...subArea} />',
     '      {p.subtitles === "gratitude" ? ( // majunge patch\n'
     '        <GratitudeSubtitles captions={p.subtitleCaptions ?? p.captions} font={fonts.body} hide={hide} tail={tail} style={p.gratitude}\n'
     '          headFont={fonts.heading} hook={p.gratitudeHook} />\n'
     '      ) : (\n'
     '        <KitSubtitles captions={p.subtitleCaptions ?? p.captions} brand={p.brand} font={fonts.body} mode={p.subtitles} hide={hide}\n'
     '          top={p.subtitlesTop ?? 1290} look={look} shade={p.subtitlesShade ?? 0.35} part="text" tail={tail} {...subArea} />\n'
     '      )}'),
    ("kit/Inserts.tsx",
     '    const z = zoom ? interpolate(frame, [0, ins.dur * fps], [1, 1.06], clamp) : 1;',
     '    // majunge patch: the end scale can come from the plan (card push-in); linear and sub-pixel, so it never shakes\n'
     '    const z = zoom ? interpolate(frame, [0, ins.dur * fps], [1, ins.zoom_to ?? 1.06], clamp) : 1;'),
    ("kit/Inserts.tsx",
     '  box?: [number, number, number, number] | number[] | null;\n};',
     '  box?: [number, number, number, number] | number[] | null;\n'
     '  zoom_to?: number; // majunge patch — card: end scale of a slow, smooth push-in (photos drawn by the kit)\n};'),
]

# 예전 버전 패치가 들어간 키트를 새 버전으로 옮긴다 (파일, 예전 패치 결과, 새 패치 결과) — patch-kit 이 EDITS 전에 적용
MIGRATIONS = [
    ('kit/Inserts.tsx',
     '        <Media ins={ins} style={{ width: b[2], height: b[3], objectFit: "contain", maxWidth: "none" }} />\n',
     '        <Media ins={ins} style={{ width: b[2], height: b[3], objectFit: "contain", maxWidth: "none" }} zoom={!!ins.zoom_to} />\n'),
    ('ReelKit.tsx',
     '<GratitudeSubtitles captions={p.subtitleCaptions ?? p.captions} font={fonts.body} hide={hide} tail={tail} style={p.gratitude} />',
     '<GratitudeSubtitles captions={p.subtitleCaptions ?? p.captions} font={fonts.body} hide={hide} tail={tail} style={p.gratitude}\n          headFont={fonts.heading} hook={p.gratitudeHook} />'),
    ('ReelKit.tsx',
     'import { GratitudeStyle, GratitudeSubtitles } from "./kit/GratitudeSubtitles"; // majunge patch',
     'import { GratitudeHook, GratitudeStyle, GratitudeSubtitles } from "./kit/GratitudeSubtitles"; // majunge patch'),
    ('ReelKit.tsx',
     '  gratitude?: GratitudeStyle | null; // majunge patch — subtitles "gratitude": its style (tools/gratitude.py props)',
     '  gratitude?: GratitudeStyle | null; // majunge patch — subtitles "gratitude": its style (tools/gratitude.py props)\n  gratitudeHook?: GratitudeHook | null; // majunge patch — the hook spoken phrases in the thumbnail style'),
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
    for f, old, new in MIGRATIONS:
        p = src / f
        s = p.read_text(encoding="utf-8")
        if new not in s and s.count(old) == 1:
            p.write_text(s.replace(old, new), encoding="utf-8")
            changed.append(f)
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
        print("키트에 감사일기 모드가 없어요 (kit.py update 뒤라면 정상) → python3 styles/gratitude/render.py patch-kit")
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


def hook_until(edit: Path) -> float | None:
    """훅(cut.json beat "hook") 구간이 끝나는 출력 초. 맨 앞 range 들이 hook 일 때만."""
    try:
        cut = json.loads((edit / "cut.json").read_text(encoding="utf-8"))
        cap = json.loads((edit / "captions.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    end = None
    for r, sg in zip(cut.get("ranges", []), cap.get("segments", [])):
        if r.get("beat") != "hook":
            break
        end = sg["out_start"] + sg["out_dur"]
    return end


def hook_keys(edit: Path, hook: dict) -> list[float]:
    """훅 자막이 한 글자씩 나오는 시각들 (키보드 효과음 자리). 키트 GratitudeSubtitles.typeTimes 와 같은 계산."""
    cap = json.loads((edit / "captions.json").read_text(encoding="utf-8"))
    until, step_max = hook["until"], hook.get("charStep", 0.11)
    out = []
    for w in cap["words"]:
        if w["start"] >= until:
            break
        n = len(w["text"])
        step = min(step_max, max(0.03, (w["end"] - w["start"]) / max(1, n)))
        out += [round(w["start"] + k * step, 3) for k in range(n)]
    return out


def safe_zone() -> dict | None:
    """릴스 화면 안전영역 (모든 스타일 공통, config/safe_zone.json — 사용자 결정 2026-10-25). {"x": [좌, 우], "y": [위, 아래]}"""
    p = ROOT / "config" / "safe_zone.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def in_safe(box: list) -> list:
    """[x, y, w, h] 상자를 안전영역 안으로 줄인다 (비율 유지하지 않음 — 키트가 상자 안에 사진을 맞춰 그린다)."""
    sz = safe_zone()
    if not sz:
        return box
    x, y, w, h = box
    x0, x1 = max(x, sz["x"][0]), min(x + w, sz["x"][1])
    y0, y1 = max(y, sz["y"][0]), min(y + h, sz["y"][1])
    return [round(x0), round(y0), round(x1 - x0), round(y1 - y0)]


def face_center(video: Path, t: float) -> tuple[int, int] | None:
    """영상 t 초 프레임에서 가장 큰 얼굴의 (위쪽 y, 가운데 y), 1920 높이 기준 (훅 자리 자동 결정, 2026-10-24)."""
    try:
        import cv2
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=540:960",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        img = np.frombuffer(raw, np.uint8).reshape(960, 540, 3).copy()
        model = ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
        det = cv2.FaceDetectorYN.create(str(model), "", (540, 960), 0.6, 0.3, 50)
        _, faces = det.detect(img)
        if faces is None or not len(faces):
            return None
        x, y, w, h = max((f[:4] for f in faces), key=lambda b: b[2] * b[3])
        return int(y * 2), int((y + h / 2) * 2)
    except Exception as e:  # noqa: BLE001
        print(f"  ! 얼굴 검출 실패 ({e}) — 훅은 기본 자리")
        return None


def head_top(video: Path, t: float) -> int | None:
    """영상 t 초 프레임에서 머리끝(머리카락 포함) y, 1920 높이 기준 (사용자 결정 2026-10-25: 훅은 머리끝 위에 여유를 두고).
    얼굴 상자 가운데 폭의 줄별 밝기를 이마에서 위로 훑어, 어두운 머리카락이 끝나고 밝은 배경이 3줄 이어지는 곳.
    못 찾으면 얼굴 위쪽 − 얼굴 높이 × 0.45 로 어림."""
    try:
        import cv2
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=1080:1920",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
        img = np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).copy()
        model = ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
        det = cv2.FaceDetectorYN.create(str(model), "", (1080, 1920), 0.6, 0.3, 50)
        _, faces = det.detect(img)
        if faces is None or not len(faces):
            return None
        x, y, w, h = [int(v) for v in max((f[:4] for f in faces), key=lambda b: b[2] * b[3])]
        rows = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[:, max(0, x + w // 4):x + 3 * w // 4].mean(axis=1)
        fallback = int(y - h * 0.45)
        for r in range(y - 5, 3, -1):
            if rows[r] > 120 and rows[r - 1] > 120 and rows[r - 2] > 120:
                return r if r >= fallback - h * 0.3 else fallback  # 너무 멀리 가면(어두운 배경) 어림값
        return fallback
    except Exception as e:  # noqa: BLE001
        print(f"  ! 머리끝 검출 실패 ({e})")
        return None


def hook_center_y(edit: Path, hook: dict, until: float) -> float:
    """훅 글씨 세로 자리 (사용자 결정 2026-10-24): 촬영 원본의 얼굴이 화면 가운데보다 아래면 머리 위(상단), 위면 하단(hook.centerY).
    훅 구간 가운데 프레임(edit/<id>/final.mp4 — 훅 확대가 들어간 실제 화면)에서 얼굴을 찾는다."""
    bottom = float(hook.get("centerY", 1430))
    if hook.get("autoPos", True) is False:
        return bottom
    # 위/아래는 촬영 원본(확대 전) 얼굴로 정하고, 머리 위 자리는 실제 화면(final.mp4, 훅 확대 포함)의 얼굴 위쪽으로 잡는다
    src_fc = None
    try:
        cut = json.loads((edit / "cut.json").read_text(encoding="utf-8"))
        r0 = cut["ranges"][0]
        srcs = cut.get("sources", {})
        main = srcs.get("main") or srcs.get(r0.get("source", "main"))
        f = Path(main["file"]) if Path(main["file"]).is_absolute() else ROOT / main["file"]
        src_fc = face_center(f, (r0["start"] + r0["end"]) / 2)
    except Exception as e:  # noqa: BLE001
        print(f"  ! 원본 얼굴 위치를 못 읽음 ({e}) — 화면 기준")
    fc = face_center(edit / "final.mp4", max(0.0, until / 2))
    if not (src_fc or fc):
        return bottom
    mid = (src_fc or fc)[1]
    always = bool(hook.get("alwaysAbove"))  # 사용자 결정 2026-10-25: 얼굴 위치와 상관없이 머리 위, 안전영역 안
    if not fc or (mid <= 960 and not always):
        return bottom
    top = fc[0]
    size = float(hook.get("size", 96))
    # 머리끝(머리카락 포함) 기준 — 훅 구간에서 머리가 가장 높이 올라간 순간 (2026-10-25)
    tops = [ht for ht in (head_top(edit / "final.mp4", until * k) for k in (0.2, 0.5, 0.8)) if ht]
    if tops:
        top = min(tops)
    y = max(float(hook.get("topMin", 330)), top - size * 0.6 - float(hook.get("headGap", 20)))
    sz = safe_zone()
    if sz:
        y = max(y, sz["y"][0] + size * 0.75)  # 글자 윗부분이 안전영역 위로 나가지 않게
    print(f"훅 자리: 머리끝 y {top} → 훅 가운데 y {round(y)}" + (" (안전영역 안)" if sz else ""))
    return round(y)


def peak_db(path: Path) -> float | None:
    """소리의 최대 레벨(dBFS) — master_audio 가 효과음 크기를 정하는 기준과 같다."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "max_volume:" in line:
            return float(line.split("max_volume:")[1].split()[0])
    return None


def cmd_keys(a) -> None:
    """edit/<id>/sfx.json 에 훅 타이핑(key)·"감사합니다" 딸깍(click) 효과음을 넣는다 (같은 종류는 다시 계산해 바꿈)."""
    c = config()
    edit = Path(a.edit)
    until = hook_until(edit)
    p = edit / "sfx.json"
    sfx = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"below_voice_db": 15, "sounds": []}
    keep = [x for x in sfx["sounds"] if x.get("what") not in ("훅 타이핑", "감사합니다 딸깍", "감사합니다 효과음")]
    snd = c.get("sounds", {})
    added = []
    if until and c.get("hook") and snd.get("key"):
        keys = snd["key"] if isinstance(snd["key"], list) else [snd["key"]]
        for i, t in enumerate(hook_keys(edit, {**c["hook"], "until": until})):
            # 높이가 조금씩 다른 키 소리를 돌아가며 (같은 소리 반복은 기계음처럼 들림)
            added.append({"file": keys[(i * 3 + i // 2) % len(keys)], "at": t, "start": 0.0, "what": "훅 타이핑"})
    if snd.get("click"):
        cap = json.loads((edit / "captions.json").read_text(encoding="utf-8"))
        dur = float(cap.get("duration") or 0) or None
        # 말 첫 음절과 겹치면 목소리에 묻힌다 (2026-10-10 확인) → 말이 끝나는 순간에, 목소리보다 click_below_db 만 낮게
        gain = None
        if snd.get("click_below_db") is not None:
            voice = peak_db(edit / "final.mp4")
            cpk = peak_db(ROOT / snd["click"])
            if voice is not None and cpk is not None:
                gain = round(voice - float(snd["click_below_db"]) - cpk, 1)
        for w in cap["words"]:
            if w["text"].rstrip(".!") in snd.get("click_words", ["감사합니다", "감사했습니다"]):
                at = w["end"] - 0.03 if snd.get("click_at", "end") == "end" else w["start"]
                if dur:
                    at = min(at, dur - 0.15)  # 소리가 영상 끝에서 잘리지 않게
                x = {"file": snd["click"], "at": round(at, 3), "start": 0.0, "what": "감사합니다 효과음"}
                if gain is not None:
                    x["gain_db"] = gain
                added.append(x)
    sfx["sounds"] = sorted(keep + added, key=lambda x: x["at"])
    p.write_text(json.dumps(sfx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"효과음: 훅 타이핑 {sum(x['what'] == '훅 타이핑' for x in added)}개, 감사합니다 효과음 "
          f"{sum(x['what'] == '감사합니다 효과음' for x in added)}개 → {p}")


def photo_source(edit: Path, ins_id: str) -> Path | None:
    """visual_plan.json 에서 그 인서트가 고른 프로젝트 사진 (블러본) 경로."""
    try:
        plan = json.loads((edit / "visual_plan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for ins in plan.get("inserts", []):
        if ins.get("id") == ins_id:
            cand = ins.get("candidate") or {}
            for k in ("id", "path"):
                q = cand.get(k)
                if q and (ROOT / q if not Path(q).is_absolute() else Path(q)).suffix.lower() in IMAGE_EXT:
                    q = ROOT / q if not Path(q).is_absolute() else Path(q)
                    if q.exists():
                        return q
    return None


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def cmd_props(a) -> None:
    rem = remotion_dir(a.remotion)
    miss = status(rem)
    if miss:
        sys.exit("[오류] 키트에 감사일기 모드가 없어요 → python3 styles/gratitude/render.py patch-kit 먼저")
    c = config()
    p = Path(a.props)
    props = json.loads(p.read_text(encoding="utf-8"))
    props["subtitles"] = "gratitude"
    props["gratitude"] = dict(c["subtitles"])
    if getattr(a, "dual", None):  # 두 언어 자막 (2026-10-22): edit/<id>/dual.json = {"style": {...}, "lines": [...]}
        dj = json.loads(Path(a.dual).read_text(encoding="utf-8"))
        props["gratitude"]["dual"] = {**c.get("dual", {}), **dj.get("style", {}), "lines": dj["lines"]}
    props["drift"] = False  # 레퍼런스: 줌 없음
    props.pop("camera", None)
    props["hook"] = None  # (pop 하면 템플릿 기본 문구가 나온다) 위쪽 훅 문구 대신 훅 자막(gratitudeHook) — 사용자 결정 2026-10-09
    hook_end = hook_until(Path(a.edit)) if a.edit else None
    if hook_end and c.get("hook"):
        sys.path.insert(0, str(ROOT / "tools"))
        from thumbs import load_style  # 썸네일 공통 스펙(config/thumb.json)까지 따라감
        grad = load_style(STYLE.name).get("thumb_gradient")
        props["gratitudeHook"] = {**c["hook"], "until": round(hook_end, 3), **({"gradient": grad} if grad else {})}
        props["gratitudeHook"]["centerY"] = hook_center_y(Path(a.edit), c["hook"], hook_end)  # 얼굴 위치로 위/아래 (2026-10-24)
        # 훅 문구와 겹치지 않게 숨겨 두던 창은 이제 필요 없다 (훅 자막이 그 자리)
        props["hideSubtitles"] = [h for h in props.get("hideSubtitles") or [] if not (h[0] <= 0.05 and h[1] <= hook_end + 0.5)]
    cards = pips = 0
    for ins in props.get("inserts", []):
        if ins.get("kind") != "broll" or ins.get("mode") not in ("replace", "window", "card"):
            continue
        ins["mode"] = "card"
        ins["transition_in"] = ins["transition_out"] = "cut"
        photo = photo_source(Path(a.edit), ins["id"]) if a.edit else None
        if photo and c.get("card_zoom", 1.0) > 1.0:
            # 사진은 미리 만든 확대 영상(zoompan: 픽셀 단위로 움직여 떨림) 대신 원본(블러본)을 키트가 직접 그리며 부드럽게 확대
            dst = rem / "public" / Path(ins["file"]).parent.parent / "photos" / (ins["id"] + photo.suffix.lower())
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(photo, dst)
            ins["file"] = dst.relative_to(rem / "public").as_posix()
            ins["media"] = "image"
            ins["src_in"] = 0.0
            ins["zoom_to"] = float(c["card_zoom"])
        size = media_size(rem / "public" / ins["file"])
        if ins.get("media") == "image" and size and size[0] > size[1] * float(c["pip_if_wider_than"]):
            # 가로 사진: 작게 위쪽 (레퍼런스 PiP, 폭 55 %, 세로 중심 40 %)
            w = round(1080 * c["pip"]["w"])
            h = min(round(w * size[1] / size[0]), round(1920 * c["pip"]["max_h"]))
            ins["box"] = in_safe([round((1080 - w) / 2), round(1920 * c["pip"]["center_y"] - h / 2), w, h])
            pips += 1
        else:
            ins["box"] = in_safe(list(c["card"]))  # 안전영역 안 (2026-10-25)
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
    q.add_argument("--dual", help="두 언어 자막: edit/<id>/dual.json (위 = 말한 언어, 아래 = 번역)")
    q = sp.add_parser("keys", help="훅 타이핑·감사합니다 효과음을 sfx.json 에 넣기")
    q.add_argument("--edit", required=True)
    a = ap.parse_args()
    {"patch-kit": cmd_patch, "check": cmd_check, "props": cmd_props, "keys": cmd_keys}[a.cmd](a)


if __name__ == "__main__":
    main()
