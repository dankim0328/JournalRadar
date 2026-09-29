"""Analyze a bounded batch of pending marketing papers; preserve each success."""
import json
import os
from pathlib import Path

try:
    from .retry_failed_analysis import analyze_paper
except ImportError:
    from retry_failed_analysis import analyze_paper

DATA_ROOT = Path(__file__).resolve().parents[1] / "site/public/data/marketing"
FAILURE_MARKERS = ("AI 분석 실패", "AI Analysis Failed", "AI 백필 분석 실패")


def needs_analysis(paper):
    return any(not paper.get(key) or any(m in paper[key] for m in FAILURE_MARKERS)
               for key in ("analysis_ko", "analysis_en"))


def run(data_root=DATA_ROOT, limit=40):
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is missing; configure the Actions secret")
    pending = []
    documents = {}
    for path in sorted(Path(data_root).glob("*/W*.json")):
        documents[path] = json.loads(path.read_text(encoding="utf-8"))
        for paper in documents[path].get("papers", []):
            if needs_analysis(paper):
                pending.append((path, paper))
    # Old pending records must not starve as new papers arrive.
    pending.sort(key=lambda entry: entry[1].get("date", ""))
    fixed = 0
    for path, paper in pending[:limit]:
        result = analyze_paper("마케팅", paper)
        ko, separator, en = result.partition("===ENGLISH===")
        ko = ko.replace("===KOREAN===", "").strip()
        en = en.strip()
        if not separator or not ko or not en or any(m in result for m in FAILURE_MARKERS):
            raise RuntimeError(f"AI analysis failed or incomplete after {fixed} successes; "
                               "saved successes are retained and pending papers will retry next run")
        paper.update(analysis_ko=ko, analysis_en=en)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(documents[path], ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
        fixed += 1
    remaining = len(pending) - fixed
    print(f"AI analysis: {fixed} completed, {remaining} pending")
    if remaining:
        print(f"::warning::{remaining} marketing papers remain pending; rerun to continue")
    return fixed, remaining


if __name__ == "__main__":
    run(limit=int(os.environ.get("MAX_ANALYSES", "40")))
