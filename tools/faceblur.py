"""[B-roll 얼굴 블러] B-roll 사진·영상에 나온 다른 사람 얼굴을 찾아 블러 처리한다.

1) scan  : 얼굴을 찾고, 영상은 프레임 사이로 같은 사람을 이어 붙여(트랙) 번호를 매긴다.
           → <폴더>/_faces/plan.json + 검토 시트(review-NN.jpg, 얼굴마다 번호 박스)
           기본값은 "찾은 얼굴 전부 블러". 마정이 본인 얼굴만 plan.json 의 keep 에 번호를 넣어 뺀다.
           영상에서 딱 한 번 잡힌 약한 검출(weak)은 오검출이 많아 keep 에 미리 들어 있다 —
           시트에서 진짜 얼굴이면 keep 에서 빼서 블러되게 한다.
2) apply : plan.json 대로 블러한 사본을 만든다 (원본은 그대로 둔다).
           → footage/<id>/broll_blur/  (화면연결 담당은 이 폴더를 B-roll로 쓴다)
           얼굴이 없는 파일도 그대로 복사해 두어, 이 폴더 하나만 보면 되게 한다.
3) check : 블러된 결과에서 다시 얼굴을 찾아, 놓친 얼굴이 남았는지 시트로 확인.

    python3 tools/faceblur.py scan  footage/<id>/broll
    python3 tools/faceblur.py apply footage/<id>/broll [--style blur|mosaic] [--pad 0.35]
    python3 tools/faceblur.py check footage/<id>/broll_blur

plan.json:
    {"files": {"IMG_01.jpg": {"kind": "image", "tracks": [{"id": 1, "boxes": [[t, x, y, w, h], ...]}, ...],
                              "keep": [], "extra": []}}}
    · keep  : 블러하지 않을 트랙 번호 (마정이 본인 등)
    · extra : 검출이 놓친 얼굴을 손으로 추가 [[시작초, 끝초, x, y, w, h], ...] (사진은 0, 0)

검출기: it-reelsmaker.json 의 face_model(YuNet .onnx)이 있으면 그걸, 없으면 OpenCV 기본 검출기(정면+옆얼굴).
기본 검출기는 작거나 많이 돌아간 얼굴을 놓칠 수 있다 → check 시트를 반드시 눈으로 본다.
개인정보 보호가 우선이라 애매하면 블러하는 쪽으로 판단한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
SCAN_FPS = 5            # 영상은 초당 5장 검사
HOLD = 0.6              # 검출이 잠깐 끊겨도 이 시간(초)까지는 블러를 유지
DET_W = 960             # 검출용 축소 폭


YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
             "face_detection_yunet_2023mar.onnx")


def fetch_yunet() -> str | None:
    """YuNet 얼굴 모델(약 230KB)을 처음 한 번 받아 assets/models/ 에 두고,
    IT Reelsmaker도 같은 모델로 얼굴 위치를 재도록 it-reelsmaker.json 의 face_model 에 등록한다."""
    import urllib.request
    dst = ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
    if not (dst.exists() and dst.stat().st_size > 100_000):
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            print("얼굴 검출 모델(YuNet) 내려받는 중 …")
            urllib.request.urlretrieve(YUNET_URL, dst)
        except Exception as e:  # 네트워크 없음 등
            print(f"  ! 모델 다운로드 실패({e}) — OpenCV 기본 검출기로 진행")
            dst.unlink(missing_ok=True)
            return None
        if dst.stat().st_size < 100_000:          # LFS 포인터 등 잘못 받은 경우
            dst.unlink()
            return None
    cfg = ROOT / "it-reelsmaker.json"
    data = json.loads(cfg.read_text(encoding="utf-8")) if cfg.exists() else {}
    if not data.get("face_model"):
        data["face_model"] = str(dst)
        cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(dst)


def need_cv2():
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        sys.exit("[오류] OpenCV가 필요해요: python3 -m pip install opencv-python-headless numpy")


class Detector:
    def __init__(self) -> None:
        import cv2
        self.cv2 = cv2
        self.yunet = None
        model = ""
        cfg = ROOT / "it-reelsmaker.json"
        if cfg.exists():
            model = json.loads(cfg.read_text(encoding="utf-8")).get("face_model", "") or ""
            if model and not Path(model).expanduser().is_absolute():
                model = str(ROOT / model)
        if not (model and Path(model).expanduser().exists()) and hasattr(cv2, "FaceDetectorYN"):
            model = fetch_yunet() or ""
        if model and Path(model).expanduser().exists():
            self.yunet = cv2.FaceDetectorYN.create(str(Path(model).expanduser()), "", (320, 320), 0.6, 0.3, 5000)
            self.name = "YuNet"
        elif not hasattr(cv2, "CascadeClassifier"):
            sys.exit("[오류] 얼굴 검출 모델이 없어요. 아래 파일을 받아 assets/models/ 에 넣어 주세요:\n  " + YUNET_URL)
        else:
            base = Path(cv2.data.haarcascades)
            self.front = cv2.CascadeClassifier(str(base / "haarcascade_frontalface_default.xml"))
            self.front2 = cv2.CascadeClassifier(str(base / "haarcascade_frontalface_alt2.xml"))
            self.profile = cv2.CascadeClassifier(str(base / "haarcascade_profileface.xml"))
            self.name = "OpenCV 기본(Haar)"

    def detect(self, img) -> list[list[int]]:
        cv2 = self.cv2
        h, w = img.shape[:2]
        k = min(1.0, DET_W / w)
        small = cv2.resize(img, (int(w * k), int(h * k))) if k < 1 else img
        boxes = []
        if self.yunet is not None:
            self.yunet.setInputSize((small.shape[1], small.shape[0]))
            _, faces = self.yunet.detect(small)
            for f in faces if faces is not None else []:
                boxes.append([int(v / k) for v in f[:4]])
        else:
            g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
            ms = max(24, int(min(small.shape[:2]) * 0.035))
            found = []
            for casc, flip in ((self.front, False), (self.front2, False),
                               (self.profile, False), (self.profile, True)):
                src = cv2.flip(g, 1) if flip else g
                for (x, y, bw, bh) in casc.detectMultiScale(src, 1.08, 6, minSize=(ms, ms)):
                    if flip:
                        x = src.shape[1] - x - bw
                    found.append([int(x / k), int(y / k), int(bw / k), int(bh / k)])
            boxes = merge(found)
        return boxes


def iou(a, b) -> float:
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    return inter / float(a[2] * a[3] + b[2] * b[3] - inter or 1)


def merge(boxes: list[list[int]]) -> list[list[int]]:
    out: list[list[int]] = []
    for b in sorted(boxes, key=lambda b: -b[2] * b[3]):
        if all(iou(b, o) < 0.3 for o in out):
            out.append(b)
    return out


def track(dets: list[tuple[float, list[list[int]]]]) -> list[dict]:
    """프레임별 검출을 IoU·거리로 이어 붙여 사람별 트랙으로."""
    tracks: list[dict] = []
    for t, boxes in dets:
        for b in boxes:
            best, score = None, 0.0
            for tr in tracks:
                lt, *lb = tr["boxes"][-1]
                if t - lt > 1.5:
                    continue
                s = iou(b, lb)
                cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
                lx, ly = lb[0] + lb[2] / 2, lb[1] + lb[3] / 2
                if s == 0 and abs(cx - lx) < lb[2] * 0.8 and abs(cy - ly) < lb[3] * 0.8:
                    s = 0.15
                if s > score and lt < t:
                    best, score = tr, s
            if best is not None and score >= 0.1:
                best["boxes"].append([round(t, 3), *b])
            else:
                tracks.append({"id": len(tracks) + 1, "boxes": [[round(t, 3), *b]]})
    # 한 번만 잡힌 영상 속 오검출은 남기되 표시 (사진은 1회가 정상)
    return tracks


def probe(path: Path) -> tuple[float, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=avg_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    num, den = info["streams"][0]["avg_frame_rate"].split("/")
    return float(info["format"]["duration"]), (float(num) / float(den or 1)) or 30.0


def read_image(path: Path):
    import cv2
    from PIL import Image, ImageOps
    import numpy as np
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def frames(path: Path, fps: float | None = None):
    """ffmpeg로 디코딩(회전 반영) → (t, BGR 배열). fps=None 이면 모든 프레임."""
    import numpy as np
    dur, src_fps = probe(path)
    w, h = [int(v) for v in subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "ppm", "-"],
        capture_output=True).stdout.split(b"\n", 2)[1].split()]
    vf = f"fps={fps}" if fps else "null"
    p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-i", str(path), "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    step = 1.0 / (fps or src_fps)
    n = 0
    try:
        while True:
            buf = p.stdout.read(w * h * 3)
            if len(buf) < w * h * 3:
                break
            yield n * step, np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
            n += 1
    finally:
        p.kill()
        p.wait()


def media(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXT | IMAGE_EXT)


def review_sheet(entries: list[tuple[str, object, list[tuple[int, list[int]]]]], out_prefix: Path) -> list[Path]:
    """파일별 대표 프레임에 트랙 번호 박스를 그려 시트로."""
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
              "C:/Windows/Fonts/malgunbd.ttf"]:
        if Path(f).exists():
            font = ImageFont.truetype(f, 26)
            break
    tiles = []
    for name, img, labels in entries:
        im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        k = 420 / max(im.size)
        im = im.resize((int(im.width * k), int(im.height * k)))
        d = ImageDraw.Draw(im)
        for tid, (x, y, w, h) in labels:
            d.rectangle([x * k, y * k, (x + w) * k, (y + h) * k], outline=(255, 40, 40), width=4)
            d.text((x * k + 4, max(0, y * k - 30)), f"#{tid}", fill=(255, 255, 0), font=font)
        tile = Image.new("RGB", (440, 480), (25, 25, 25))
        tile.paste(im, ((440 - im.width) // 2, 10))
        ImageDraw.Draw(tile).text((10, 440), name[:30], fill=(255, 255, 255), font=font)
        tiles.append(tile)
    outs = []
    for page in range(0, len(tiles), 6):
        chunk = tiles[page:page + 6]
        sheet = Image.new("RGB", (3 * 450 + 10, ((len(chunk) + 2) // 3) * 490 + 10), (0, 0, 0))
        for i, t in enumerate(chunk):
            sheet.paste(t, (10 + (i % 3) * 450, 10 + (i // 3) * 490))
        p = out_prefix.parent / f"{out_prefix.name}-{page // 6 + 1:02d}.jpg"
        sheet.save(p, quality=88)
        outs.append(p)
    return outs


def cmd_scan(a) -> None:
    need_cv2()
    folder = (ROOT / a.folder) if not Path(a.folder).is_absolute() else Path(a.folder)
    det = Detector()
    plan = {"detector": det.name, "files": {}}
    entries = []
    for f in media(folder):
        if f.suffix.lower() in IMAGE_EXT:
            img = read_image(f)
            boxes = det.detect(img)
            tracks = [{"id": i + 1, "boxes": [[0, *b]]} for i, b in enumerate(boxes)]
            plan["files"][f.name] = {"kind": "image", "tracks": tracks, "keep": [], "extra": []}
            entries.append((f.name, img, [(t["id"], t["boxes"][0][1:]) for t in tracks]))
        else:
            dets = [(t, det.detect(img)) for t, img in frames(f, SCAN_FPS)]
            tracks = track(dets)
            # 영상에서 한 번만(0.2초) 잡힌 작은 박스는 오검출일 가능성이 커서 기본 제외 → 시트에서 확인
            weak = [tr["id"] for tr in tracks if len(tr["boxes"]) < 2]
            plan["files"][f.name] = {"kind": "video", "tracks": tracks, "keep": weak, "extra": [],
                                     "weak": weak}
            # 트랙마다 얼굴이 가장 크게 잡힌 순간을 대표 프레임으로 (가까운 순간끼리는 한 장에)
            groups: list[tuple[float, list]] = []
            for tr in tracks:
                tb = max(tr["boxes"], key=lambda b: b[3] * b[4])
                g = next((g for g in groups if abs(g[0] - tb[0]) < 0.3), None)
                if g is None:
                    groups.append((tb[0], [(tr["id"], tb[1:])]))
                else:
                    g[1].append((tr["id"], tb[1:]))
            if not groups:
                groups = [(0.0, [])]
            want = {round(g[0] * SCAN_FPS) for g in groups}
            shots = {i: im for i, (t, im) in enumerate(frames(f, SCAN_FPS)) if i in want}
            for t, labels in sorted(groups, key=lambda g: g[0]):
                img = shots.get(round(t * SCAN_FPS))
                if img is not None:
                    tag = "  (약한 검출: " + ",".join(f"#{i}" for i, _ in labels if i in weak) + ")" \
                        if any(i in weak for i, _ in labels) else ""
                    entries.append((f"{f.name} @{t:.1f}s{tag}", img, labels))
        n = len(plan["files"][f.name]["tracks"])
        w = len(plan["files"][f.name].get("weak", []))
        print(f"  {f.name}: 얼굴 {n}개" + (f" (그중 약한 검출 {w}개는 기본 제외)" if w else ""))
    out_dir = folder / "_faces"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    sheets = review_sheet(entries, out_dir / "review") if entries else []
    total = sum(len(v["tracks"]) for v in plan["files"].values())
    print(f"검출기: {det.name} / 파일 {len(plan['files'])}개 / 얼굴 {total}개 → 기본값: 전부 블러")
    print(f"계획: {(out_dir / 'plan.json').relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}")
    for s in sheets:
        print(f"검토 시트: {s}")
    print("→ 시트를 보고 마정이 본인 얼굴 번호만 plan.json 의 keep 에 넣으세요. 놓친 얼굴은 extra 에 추가.")


def blur_region(img, box, style: str, pad: float):
    import cv2
    h, w = img.shape[:2]
    x, y, bw, bh = box
    px, py = int(bw * pad), int(bh * pad)
    x0, y0 = max(0, x - px), max(0, y - py)
    x1, y1 = min(w, x + bw + px), min(h, y + bh + int(py * 1.3))
    if x1 <= x0 or y1 <= y0:
        return
    roi = img[y0:y1, x0:x1]
    if style == "mosaic":
        s = max(1, (x1 - x0) // 12)
        small = cv2.resize(roi, (max(1, (x1 - x0) // s), max(1, (y1 - y0) // s)), interpolation=cv2.INTER_LINEAR)
        img[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    else:
        k = max(31, ((x1 - x0) // 2) | 1)
        blurred = cv2.GaussianBlur(roi, (k, k), 0)
        blurred = cv2.GaussianBlur(blurred, (k, k), 0)
        mask = __import__("numpy").zeros(roi.shape[:2], "uint8")
        cv2.ellipse(mask, ((x1 - x0) // 2, (y1 - y0) // 2), ((x1 - x0) // 2, (y1 - y0) // 2), 0, 0, 360, 255, -1)
        mask = cv2.GaussianBlur(mask, (31, 31), 0)[..., None] / 255.0
        img[y0:y1, x0:x1] = (blurred * mask + roi * (1 - mask)).astype("uint8")


def boxes_at(t: float, tracks: list[dict], keep: list[int], extra: list, is_image: bool) -> list[list[int]]:
    out = []
    for tr in tracks:
        if tr["id"] in keep:
            continue
        bs = tr["boxes"]
        if is_image:
            out.append(bs[0][1:])
            continue
        if t < bs[0][0] - HOLD or t > bs[-1][0] + HOLD:
            continue
        prev = max((b for b in bs if b[0] <= t), key=lambda b: b[0], default=bs[0])
        nxt = min((b for b in bs if b[0] >= t), key=lambda b: b[0], default=bs[-1])
        if nxt[0] - prev[0] > 1e-6 and nxt[0] - prev[0] <= 1.5:
            r = (t - prev[0]) / (nxt[0] - prev[0])
            out.append([int(p + (n - p) * r) for p, n in zip(prev[1:], nxt[1:])])
        else:
            near = prev if abs(t - prev[0]) <= abs(nxt[0] - t) else nxt
            if abs(near[0] - t) <= HOLD:
                out.append(near[1:])
    for e in extra:
        if is_image or e[0] <= t <= e[1]:
            out.append(e[2:6])
    return out


def cmd_apply(a) -> None:
    need_cv2()
    import cv2
    folder = (ROOT / a.folder) if not Path(a.folder).is_absolute() else Path(a.folder)
    plan_path = folder / "_faces" / "plan.json"
    if not plan_path.exists():
        sys.exit("[오류] 먼저 scan 을 실행하세요.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    out_dir = folder.parent / (folder.name + "_blur")
    out_dir.mkdir(exist_ok=True)
    for f in media(folder):
        info = plan["files"].get(f.name)
        dst = out_dir / (f.stem + (".jpg" if f.suffix.lower() in IMAGE_EXT else ".mp4"))
        if info is None:
            print(f"  ! {f.name}: scan 이후 추가된 파일 — scan 을 다시 하세요"); continue
        keep, extra, tracks = info.get("keep", []), info.get("extra", []), info["tracks"]
        todo = [t for t in tracks if t["id"] not in keep]
        if not todo and not extra:
            if f.suffix.lower() in IMAGE_EXT:
                cv2.imwrite(str(dst), read_image(f), [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                shutil.copy2(f, out_dir / f.name)
            print(f"  {f.name}: 블러할 얼굴 없음 → 그대로 복사"); continue
        if info["kind"] == "image":
            img = read_image(f)
            for b in boxes_at(0, tracks, keep, extra, True):
                blur_region(img, b, a.style, a.pad)
            cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            dur, fps = probe(f)
            it = frames(f)
            t0, first = next(it)
            h, w = first.shape[:2]
            enc = subprocess.Popen(
                ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                 "-r", f"{fps:.5f}", "-i", "-", "-i", str(f), "-map", "0:v", "-map", "1:a:0?",
                 "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-shortest", str(dst)], stdin=subprocess.PIPE)
            for t, img in [(t0, first), *it]:
                for b in boxes_at(t, tracks, keep, extra, False):
                    blur_region(img, b, a.style, a.pad)
                enc.stdin.write(img.tobytes())
            enc.stdin.close(); enc.wait()
            if enc.returncode != 0:
                sys.exit(f"[오류] 인코딩 실패: {f.name}")
        print(f"  {f.name}: 얼굴 {len(todo) + len(extra)}개 블러 → {dst.name}")
    print(f"완료: {out_dir}  (원본 폴더는 그대로)")


def cmd_check(a) -> None:
    need_cv2()
    folder = (ROOT / a.folder) if not Path(a.folder).is_absolute() else Path(a.folder)
    det = Detector()
    entries, left = [], 0
    for f in media(folder):
        if f.suffix.lower() in IMAGE_EXT:
            img = read_image(f)
            boxes = det.detect(img)
            entries.append((f.name, img, [(i + 1, b) for i, b in enumerate(boxes)]))
            left += len(boxes)
        else:
            worst = (0, None, [])
            for t, img in frames(f, 2):
                boxes = det.detect(img)
                if len(boxes) > worst[0] or worst[1] is None:
                    worst = (len(boxes), (t, img), boxes)
            left += worst[0]
            t, img = worst[1]
            entries.append((f"{f.name} @{t:.1f}s", img, [(i + 1, b) for i, b in enumerate(worst[2])]))
    out_dir = folder.parent / "_faces_check"
    out_dir.mkdir(exist_ok=True)
    sheets = review_sheet(entries, out_dir / "check") if entries else []
    for s in sheets:
        print(f"확인 시트: {s}")
    print(f"블러 후에도 얼굴로 잡힌 곳: {left}곳 (keep 한 본인 얼굴이면 정상). 시트를 눈으로 확인하세요.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan"); s.add_argument("folder"); s.set_defaults(fn=cmd_scan)
    p = sp.add_parser("apply"); p.add_argument("folder")
    p.add_argument("--style", choices=["blur", "mosaic"], default="blur")
    p.add_argument("--pad", type=float, default=0.35, help="얼굴 박스 주변 여유 비율")
    p.set_defaults(fn=cmd_apply)
    c = sp.add_parser("check"); c.add_argument("folder"); c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
