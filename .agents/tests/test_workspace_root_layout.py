import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from workspace_root_layout import (  # noqa: E402
    latest_rows_by_source,
    processed_run_destination,
    source_destination,
    source_disposition,
)


class WorkspaceRootLayoutTests(unittest.TestCase):
    def test_status_dispositions(self):
        self.assertEqual(source_disposition({"Status": "discovered"}), "inbox")
        self.assertEqual(source_disposition({"Status": "historical"}), "archive")
        self.assertEqual(source_disposition({"Status": "completed"}), "archive")
        self.assertEqual(source_disposition({
            "Status": "ignored",
            "Reason": "ignored (reference_material): canonical input",
        }), "reference")
        self.assertEqual(source_disposition({
            "Status": "ignored",
            "Reason": "ignored (non_intake_course_material): training",
        }), "reference")

    def test_destinations(self):
        source = "00_Source_Docs/01_Meeting_Transcripts/meeting.txt"
        self.assertEqual(source_destination(source, "inbox"), ("00_Inbox", "meeting.txt"))
        self.assertEqual(
            source_destination(source, "archive"),
            ("90_Archive", "Processed_Sources", "Meeting_Transcripts", "meeting.txt"),
        )
        reference = "00_Source_Docs/03_Source_Documents/course/item.docx"
        self.assertEqual(
            source_destination(reference, "reference"),
            ("30_Reference", "Source_Documents", "course", "item.docx"),
        )

    def test_latest_row_wins_case_insensitively(self):
        rows = [
            {"Source": "00_Source_Docs/A.txt", "Status": "discovered"},
            {"Source": "00_source_docs/a.txt", "Status": "historical"},
        ]
        result = latest_rows_by_source(rows)
        self.assertEqual(result["00_source_docs/a.txt"]["Status"], "historical")

    def test_processed_run_destination_is_unique_and_dated(self):
        self.assertEqual(
            processed_run_destination("20260721-source-abcd", "source.txt", "2026-07-21"),
            ("90_Archive", "Processed_Sources", "2026", "07", "20260721-source-abcd", "source.txt"),
        )


if __name__ == "__main__":
    unittest.main()
