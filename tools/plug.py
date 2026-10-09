"""설치된 로컬 플러그인을 찾아 주고, IT Reelsmaker 스크립트를 대신 실행해 주는 도우미.

담당자(에이전트)는 플러그인 폴더 경로를 몰라도 이 도구로 플러그인 기능을 쓴다.

    python3 tools/plug.py doctor                  # 플러그인 3종 설치 여부 + IT Reelsmaker 환경 점검
    python3 tools/plug.py where                   # 찾은 경로 출력 (config/plugins.json 에 캐시)
    python3 tools/plug.py rm <스크립트> [인자...]   # IT Reelsmaker 스크립트 실행
        예) python3 tools/plug.py rm transcribe edit/2026-10-09 footage/2026-10-09/main.MOV --language ko
    python3 tools/plug.py skill <스킬이름>         # 플러그인 스킬의 SKILL.md 경로 (Skill 도구가 안 될 때 Read용)
        예) python3 tools/plug.py skill hook-writer

찾는 위치: ~/.claude/plugins (Claude Code 플러그인 캐시), ~/.claude/skills, 환경변수 REELSMAKER_DIR.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "config" / "plugins.json"
SEARCH = [Path.home() / ".claude" / "plugins", Path.home() / ".claude" / "skills"]

PLUGINS = {
    # 키: (찾을 파일 패턴, 설명, 설치 명령)
    "reelsmaker": ("**/it-reelsmaker/scripts/cut.py", "IT Reelsmaker (전사·컷·자막·B-roll·마스터링)",
                   "/plugin marketplace add itpartypattaya/reels-montage\n"
                   "      /plugin install it-reelsmaker@itparty"),
    "social": ("**/hook-writer/SKILL.md", "Social Media Skills (훅·썸네일·자막·캡션 노하우)",
               "/plugin marketplace add social-media-skills/skills\n"
               "      /plugin install social-media-skills@social-media-skills"),
    "ffmpeg": ("**/ffmpeg-command/SKILL.md", "ffmpeg-llm (ffmpeg 명령 보조, ffmpeg-expert 에이전트)",
               "/plugin marketplace add rendi-api/ffmpeg-llm\n"
               "      /plugin install ffmpeg-llm@rendi-official"),
}


def newest(paths: list[Path]) -> Path | None:
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def find_all(refresh: bool = False) -> dict:
    if CACHE.exists() and not refresh:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        if all(v is None or Path(v).exists() for v in data.values()):
            return data
    found = {}
    env = os.environ.get("REELSMAKER_DIR")
    for key, (pattern, _, _) in PLUGINS.items():
        hits: list[Path] = []
        if key == "reelsmaker" and env and (Path(env) / "scripts" / "cut.py").exists():
            hits = [Path(env) / "scripts" / "cut.py"]
        for base in SEARCH:
            if base.exists() and not hits:
                hits = [p for p in base.glob(pattern) if "/.git/" not in str(p)]
        hit = newest(hits)
        if hit is None:
            found[key] = None
        elif key == "reelsmaker":
            found[key] = str(hit.parent)                     # .../it-reelsmaker/scripts
        else:
            found[key] = str(hit.parent.parent)              # .../skills
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding="utf-8")
    return found


def python_exe() -> str:
    return sys.executable or "python3"


def cmd_where(refresh=True) -> dict:
    found = find_all(refresh=refresh)
    for key, (_, desc, install) in PLUGINS.items():
        mark = "✓" if found[key] else "✗"
        print(f"{mark} {desc}\n    {found[key] or '설치 안 됨 → Claude Code에서:'}")
        if not found[key]:
            print(f"      {install}")
    return found


def cmd_doctor() -> None:
    found = cmd_where()
    if found["reelsmaker"]:
        print("\n[IT Reelsmaker 환경 점검]")
        r = subprocess.run([python_exe(), str(Path(found["reelsmaker"]) / "doctor.py")], cwd=ROOT)
        sys.exit(r.returncode)
    sys.exit(1)


def cmd_rm(args: list[str]) -> None:
    if not args:
        sys.exit("사용법: tools/plug.py rm <스크립트> [인자...]")
    scripts = find_all().get("reelsmaker")
    if not scripts:
        cmd_where()
        sys.exit("[오류] IT Reelsmaker 플러그인을 찾지 못했어요. 위 명령으로 설치하세요.")
    name = args[0] if args[0].endswith(".py") else f"{args[0]}.py"
    script = Path(scripts) / name
    if not script.exists():
        sys.exit(f"[오류] 플러그인에 {name} 이 없어요. 있는 것: "
                 + ", ".join(sorted(p.stem for p in Path(scripts).glob('*.py'))))
    env = dict(os.environ, REELS_PROJECT=str(ROOT))
    r = subprocess.run([python_exe(), str(script), *args[1:]], cwd=ROOT, env=env)
    sys.exit(r.returncode)


def cmd_skill(name: str) -> None:
    found = find_all()
    for key in ("social", "ffmpeg"):
        if found.get(key) and (Path(found[key]) / name / "SKILL.md").exists():
            print(Path(found[key]) / name / "SKILL.md")
            return
    if found.get("reelsmaker") and name == "it-reelsmaker":
        print(Path(found["reelsmaker"]).parent / "SKILL.md")
        return
    sys.exit(f"[오류] 스킬 {name} 을 찾지 못했어요 (python3 tools/plug.py where)")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "where":
        cmd_where()
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "rm":
        cmd_rm(rest)
    elif cmd == "skill" and rest:
        cmd_skill(rest[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
