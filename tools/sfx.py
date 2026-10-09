"""기본 효과음 4종을 assets/sfx/ 에 만든다 (저작권 걱정 없는 합성음).

    python3 tools/sfx.py

whoosh(장면 전환) · pop(감사 제목 등장) · ding(마무리·깨달음) · rise(훅→본론 넘어갈 때)
직접 고른 효과음·BGM은 assets/sfx/, assets/music/ 에 넣으면 오디오 담당이 함께 고른다.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX = {
    "whoosh.wav": ("0.6*(random(0)*2-1)*sin(PI*t/0.45)*exp(-1.5*t)", 0.45),
    "pop.wav": ("0.8*sin(2*PI*(620-900*t)*t)*exp(-28*t)", 0.18),
    "ding.wav": ("0.5*(sin(2*PI*1318*t)+0.5*sin(2*PI*2637*t))*exp(-5*t)", 1.0),
    "rise.wav": ("0.4*sin(2*PI*(300+1400*t*t)*t)*sin(PI*t/0.7)", 0.7),
}


def main() -> None:
    out_dir = ROOT / "assets" / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (expr, d) in SFX.items():
        out = out_dir / name
        if out.exists():
            print(f"있음: {out.relative_to(ROOT)}")
            continue
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                        "-i", f"aevalsrc='{expr}':s=48000:c=stereo:d={d}",
                        "-af", f"highpass=f=120,afade=t=out:st={d - 0.05:.2f}:d=0.05", str(out)],
                       check=True)
        print(f"생성: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
