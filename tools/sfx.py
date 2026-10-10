"""기본 효과음 4종을 assets/sfx/ 에 만든다 (저작권 걱정 없는 합성음).

    python3 tools/sfx.py

whoosh(장면 전환) · pop(감사 제목 등장) · ding(마무리·깨달음) · rise(훅→본론 넘어갈 때)
key1~4(훅 자막이 한 글자씩 나올 때 키보드 타닥타닥, 높이가 조금씩 다른 4가지) · click("감사합니다"마다 마우스 딸깍)
— key·click 은 2026-10-10 사용자가 들어 보고 고른 소리 (덜 날카롭게 다듬은 버전). 같은 seed 라 매번 똑같이 만들어진다.
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


# ---- 키보드 타닥 · 마우스 딸깍 (numpy 합성, 사용자 승인 2026-10-10) ----
def _numpy_sounds(out_dir: Path) -> None:
    import wave
    import numpy as np
    SR = 48000
    rng = np.random.default_rng(7)

    def save(path: Path, x):
        x = x / (np.abs(x).max() + 1e-9) * 0.8
        y = np.stack([x, x], 1)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((y * 32767).astype(np.int16).tobytes())

    def bp(x, lo, hi):
        X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
        m = np.convolve(((f >= lo) & (f <= hi)).astype(float), np.ones(40) / 40, "same")
        return np.fft.irfft(X * m, len(x))

    def soften(x, cut=4200):  # 귀를 찌르는 고음을 부드럽게 (1차 로우패스 두 번)
        a = np.exp(-2 * np.pi * cut / SR); y = x.copy()
        for _ in range(2):
            z = np.zeros_like(y); acc = 0.0
            for i, v in enumerate(y):
                acc = (1 - a) * v + a * acc; z[i] = acc
            y = z
        return y

    def burst(dur, decay, lo, hi):
        n = int(SR * dur); t = np.arange(n) / SR
        return bp(rng.standard_normal(n), lo, hi) * np.exp(-t / decay)

    def key(v):  # 키캡이 눌리는 '타' + 바닥에 닿는 '닥'
        f = [2200, 1950, 2450, 2100][v]; amp = [1.0, 0.95, 1.05, 0.9][v]
        x = np.zeros(int(SR * 0.07))
        a = burst(0.016, 0.0026, 900, f * 1.6) * amp
        m = int(SR * 0.014); t = np.arange(m) / SR
        x[:len(a)] += a; x[:m] += np.sin(2 * np.pi * (f * 0.32) * t) * np.exp(-t / 0.0025) * 0.5
        off = int(SR * (0.02 + 0.004 * v)); b = burst(0.014, 0.0022, 600, 3000) * 0.55
        x[off:off + len(b)] += b
        return soften(x)

    def click():  # 마우스 버튼: 누를 때 '딸', 뗄 때 '깍' (0.075초 간격)
        x = np.zeros(int(SR * 0.13))
        def tick(f, amp, dec):
            m = int(SR * 0.012); t = np.arange(m) / SR
            return (np.sin(2 * np.pi * f * t) * 0.7 + bp(rng.standard_normal(m), 1200, 4500)) * np.exp(-t / dec) * amp
        a = tick(2600, 1.0, 0.0018); b = tick(2200, 0.65, 0.0015)
        x[:len(a)] += a; o = int(SR * 0.075); x[o:o + len(b)] += b
        return soften(x, 3800)

    keys = [key(v) for v in range(4)]  # 생성 순서가 seed 결과를 정하므로 key → click 순서를 지킨다
    c = click()
    for i, k in enumerate(keys, 1):
        out = out_dir / f"key{i}.wav"
        if out.exists():
            print(f"있음: {out.relative_to(ROOT)}")
        else:
            save(out, k); print(f"생성: {out.relative_to(ROOT)}")
    out = out_dir / "click.wav"
    if out.exists():
        print(f"있음: {out.relative_to(ROOT)}")
    else:
        save(out, c); print(f"생성: {out.relative_to(ROOT)}")


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
    _numpy_sounds(out_dir)


if __name__ == "__main__":
    main()
