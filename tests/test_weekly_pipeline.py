import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch, Mock

from scripts import convert_all_to_weekly as convert
from scripts import generate_weekly_json as weekly
from scripts import fetch_latest_papers as fetch
from scripts import analyze_pending as analysis


class WeeklyPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for module, name in [(convert, "SITE_PUBLIC_DATA"), (weekly, "SITE_DATA_DIR"),
                             (fetch, "DATA_ROOT")]:
            patcher = patch.object(module, name, self.root)
            patcher.start()
            self.addCleanup(patcher.stop)

    def save(self, title, year, week, date, **extra):
        paper = dict(title=title, slug=weekly.slugify(title), date=date,
                     analysis_ko="기존 요약", analysis_en="Existing summary")
        paper.update(extra)
        weekly.save_weekly_data("marketing", year, week, [paper])

    def read(self, path):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def test_batch_preserves_history_and_summaries_and_is_idempotent(self):
        self.save("Old", 2025, 1, "2025-01-01")
        self.save("Existing", 2026, 22, "2026-05-26")
        batch = [dict(Category="Marketing", Title=title, Date="2026-05-29", AI_Analysis="")
                 for title in ("Existing", "New")]
        for _ in range(2):
            convert.process_category(batch, "Marketing", "마케팅", "Marketing")
        week = self.read("marketing/2026/W22.json")
        self.assertEqual(week["paperCount"], 2)
        self.assertEqual(week["papers"][0]["analysis_ko"], "기존 요약")
        self.assertEqual(len(self.read("marketing/index.json")["years"]), 2)
        self.assertEqual(self.read("marketing/2026/index.json")["totalPapers"], 2)

    def test_empty_batch_does_not_hide_existing_weeks(self):
        self.save("Old", 2025, 1, "2025-01-01")
        convert.process_category([], "Marketing", "마케팅", "Marketing")
        self.assertEqual(self.read("marketing/index.json")["years"][0]["totalPapers"], 1)

    def test_month_end_and_iso_year_dates_are_not_clamped(self):
        self.assertEqual(convert.get_iso_week(convert.parse_date("2026-03-31")), (2026, 14))
        self.assertEqual(convert.get_iso_week(convert.parse_date("2025-12-31")), (2026, 1))
        self.assertIsNone(convert.parse_date("2026-02-30"))

    def test_recovery_date_ignores_future_issue_dates(self):
        self.save("Old", 2026, 22, "2026-05-29")
        self.save("Future", 2027, 1, "2027-01-01")
        self.assertEqual(fetch.default_from_date(datetime.date(2026, 9, 29)), "2026-05-08")

    def test_each_category_uses_its_own_recovery_date(self):
        self.save("Marketing latest", 2026, 39, "2026-09-25")
        weekly.save_weekly_data("finance", 2026, 22, [dict(title="Finance older", slug="finance-older", date="2026-05-29")])
        self.assertEqual(fetch.default_from_date(datetime.date(2026, 9, 29), "Finance"), "2026-05-08")
        self.assertEqual(fetch.default_from_date(datetime.date(2026, 9, 29), "Marketing"), "2026-09-04")

    @patch.object(fetch.requests, "Session")
    @patch.object(fetch, "enrich_abstract", side_effect=lambda abstract, doi: abstract)
    def test_duplicate_issns_are_skipped_but_existing_abstracts_can_refresh(self, enrich, session):
        self.save("Existing", 2026, 22, "2026-05-29")
        item = {"title": ["New"], "container-title": ["Journal of Marketing"],
                "published": {"date-parts": [[2026, 9, 29]]}}
        response = Mock()
        response.json.return_value = {"message": {"items": [item, dict(item, title=["Existing"])]}}
        session.return_value.get.return_value = response
        result = fetch.fetch_domain_papers("Marketing", fetch.DOMAINS["Marketing"], "2026-05-01")
        self.assertEqual([p["Title"] for p in result], ["New", "Existing"])
        self.assertEqual(enrich.call_count, 2)
        self.assertEqual(session.return_value.get.call_args.kwargs["timeout"], 30)

    def test_existing_abstract_refresh_preserves_summary_and_original_route(self):
        self.save("Existing", 2026, 22, "2026-05-29", abstract="Old abstract")
        batch = [dict(Category="Marketing", Title="Existing", Date="2026-09-29",
                      Abstract="Updated publisher abstract", AI_Analysis="")]
        convert.process_category(batch, "Marketing", "마케팅", "Marketing")
        paper = self.read("marketing/2026/W22.json")["papers"][0]
        self.assertEqual(paper["abstract"], "Updated publisher abstract")
        self.assertEqual(paper["analysis_ko"], "기존 요약")
        self.assertFalse((self.root / "marketing/2026/W40.json").exists())

    def test_missing_fetched_abstract_does_not_erase_saved_abstract(self):
        self.save("Existing", 2026, 22, "2026-05-29", abstract="Saved abstract")
        convert.process_category([dict(Category="Marketing", Title="Existing", Date="2026-05-29",
                                      Abstract="초록(Abstract) 정보가 제공되지 않았습니다.")],
                                 "Marketing", "마케팅", "Marketing")
        self.assertEqual(self.read("marketing/2026/W22.json")["papers"][0]["abstract"], "Saved abstract")

    def test_metadata_collector_does_not_import_gemini(self):
        subprocess.run([sys.executable, "-c",
                        "from scripts import fetch_latest_papers; import sys; "
                        "assert 'gemini_safe_client' not in sys.modules; "
                        "assert 'google.generativeai' not in sys.modules"], check=True)

    def test_weekly_workflow_has_no_ai_step_or_secret(self):
        workflow = Path('.github/workflows/weekly_research.yml').read_text(encoding='utf-8')
        self.assertNotIn('secrets.GEMINI_API_KEY', workflow)
        self.assertNotIn('python scripts/analyze_pending.py', workflow)

    def test_collection_batch_does_not_overwrite_legacy_state(self):
        legacy = self.root / "backfill_state.json"
        legacy.write_text('[{"Title": "Legacy"}]', encoding="utf-8")
        batch = self.root / ".weekly_batch.json"
        cutoff = datetime.date.today().isoformat()
        record = dict(Category="Marketing", Title="New", Date="2026-09-28",
                      Abstract="Publisher abstract", AI_Analysis="", YearMonth="2026-09")
        with patch.object(fetch, "BACKFILL_FILE", str(batch)), \
             patch.object(convert, "BACKFILL_FILE", str(batch)), \
             patch.object(fetch, "fetch_domain_papers", side_effect=lambda cat, *args: [dict(record, Category=cat)]), \
             patch.object(sys, "argv", ["fetch", "--from-date", "2020-01-01", "--until-date", cutoff]):
            fetch.main()
            convert.main()
        self.assertEqual(json.loads(legacy.read_text())[0]["Title"], "Legacy")
        self.assertEqual(self.read("marketing/update_status.json")["throughDate"], cutoff)
        self.assertFalse(self.read("marketing/update_status.json")["aiEnabled"])
        for category in ("finance", "accounting"):
            self.assertEqual(self.read(f"{category}/update_status.json")["throughDate"], cutoff)
            self.assertEqual(self.read(f"{category}/2026/W40.json")["paperCount"], 1)

    @patch.object(fetch.requests, "Session")
    def test_http_failure_is_not_reported_as_empty_success(self, session):
        session.return_value.get.side_effect = fetch.requests.Timeout("timeout")
        with self.assertRaisesRegex(RuntimeError, "Crossref fetch failed"):
            fetch.fetch_domain_papers("Marketing", fetch.DOMAINS["Marketing"], "2026-05-01")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"})
    @patch.object(analysis, "analyze_paper")
    def test_partial_ai_failure_keeps_success_and_retries_pending(self, analyze):
        for title in ("A", "B"):
            self.save(title, 2026, 22, "2026-05-29", analysis_ko="", analysis_en="")
        analyze.side_effect = ["===KOREAN===\n완료\n===ENGLISH===\nDone", "AI Analysis Failed"]
        with self.assertRaises(RuntimeError):
            analysis.run(self.root / "marketing")
        papers = self.read("marketing/2026/W22.json")["papers"]
        self.assertEqual(papers[0]["analysis_en"], "Done")
        self.assertEqual(papers[1]["analysis_en"], "")
        analyze.side_effect = None
        analyze.return_value = "===KOREAN===\n완료\n===ENGLISH===\nDone"
        self.assertEqual(analysis.run(self.root / "marketing"), (1, 0))

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-only"})
    @patch.object(analysis, "analyze_paper", return_value="===KOREAN===\n완료\n===ENGLISH===\nDone")
    def test_ai_batch_limit_and_english_only_failure(self, analyze):
        for title in ("A", "B"):
            self.save(title, 2026, 22, "2026-05-29", analysis_en="")
        self.assertEqual(analysis.run(self.root / "marketing", limit=1), (1, 1))
        self.assertEqual(analyze.call_count, 1)


if __name__ == "__main__":
    unittest.main()
